"""Direct Azure OpenAI inference; no Copilot executable or agent orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    OpenAIError,
)

from ._lifecycle import finish_cleanup
from .contracts import (
    InferenceError,
    InferenceRequest,
    InferenceResponse,
    strict_json,
    validate_content,
)


def azure_base_url(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and parsed.hostname.endswith((
                ".openai.azure.com", ".services.ai.azure.com",
                ".cognitiveservices.azure.com",
            ))
            and not parsed.username and not parsed.password
            and parsed.port in {None, 443}
            and not parsed.query and not parsed.fragment
            and parsed.path in {"", "/", "/openai/v1", "/openai/v1/"}
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise InferenceError(
            "configuration", "Expected an HTTPS public Azure OpenAI resource endpoint"
        )
    return f"https://{parsed.hostname}/openai/v1/"


def native_schema(schema: dict) -> dict:
    if schema.get("type") != "object":
        raise InferenceError("invalid_schema", "Native JSON requires a root object schema")

    def check(value: dict) -> dict:
        if not isinstance(value, dict):
            raise InferenceError("invalid_schema", "Native JSON does not accept boolean subschemas")
        # Azure's documented native subset omits these; the original schema still validates locally.
        local_only = {"uniqueItems", "minLength", "maxLength", "minimum", "maximum", "minItems", "maxItems"}
        wire = {key: child for key, child in value.items() if key not in local_only}
        if value.get("type") == "object" or "properties" in value:
            properties = value.get("properties", {})
            if (
                value.get("additionalProperties") is not False
                or set(value.get("required", [])) != set(properties)
            ):
                raise InferenceError(
                    "invalid_schema",
                    "Native JSON requires closed objects with every property required",
                )
            wire["properties"] = {name: check(child) for name, child in properties.items()}
        if "items" in value:
            wire["items"] = check(value["items"])
        for key in ("anyOf", "allOf", "oneOf"):
            if key in value:
                wire[key] = [check(child) for child in value[key]]
        if "$defs" in value:
            wire["$defs"] = {name: check(child) for name, child in value["$defs"].items()}
        return wire

    return {
        "type": "json_schema",
        "json_schema": {"name": "inference_response", "strict": True, "schema": check(schema)},
    }


def _filtered(value: object) -> bool:
    if isinstance(value, dict):
        return value.get("filtered") is True or any(_filtered(x) for x in value.values())
    if isinstance(value, list):
        return any(_filtered(x) for x in value)
    return False


class _WireBoundaryViolation(InferenceError):
    def __init__(self, message: str) -> None:
        super().__init__("boundary_violation", message)


def _responses_text(response: object, receipt: dict) -> str:
    receipt["response_status"] = getattr(response, "status", None)
    receipt["refused"] = False
    receipt["content_filter_triggered"] = _filtered(response.model_extra)
    if receipt["content_filter_triggered"]:
        raise InferenceError("content_filter", "Azure content filtering blocked the response")
    if response.error is not None:
        raise InferenceError("provider_error", "Azure response reported an error")
    if receipt["response_status"] != "completed" or response.incomplete_details is not None:
        raise InferenceError("incomplete_response", "Azure response did not finish normally")
    if not isinstance(response.output, list):
        raise InferenceError("invalid_response", "Expected Azure response output items")
    texts = []
    for item in response.output:
        kind = getattr(item, "type", None)
        if kind == "reasoning":
            # Reasoning metadata is allowed, but never returned or copied to receipts.
            if getattr(item, "status", None) not in {None, "completed"}:
                raise InferenceError("incomplete_response", "Azure reasoning did not finish normally")
            continue
        if kind != "message":
            raise InferenceError("boundary_violation", "Unexpected Azure operational output")
        if getattr(item, "role", None) != "assistant":
            raise InferenceError("invalid_response", "Expected Azure assistant output")
        if getattr(item, "status", None) != "completed":
            raise InferenceError("incomplete_response", "Azure message did not finish normally")
        if not isinstance(getattr(item, "content", None), list):
            raise InferenceError("invalid_response", "Expected Azure text content")
        for content in item.content:
            if getattr(content, "type", None) == "refusal":
                receipt["refused"] = True
                raise InferenceError("refusal", "Azure model refused the request")
            if (
                getattr(content, "type", None) != "output_text"
                or not isinstance(getattr(content, "text", None), str)
            ):
                raise InferenceError("invalid_response", "Unexpected Azure non-text output")
            texts.append(content.text)
    return "".join(texts)


class AzureOpenAIProvider:
    def __init__(
        self,
        endpoint: str | None = None,
        *,
        api_key: str | None = None,
        auth: str = "api_key",
        api: str = "chat_completions",
        native_json_schema: bool = False,
        max_completion_tokens: int | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = azure_base_url(
            endpoint if endpoint is not None else os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        )
        if auth not in {"api_key", "entra"}:
            raise InferenceError("configuration", "Authentication must be api_key or entra")
        if api not in {"chat_completions", "responses"}:
            raise InferenceError("configuration", "API must be chat_completions or responses")
        if auth == "entra" and api_key is not None:
            raise InferenceError("configuration", "An API key cannot be supplied in Entra mode")
        key = api_key if api_key is not None else os.environ.get("AZURE_OPENAI_API_KEY")
        if auth == "api_key" and (
            not isinstance(key, str) or not key or any(char.isspace() for char in key)
        ):
            raise InferenceError("configuration", "AZURE_OPENAI_API_KEY is required")
        if not isinstance(native_json_schema, bool):
            raise InferenceError("configuration", "native_json_schema must be boolean")
        if max_completion_tokens is not None and (
            type(max_completion_tokens) is not int or max_completion_tokens < 1
        ):
            raise InferenceError("configuration", "Completion-token cap must be a positive integer")
        self.auth = auth
        self.api = api
        self._api_key = key if auth == "api_key" else None
        self.native_json_schema = native_json_schema
        self.max_completion_tokens = max_completion_tokens
        self._transport = http_transport
        self._client: AsyncOpenAI | None = None
        self._http: httpx.AsyncClient | None = None
        self._credential: DefaultAzureCredential | None = None
        self._active_receipt: dict | None = None
        self._last_receipt: dict = {}
        self._closed = False
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> AzureOpenAIProvider:
        if self._client is not None or self._closed:
            raise InferenceError("lifecycle", "Provider is already started or closed")
        key = self._api_key
        if self.auth == "entra":
            self._credential = DefaultAzureCredential()
            key = get_bearer_token_provider(self._credential, "https://ai.azure.com/.default")
        self._http = httpx.AsyncClient(
            transport=self._transport or httpx.AsyncHTTPTransport(retries=0),
            follow_redirects=False,
            event_hooks={
                "request": [self._observe_request],
                "response": [self._observe_response],
            },
        )
        try:
            self._client = AsyncOpenAI(
                api_key=key,
                base_url=self.base_url,
                max_retries=0,
                http_client=self._http,
            )
        except Exception:
            await self.close()
            raise InferenceError("startup", "Could not initialize Azure OpenAI client") from None
        return self

    async def __aexit__(self, _type: object, error: BaseException | None, _tb: object) -> None:
        try:
            await self.close()
        except InferenceError as cleanup:
            if isinstance(error, InferenceError):
                cleanup.receipt = {**error.receipt, "primary_error_class": error.code}
            raise

    async def close(self) -> None:
        interrupted = await finish_cleanup(self._shutdown())
        if interrupted:
            raise asyncio.CancelledError

    async def _shutdown(self) -> None:
        async with self._lock:
            self._closed = True
            errors = []
            for name, resource in (("http", self._http), ("credential", self._credential)):
                if resource is not None:
                    try:
                        async with asyncio.timeout(10):
                            if name == "http":
                                await resource.aclose()
                            else:
                                await resource.close()
                    except (Exception, asyncio.CancelledError):
                        errors.append(name)
                    else:
                        if name == "http":
                            self._http = None
                            self._client = None
                        else:
                            self._credential = None
            self._api_key = None
            if errors:
                raise InferenceError(
                    "cleanup", "Azure client resource shutdown failed",
                    {**self._last_receipt, "cleanup_failed_resources": errors},
                )

    def configuration(self) -> dict:
        return {
            "provider": "azure-openai",
            "sdk_version": importlib.metadata.version("openai"),
            "api": (
                "azure-openai-v1-responses" if self.api == "responses"
                else "azure-openai-v1-chat-completions"
            ),
            "endpoint_sha256": hashlib.sha256(self.base_url.encode()).hexdigest(),
            "auth": self.auth,
            "sdk_retries": 0,
            "http_transport_retries": 0 if self._transport is None else "caller_supplied",
            "follow_redirects": False,
            "schema_mode": "native" if self.native_json_schema else "prompt_guidance",
            "max_completion_tokens": self.max_completion_tokens,
            "tools": False,
            "usd_cost": None,
        }

    async def _observe_request(self, request: httpx.Request) -> None:
        receipt = self._active_receipt
        if receipt is None:
            raise _WireBoundaryViolation("Unattributed Azure HTTP request")
        receipt["http_dispatches_observed"] += 1
        if receipt["http_dispatches_observed"] != 1:
            raise _WireBoundaryViolation("Unexpected additional HTTP dispatch")
        if (
            request.method != "POST"
            or str(request.url) != self.base_url + (
                "responses" if self.api == "responses" else "chat/completions"
            )
        ):
            raise _WireBoundaryViolation("Unexpected Azure inference destination")
        body = strict_json(request.content.decode("utf-8"))
        if not isinstance(body, dict):
            raise _WireBoundaryViolation("Unexpected Azure request body")
        messages = body.get("input" if self.api == "responses" else "messages", [])
        if (
            body.get("tools") or body.get("functions")
            or not isinstance(messages, list)
            or len(messages) != 2
            or any(not isinstance(item, dict) for item in messages)
            or [item.get("role") for item in messages] != ["system", "user"]
            or any(not isinstance(item.get("content"), str) for item in messages)
            or body.get("model") != receipt["requested_model"]
        ):
            raise _WireBoundaryViolation("Unexpected Azure request content")
        if self.api == "responses" and (
            body.get("tools") != [] or body.get("tool_choice") != "none"
            or body.get("parallel_tool_calls") is not False
            or body.get("store") is not False or body.get("background") is not False
            or any(key in body for key in (
                "instructions", "conversation", "previous_response_id", "messages",
            ))
        ):
            raise _WireBoundaryViolation("Unexpected Azure Responses controls")
        observed = [
            hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
            for item in messages
        ]
        if observed != [receipt["system_sha256"], receipt["user_sha256"]]:
            raise _WireBoundaryViolation("Azure wire messages differ from input")
        receipt["wire_message_hashes_match"] = True
        receipt["wire_body_sha256"] = hashlib.sha256(request.content).hexdigest()

    async def _observe_response(self, response: httpx.Response) -> None:
        receipt = self._active_receipt
        if receipt is None:
            raise _WireBoundaryViolation("Unattributed Azure HTTP response")
        receipt["http_status"] = response.status_code
        body = await response.aread()
        receipt["wire_response_sha256"] = hashlib.sha256(body).hexdigest()

    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        system, user, validator = request.prepared()
        if request.reasoning_effort not in {None, "none", "minimal", "low", "medium", "high", "xhigh"}:
            raise InferenceError("unsupported_control", "Unsupported Azure reasoning effort")
        response_format = (
            native_schema(validator.schema)
            if self.native_json_schema and validator is not None else None
        )
        async with self._lock:
            if self._client is None or self._closed:
                raise InferenceError("lifecycle", "Azure provider is not open")
            receipt = {
                **self.configuration(),
                "request_id": str(uuid4()),
                "requested_model": request.model,
                "observed_model": None,
                "requested_reasoning_effort": request.reasoning_effort,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
                "user_sha256": hashlib.sha256(user.encode("utf-8")).hexdigest(),
                "http_dispatches_observed": 0,
                "adapter_attempts": 0,
                "usage": None,
                "cache_mode": "no_application_result_cache_backend_cache_uncontrolled",
            }
            self._last_receipt = self._active_receipt = receipt
            options = {}
            if response_format is not None:
                if self.api == "responses":
                    options["text"] = {
                        "format": {"type": "json_schema", **response_format["json_schema"]},
                    }
                else:
                    options["response_format"] = response_format
            if request.reasoning_effort is not None:
                if self.api == "responses":
                    options["reasoning"] = {"effort": request.reasoning_effort}
                else:
                    options["reasoning_effort"] = request.reasoning_effort
            if self.max_completion_tokens is not None:
                options[
                    "max_output_tokens" if self.api == "responses" else "max_completion_tokens"
                ] = self.max_completion_tokens
            started, failure = time.monotonic(), None
            try:
                receipt["adapter_attempts"] = 1
                async with asyncio.timeout(request.timeout_seconds):
                    messages = [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ]
                    if self.api == "responses":
                        response = await self._client.responses.create(
                            model=request.model, input=messages,
                            tools=[], tool_choice="none", parallel_tool_calls=False,
                            store=False, background=False,
                            stream=False, timeout=request.timeout_seconds, **options,
                        )
                    else:
                        response = await self._client.chat.completions.create(
                            model=request.model, messages=messages,
                            n=1, stream=False, timeout=request.timeout_seconds, **options,
                        )
                receipt["observed_model"] = response.model
                receipt["usage"] = (
                    response.usage.model_dump(
                        mode="json", exclude_unset=self.api == "responses",
                    ) if response.usage else None
                )
                if self.api == "responses":
                    text = _responses_text(response, receipt)
                else:
                    if len(response.choices) != 1:
                        raise InferenceError("invalid_response", "Expected one Azure completion")
                    choice = response.choices[0]
                    receipt["finish_reason"] = choice.finish_reason
                    receipt["refused"] = bool(choice.message.refusal)
                    receipt["content_filter_triggered"] = _filtered(response.model_extra) or _filtered(
                        choice.model_extra
                    )
                    if choice.finish_reason == "content_filter" or receipt["content_filter_triggered"]:
                        raise InferenceError("content_filter", "Azure content filtering blocked the response")
                    if choice.message.refusal:
                        raise InferenceError("refusal", "Azure model refused the request")
                    if choice.message.tool_calls or choice.message.function_call:
                        raise InferenceError("boundary_violation", "Unexpected Azure tool request")
                    if choice.finish_reason != "stop":
                        raise InferenceError("incomplete_response", "Azure completion did not finish normally")
                    text = choice.message.content
                if isinstance(text, str):
                    receipt["response_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                parsed = validate_content(text, validator)
                if receipt["http_dispatches_observed"] != 1:
                    raise InferenceError("unverified_attempts", "Expected one Azure HTTP dispatch")
            except InferenceError as error:
                failure = error
            except (TimeoutError, APITimeoutError):
                failure = InferenceError("timeout", "Azure inference deadline exceeded")
            except APIStatusError as error:
                receipt["http_status"] = error.status_code
                code = {
                    401: "authentication", 403: "permission_denied",
                    404: "not_found", 429: "rate_limit",
                }.get(error.status_code, "provider_error" if error.status_code >= 500 else "bad_request")
                failure = InferenceError(code, "Azure inference returned an HTTP error")
            except APIConnectionError as error:
                # The SDK wraps event-hook failures as connection errors.
                failure = (
                    error.__cause__ if isinstance(error.__cause__, _WireBoundaryViolation)
                    else InferenceError("transport", "Azure inference connection failed")
                )
            except asyncio.CancelledError as error:
                receipt["cancelled"] = True
                failure = error
            except OpenAIError:
                failure = InferenceError("provider_error", "Azure SDK rejected the response")
            except Exception:
                failure = InferenceError("transport", "Azure inference failed")
            finally:
                receipt["elapsed_seconds"] = time.monotonic() - started
                receipt["billing_complete"] = receipt["usage"] is not None
                self._active_receipt = None
            if failure is not None:
                if isinstance(failure, InferenceError):
                    failure.receipt = receipt
                raise failure from None
            return InferenceResponse(text=text, parsed=parsed, receipt=receipt)
