from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib.metadata
import os
import shutil
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from copilot import CopilotClient, RuntimeConnection
from copilot.rpc import PermissionDecisionReject
from copilot.session import CopilotSession
from copilot.session_events import SessionEvent

from ._lifecycle import finish_cleanup
from .contracts import (
    InferenceError,
    InferenceRequest,
    InferenceResponse,
    validate_content,
)

CAPABILITIES = {
    "text": True,
    "system_message": "replace_requested",
    "json_schema": "prompt_guidance_and_local_validation",
    "conversation": "fresh_session_per_request",
    "tools": False,
    "streaming_api": False,
    "native_structured_output": False,
    "sampling_controls": False,
    "max_output_tokens": False,
    "reasoning_effort": "catalog_validated_when_supplied",
    "adapter_retries": 0,
    "internal_http_retries": "unknown",
    "raw_provider_equivalence": False,
}


def child_environment() -> dict[str, str]:
    excluded = (
        "COPILOT_",
        "GITHUB_COPILOT_",
        "OTEL_",
        "OPENAI_",
        "ANTHROPIC_",
        "AZURE_",
        "GOOGLE_",
        "GEMINI_",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if (key.upper() == "COPILOT_GITHUB_TOKEN" or not key.upper().startswith(excluded))
        and key.upper() not in {"NODE_OPTIONS", "BASH_ENV", "ENV"}
    }
    env["COPILOT_TELEMETRY_DISABLED"] = "true"
    return env


def session_options(system: str) -> dict:
    return {
        "system_message": {"mode": "replace", "content": system},
        "available_tools": [],
        "excluded_tools": ["builtin:*", "mcp:*", "custom:*"],
        "tools": [],
        "mcp_servers": {},
        "disabled_mcp_servers": ["github-mcp-server", "githubiq"],
        "custom_agents": [],
        "included_builtin_agents": [],
        "tool_search": {"enabled": False},
        "enable_config_discovery": False,
        "skip_custom_instructions": True,
        "skip_embedding_retrieval": True,
        "enable_on_demand_instruction_discovery": False,
        "enable_file_hooks": False,
        "enable_host_git_operations": False,
        "enable_session_store": False,
        "enable_session_telemetry": False,
        "enable_file_change_tracking": False,
        "enable_skills": False,
        "enable_experimental_mode": False,
        "custom_agents_local_only": True,
        "included_builtin_skills": [],
        "mcp_oauth_token_storage": "in-memory",
        "embedding_cache_storage": "in-memory",
        "skill_directories": [],
        "agent_directories": [],
        "hook_directories": [],
        "plugin_directories": [],
        "instruction_directories": [],
        "memory": {"enabled": False},
        "infinite_sessions": {"enabled": False},
        "autopilot": {"continuation_enabled": False, "max_continues": 0},
        "auto_mode_recovery": False,
        "request_extensions": False,
        "coauthor_enabled": False,
        "manage_schedule_enabled": False,
        "streaming": False,
    }


class EventAudit:
    def __init__(self, system: str = "", user: str = "") -> None:
        self.counts: Counter = Counter()
        self.usages: list[dict] = []
        self.checkpoint: dict | None = None
        self.violation: str | None = None
        self.system, self.user = system, user
        self.message_audit: list[dict] = []
        self.tool_counts: list[int] = []

    def permission(self, *_: object) -> PermissionDecisionReject:
        self.violation = "permission_requested"
        return PermissionDecisionReject()

    def observe(self, event: SessionEvent) -> None:
        raw = event.to_dict()
        kind, data = raw["type"], raw.get("data", {})
        self.counts[kind] += 1
        if raw.get("agentId") or data.get("agentId"):
            self.violation = "subagent_activity"
        if (
            kind.startswith(("tool.", "subagent.", "external_tool.", "hook."))
            or kind in {
                "session.error", "session.model_change", "session.truncation",
                "assistant.turn_retry", "model.call_failure", "session.handoff",
            }
            or kind.startswith(("session.compaction", "session.context_compaction"))
        ):
            self.violation = kind
        if kind == "assistant.message" and data.get("toolRequests"):
            self.violation = "assistant_tool_request"
        if kind == "session.mcp_server_status_changed" and data.get("status") in {
            "pending",
            "connected",
        }:
            self.violation = "mcp_initialization"
        if kind == "session.mcp_servers_loaded" and any(
            item.get("status") in {"pending", "connected"}
            for item in data.get("servers", [])
        ):
            self.violation = "mcp_initialization"
        if kind in {
            "model.model_call_success",
            "model.model_call_start",
            "model.model_call_started",
            "model.call_finished",
            "assistant.usage",
            "session.mcp_server_tools_loaded",
            "session.usage_info",
        } and any(
            (data.get(key) or 0) > 0
            for key in (
                "toolCount",
                "availableToolCount",
                "deferredToolCount",
                "toolTokenCount",
                "visibleToolCount",
                "toolDefinitionsTokens",
            )
        ):
            self.violation = "model_facing_tools"
        if kind in {"system.message", "user.message"}:
            content = data.get("content", "")
            expected = self.system if kind == "system.message" else self.user
            matches = content == expected
            self.message_audit.append({
                "kind": kind,
                "role": data.get("role"),
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "matches_sdk_input": matches,
            })
            if not matches:
                self.violation = "unexpected_message_content"
        if kind == "assistant.usage":
            keys = (
                "model", "responseModel", "modelProvider", "provider", "inputTokens",
                "outputTokens", "cacheReadTokens", "cacheWriteTokens", "reasoningTokens",
                "cost", "copilotUsage", "reasoningEffort", "finishReason", "isByok",
                "availableToolCount",
            )
            self.usages.append({key: data[key] for key in keys if key in data})
            if "availableToolCount" in data:
                self.tool_counts.append(data["availableToolCount"])
        if kind == "session.usage_checkpoint":
            self.checkpoint = {
                key: data[key]
                for key in ("totalNanoAiu", "totalPremiumRequests", "providerModelMetrics")
                if key in data
            }

    def metadata(self) -> dict:
        return {
            "event_counts": dict(self.counts),
            "inference_calls_observed": len(self.usages),
            "usage": list(self.usages),
            "accounting_checkpoint": self.checkpoint,
            "boundary_violation": self.violation,
            "message_audit": list(self.message_audit),
            "tool_counts_observed": list(self.tool_counts),
            "http_attempts": None,
            "usd_cost": None,
        }

    def verify(self, model: str) -> str:
        if self.violation:
            raise InferenceError("boundary_violation", "Unexpected runtime activity")
        if len(self.usages) != 1 or self.counts["model.call_start"] > 1:
            raise InferenceError(
                "unverified_attempts", "Expected exactly one observed inference call"
            )
        observed = self.usages[0].get("model")
        if observed != model:
            raise InferenceError("model_mismatch", "Observed model differs from request")
        if self.usages[0].get("isByok"):
            raise InferenceError("provider_mismatch", "Unexpected BYOK inference")
        if self.usages[0].get("finishReason") not in {None, "stop", "end_turn"}:
            raise InferenceError("incomplete_response", "Inference did not finish normally")
        return observed


class CopilotProvider:
    """Use as an async context manager; calls on one instance are serialized."""

    def __init__(self, executable: str | Path | None = None) -> None:
        resolved = str(executable) if executable is not None else shutil.which("copilot")
        if not resolved or not Path(resolved).is_file():
            raise InferenceError("configuration", "Copilot executable was not found")
        self.executable = str(Path(resolved).resolve())
        if Path(resolved).suffix.lower() in {".cmd", ".bat", ".ps1"}:
            raise InferenceError("configuration", "Use the native Copilot executable")
        self._client = None
        self._workspace = None
        self._lock = asyncio.Lock()
        self._poisoned = False
        self._version = None
        self._models: dict = {}
        self._last_receipt: dict = {}
        self._binary_hash = hashlib.sha256(Path(self.executable).read_bytes()).hexdigest()

    async def __aenter__(self) -> CopilotProvider:
        if self._client is not None or self._poisoned:
            raise InferenceError("lifecycle", "Provider is already started or closed")
        self._workspace = tempfile.TemporaryDirectory(prefix="falkor-inference-")
        root = Path(self._workspace.name)
        try:
            return await self._start(root)
        except BaseException as error:
            await self.close()
            if isinstance(error, asyncio.CancelledError):
                raise
            raise InferenceError(
                "startup", "Could not start authenticated Copilot runtime"
            ) from error

    async def _start(self, root: Path) -> CopilotProvider:
        self._client = CopilotClient(
            connection=RuntimeConnection.for_stdio(
                path=self.executable,
                args=(
                    "--no-auto-update",
                    "--disable-builtin-mcps",
                    "--no-custom-instructions",
                    "--no-ask-user",
                    "--disable-client-telemetry",
                    "--log-dir", str(root / "logs"),
                ),
            ),
            mode="copilot-cli",
            working_directory=str(root),
            env=child_environment(),
            log_level="none",
            use_logged_in_user=True,
        )
        async with asyncio.timeout(45):
            await self._client.start()
            self._version = (await self._client.get_status()).version
            self._models = {
                item.id: item.to_dict() for item in await self._client.list_models()
            }
            if not self._models:
                raise InferenceError(
                    "authentication", "No account-visible models; check Copilot login"
                )
        return self

    async def __aexit__(self, _type: object, error: BaseException | None, _tb: object) -> None:
        try:
            await self.close()
        except InferenceError as cleanup_error:
            if isinstance(error, InferenceError):
                cleanup_error.receipt = {
                    **error.receipt, "primary_error_class": error.code,
                    "runtime_shutdown_error": cleanup_error.code,
                }
            raise

    async def close(self) -> None:
        try:
            cancelled = await finish_cleanup(self._shutdown())
        except InferenceError as error:
            error.receipt = {
                **self._last_receipt, "runtime_shutdown_error": error.code,
            }
            raise
        if cancelled:
            raise asyncio.CancelledError

    async def _shutdown(self) -> None:
        async with self._lock:
            self._poisoned = True
            shutdown_error = None
            try:
                if self._client is not None:
                    async with asyncio.timeout(20):
                        errors = await self._client.stop()
                    if errors:
                        raise InferenceError("cleanup", "Runtime shutdown reported errors")
            except (Exception, asyncio.CancelledError) as error:
                try:
                    async with asyncio.timeout(10):
                        await self._client.force_stop()
                except (Exception, asyncio.CancelledError) as forced_error:
                    raise InferenceError(
                        "cleanup", "Owned runtime could not be stopped"
                    ) from forced_error
                shutdown_error = InferenceError(
                    "cleanup", "Graceful shutdown failed; owned runtime was force-stopped"
                )
                shutdown_error.__cause__ = error
            self._client = None
            if self._workspace is not None:
                try:
                    self._workspace.cleanup()
                except OSError as error:
                    raise InferenceError(
                        "cleanup", "Owned workspace cleanup failed"
                    ) from error
                self._workspace = None
            if shutdown_error:
                raise shutdown_error

    async def _delete_session(
        self, session: CopilotSession | None, session_id: str, completed: bool, receipt: dict
    ) -> None:
        errors = []
        if session is not None and not completed:
            try:
                async with asyncio.timeout(5):
                    await session.abort()
            except (Exception, asyncio.CancelledError) as error:
                errors.append({"operation": "abort", "error_class": type(error).__name__})
        try:
            async with asyncio.timeout(10):
                await self._client.delete_session(session_id)
                receipt["session_deleted"] = True
        except (Exception, asyncio.CancelledError) as error:
            errors.append({"operation": "delete", "error_class": type(error).__name__})
        if errors:
            self._poisoned = True
            receipt["cleanup_errors"] = errors
            raise InferenceError(
                "cleanup", "Session cleanup failed; provider cannot be reused"
            )

    def configuration(self) -> dict:
        return {
            "provider": "github-copilot",
            "sdk_version": importlib.metadata.version("github-copilot-sdk"),
            "runtime_version": self._version,
            "binary_sha256": self._binary_hash,
            "capabilities": dict(CAPABILITIES),
        }

    def models(self) -> list[dict]:
        return copy.deepcopy(list(self._models.values()))

    async def generate(self, request: InferenceRequest) -> InferenceResponse:
        system, user, validator = request.prepared()
        async with self._lock:
            if self._client is None or self._poisoned:
                raise InferenceError("lifecycle", "Provider is closed or unsafe to reuse")
            if hashlib.sha256(Path(self.executable).read_bytes()).hexdigest() != (
                self._binary_hash
            ):
                raise InferenceError("configuration", "Copilot executable changed")
            model = self._models.get(request.model)
            if model is None or model.get("policy", {}).get("state") == "disabled":
                raise InferenceError("model_unavailable", "Model is not enabled in catalog")
            if model.get("provider", {}).get("kind") != "copilot":
                raise InferenceError("provider_mismatch", "Model is not a Copilot model")
            if request.reasoning_effort is not None and request.reasoning_effort not in (
                model.get("supportedReasoningEfforts") or []
            ):
                raise InferenceError(
                    "unsupported_control", "Model does not advertise this reasoning effort"
                )
            audit, session_id = EventAudit(system, user), str(uuid4())
            receipt = {
                **self.configuration(),
                "session_id": session_id,
                "requested_model": request.model,
                "observed_model": None,
                "requested_reasoning_effort": request.reasoning_effort,
                "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
                "user_sha256": hashlib.sha256(user.encode("utf-8")).hexdigest(),
                "dispatched": False,
                "session_deleted": False,
                "adapter_attempts": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "cache_mode": "no_application_result_cache_backend_cache_uncontrolled",
            }
            self._last_receipt = receipt
            session, completed, failure = None, False, None
            started = time.monotonic()
            try:
                async with asyncio.timeout(request.timeout_seconds):
                    session = await self._client.create_session(
                        session_id=session_id,
                        model=request.model,
                        reasoning_effort=request.reasoning_effort,
                        on_permission_request=audit.permission,
                        on_event=audit.observe,
                        **session_options(system),
                    )
                    receipt["dispatched"] = True
                    receipt["adapter_attempts"] = 1
                    response = await session.send_and_wait(
                        user, timeout=request.timeout_seconds, agent_mode="interactive"
                    )
                    completed = True
                    receipt["observed_model"] = audit.verify(request.model)
                    text = getattr(getattr(response, "data", None), "content", None)
                    if isinstance(text, str):
                        receipt["response_sha256"] = hashlib.sha256(
                            text.encode("utf-8")
                        ).hexdigest()
                    parsed = validate_content(text, validator)
            except InferenceError as error:
                failure = error
            except TimeoutError:
                failure = InferenceError("timeout", "Inference deadline exceeded")
            except asyncio.CancelledError as error:
                failure = error
            except Exception as error:
                failure = InferenceError(
                    "transport", "Copilot SDK request failed; no automatic retry"
                )
                failure.__cause__ = error
            finally:
                try:
                    cancelled = await finish_cleanup(
                        self._delete_session(session, session_id, completed, receipt)
                    )
                    if cancelled:
                        self._poisoned = True
                        if failure is None:
                            failure = asyncio.CancelledError()
                except InferenceError as error:
                    receipt["primary_error_class"] = (
                        failure.code if isinstance(failure, InferenceError) else None
                    )
                    failure = error
                receipt.update(audit.metadata())
                receipt["elapsed_seconds"] = time.monotonic() - started
            if failure is not None:
                if isinstance(failure, InferenceError):
                    failure.receipt = receipt
                raise failure
            return InferenceResponse(text=text, parsed=parsed, receipt=receipt)
