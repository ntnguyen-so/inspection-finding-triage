from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from llm_inference import AzureOpenAIProvider, InferenceError, InferenceRequest
from llm_inference.__main__ import main as cli_main, run as cli_run
from llm_inference.azure import azure_base_url
from tools.compare_inference import (
    BUDGET, DEFAULT_COPILOT_MODEL, FIXTURE_VERSION, main as compare_main,
    run as compare_run, summarize,
)
from tools.probe_inference import run as probe_run

ENDPOINT = "https://fixture.openai.azure.com"
KEY = "API_KEY_CANARY_NEVER_LOG"
SCHEMA = {
    "type": "object", "properties": {"value": {"type": "integer"}},
    "required": ["value"], "additionalProperties": False,
}


def completion(content='{"value":5}', **overrides):
    return {
        "id": "public-fixture", "object": "chat.completion", "created": 0,
        "model": "gpt-6-sol-2026-09-22",
        "choices": [{
            "index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": content},
        }],
        "usage": {"prompt_tokens": 15, "completion_tokens": 6, "total_tokens": 21},
        **overrides,
    }


def responses_result(content='{"value":5}', **overrides):
    return {
        "id": "public-responses-fixture", "object": "response", "created_at": 0,
        "model": "observed-responses-model", "status": "completed",
        "error": None, "incomplete_details": None,
        "output": [{
            "id": "private-reasoning", "type": "reasoning", "status": "completed",
            "summary": [{"type": "summary_text", "text": "PRIVATE_REASONING_CANARY"}],
            "encrypted_content": "PRIVATE_ENCRYPTED_CANARY",
        }, {
            "id": "public-message", "type": "message", "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": content, "annotations": []}],
        }],
        "usage": {
            "input_tokens": 15, "input_tokens_details": {"cached_tokens": 3},
            "output_tokens": 10, "output_tokens_details": {"reasoning_tokens": 4},
            "total_tokens": 25,
        },
        **overrides,
    }


def request(**overrides):
    return InferenceRequest(**{
        "model": "panel-deployment", "system": "Transform the input.", "user": "2 + 3",
        "response_schema": SCHEMA, **overrides,
    })


def provider(handler, **overrides):
    return AzureOpenAIProvider(**{
        "endpoint": ENDPOINT, "api_key": KEY,
        "http_transport": httpx.MockTransport(handler), **overrides,
    })


class ConfigurationTests(unittest.TestCase):
    def test_comparison_defaults_to_fast_copilot_model(self):
        with (
            patch("sys.argv", ["compare_inference", "--output", "unused.json"]),
            patch("tools.compare_inference.run", new_callable=AsyncMock, return_value=0) as run,
        ):
            self.assertEqual(0, compare_main())
        self.assertEqual(DEFAULT_COPILOT_MODEL, run.call_args.args[0].copilot_model)

    def test_only_validated_azure_origins_and_paths_are_allowed(self):
        for endpoint in (
            "http://fixture.openai.azure.com", "https://evil.example",
            "https://fixture.openai.azure.com.evil.example",
            "https://user:password@fixture.openai.azure.com",
            "https://fixture.openai.azure.com/?key=secret",
            "https://fixture.openai.azure.com/path",
            "https://fixture.openai.azure.com:8443", "",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(InferenceError):
                azure_base_url(endpoint)
        self.assertEqual(azure_base_url(ENDPOINT + "/openai/v1/"), ENDPOINT + "/openai/v1/")

    def test_configuration_rejects_ambiguous_auth_and_bad_controls(self):
        for overrides in (
            {"auth": "fallback"}, {"auth": "entra"}, {"api_key": ""},
            {"native_json_schema": "true"}, {"max_completion_tokens": True},
            {"max_completion_tokens": 0}, {"api": "automatic"},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(InferenceError):
                provider(lambda _: httpx.Response(200, json=completion()), **overrides)

    def test_cli_api_parser_selection_and_default(self):
        for flags, selected in (([], "chat_completions"), (["--azure-api", "responses"], "responses")):
            with (
                self.subTest(api=selected),
                patch("sys.argv", ["llm_inference", "--provider", "azure", "--request", "-", *flags]),
                patch("sys.stdout", io.StringIO()),
                patch("llm_inference.__main__.run", new_callable=AsyncMock, return_value={}) as run,
            ):
                self.assertEqual(cli_main(), 0)
                self.assertEqual(run.call_args.args[0].azure_api, selected)
        with (
            patch("sys.argv", ["llm_inference", "--request", "-", "--azure-api", "fallback"]),
            patch("sys.stderr", io.StringIO()),
            self.assertRaises(SystemExit) as caught,
        ):
            cli_main()
        self.assertEqual(caught.exception.code, 2)


class AzureTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_wire_messages_usage_and_no_agent_or_retries(self):
        dispatched = []

        def handler(req):
            dispatched.append(req)
            return httpx.Response(200, json=completion())

        async with provider(handler, max_completion_tokens=1024) as azure:
            response = await azure.generate(request(reasoning_effort="low"))
        body = json.loads(dispatched[0].content)
        self.assertEqual(body["model"], "panel-deployment")
        self.assertEqual([x["role"] for x in body["messages"]], ["system", "user"])
        self.assertEqual(body["messages"][1]["content"], "2 + 3")
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(body["max_completion_tokens"], 1024)
        self.assertNotIn("tools", body)
        self.assertNotIn("response_format", body)
        self.assertEqual(response.parsed, {"value": 5})
        self.assertEqual(response.receipt["http_dispatches_observed"], 1)
        self.assertTrue(response.receipt["wire_message_hashes_match"])
        self.assertEqual(response.receipt["usage"]["prompt_tokens"], 15)
        self.assertEqual(response.receipt["sdk_retries"], 0)
        self.assertIsNone(response.receipt["usd_cost"])
        self.assertNotIn(KEY, json.dumps(response.receipt))
        self.assertIsNone(azure._client)

    async def test_native_json_is_explicit_and_still_locally_validated(self):
        bodies = []

        def handler(req):
            bodies.append(json.loads(req.content))
            return httpx.Response(200, json=completion())

        async with provider(handler, native_json_schema=True) as azure:
            result = await azure.generate(request())
        self.assertEqual(result.receipt["schema_mode"], "native")
        self.assertTrue(bodies[0]["response_format"]["json_schema"]["strict"])
        self.assertEqual(bodies[0]["response_format"]["json_schema"]["schema"], SCHEMA)

    async def test_invalid_native_object_schema_fails_without_http(self):
        calls = []

        def handler(req):
            calls.append(req)
            return httpx.Response(200, json=completion())

        async with provider(handler, native_json_schema=True) as azure:
            for schema in (
                {"type": "object", "properties": {"value": {"type": "integer"}}},
                {**SCHEMA, "properties": {"value": True}},
                {**SCHEMA, "properties": {"value": {"type": "array", "items": False}}},
            ):
                with self.subTest(schema=schema), self.assertRaises(InferenceError) as caught:
                    await azure.generate(request(response_schema=schema))
                self.assertEqual(caught.exception.code, "invalid_schema")
        self.assertFalse(calls)

    async def test_azure_unsupported_constraints_are_still_enforced_locally(self):
        schema = {
            "type": "object", "properties": {"uniqueItems": {
                "type": "array", "items": {"type": "string", "minLength": 3, "maxLength": 5},
                "uniqueItems": True, "minItems": 1, "maxItems": 2,
            }, "bounded": {"type": "integer", "minimum": 1, "maximum": 10}},
            "required": ["uniqueItems", "bounded"], "additionalProperties": False,
        }
        bodies = []
        replies = iter(('{"uniqueItems":["same","same"],"bounded":5}',
                        '{"uniqueItems":["same"],"bounded":0}',
                        '{"uniqueItems":["xx"],"bounded":5}'))

        def handler(req):
            bodies.append(json.loads(req.content))
            return httpx.Response(200, json=completion(next(replies)))

        async with provider(handler, native_json_schema=True) as azure:
            for _ in range(3):
                with self.assertRaises(InferenceError) as caught:
                    await azure.generate(request(response_schema=schema))
                self.assertEqual("schema_violation", caught.exception.code)
        wire = bodies[0]["response_format"]["json_schema"]["schema"]
        self.assertNotIn("uniqueItems", wire["properties"]["uniqueItems"])
        self.assertNotIn("minimum", wire["properties"]["bounded"])
        self.assertNotIn("minLength", wire["properties"]["uniqueItems"]["items"])
        self.assertTrue(schema["properties"]["uniqueItems"]["uniqueItems"])
        self.assertEqual(3, len(bodies))

    async def test_no_retry_and_no_secret_in_error_receipts(self):
        for status, expected in (
            (401, "authentication"), (403, "permission_denied"), (404, "not_found"),
            (429, "rate_limit"), (500, "provider_error"), (400, "bad_request"),
        ):
            calls = []

            def handler(req):
                calls.append(req)
                return httpx.Response(status, json={"error": {"message": KEY}})

            with self.subTest(status=status):
                async with provider(handler) as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request())
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(calls), 1)
                self.assertEqual(caught.exception.receipt["http_dispatches_observed"], 1)
                self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))
                self.assertNotIn(KEY, repr(caught.exception))
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.receipt["usage"])

    async def test_redirect_is_not_followed_with_credentials(self):
        hosts = []

        def handler(req):
            hosts.append(req.url.host)
            return httpx.Response(307, headers={"Location": "https://evil.example/inference"})

        async with provider(handler) as azure:
            with self.assertRaises(InferenceError):
                await azure.generate(request())
        self.assertEqual(hosts, ["fixture.openai.azure.com"])

    async def test_connection_failure_is_one_observed_dispatch(self):
        calls = []

        def handler(req):
            calls.append(req)
            raise httpx.ConnectError(KEY, request=req)

        async with provider(handler) as azure:
            with self.assertRaises(InferenceError) as caught:
                await azure.generate(request())
        self.assertEqual(caught.exception.code, "transport")
        self.assertEqual(len(calls), 1)
        self.assertFalse(caught.exception.receipt["billing_complete"])
        self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))

    async def test_timeout_and_cancellation_keep_unknown_billing(self):
        dispatched = asyncio.Event()
        calls = 0

        async def handler(req):
            nonlocal calls
            calls += 1
            dispatched.set()
            if calls == 1:
                raise httpx.ReadTimeout(KEY, request=req)
            await asyncio.sleep(10)

        async with provider(handler) as azure:
            with self.assertRaises(InferenceError) as caught:
                await azure.generate(request())
            self.assertEqual(caught.exception.code, "timeout")
            self.assertEqual(caught.exception.receipt["http_dispatches_observed"], 1)
            self.assertIsNone(caught.exception.receipt["usage"])
            dispatched.clear()
            task = asyncio.create_task(azure.generate(request()))
            await dispatched.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(azure._last_receipt["cancelled"])

    async def test_overall_deadline_does_not_invent_an_http_dispatch(self):
        async def handler(req):
            await asyncio.sleep(10)

        async with provider(handler) as azure:
            with self.assertRaises(InferenceError) as caught:
                await azure.generate(request(timeout_seconds=0.001))
        self.assertEqual(caught.exception.code, "timeout")
        self.assertLessEqual(caught.exception.receipt["http_dispatches_observed"], 1)
        self.assertIsNone(caught.exception.receipt["usage"])

    async def test_refusal_filter_truncation_tools_and_bad_outputs_are_distinct(self):
        fixtures = []
        for reason, expected in (("length", "incomplete_response"), ("content_filter", "content_filter")):
            body = completion()
            body["choices"][0]["finish_reason"] = reason
            fixtures.append((body, expected))
        refusal = completion()
        refusal["choices"][0]["message"]["refusal"] = "PRIVATE_REFUSAL_TEXT"
        fixtures.append((refusal, "refusal"))
        tool = completion()
        tool["choices"][0]["message"]["tool_calls"] = [{
            "id": "fixture-tool", "type": "function",
            "function": {"name": "forbidden", "arguments": "{}"},
        }]
        fixtures.append((tool, "boundary_violation"))
        fixtures += [
            (completion("```json\n{\"value\":5}\n```"), "malformed_json"),
            (completion('{"value":true}'), "schema_violation"),
            (completion(None), "empty_response"),
            (completion(choices=[]), "invalid_response"),
            (completion(prompt_filter_results=[{"filtered": True}]), "content_filter"),
        ]
        for body, expected in fixtures:
            with self.subTest(expected=expected):
                async with provider(lambda _: httpx.Response(200, json=body)) as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request())
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(caught.exception.receipt["usage"]["total_tokens"], 21)
                self.assertNotIn("PRIVATE_REFUSAL_TEXT", json.dumps(caught.exception.to_dict()))

    async def test_entra_explicitly_uses_token_provider_and_closes_credential(self):
        class Credential:
            closed = False

            async def close(self):
                self.closed = True

        credential = Credential()

        async def token():
            return "BEARER_TOKEN_CANARY_NEVER_LOG"

        headers = []

        def handler(req):
            headers.append(req.headers["Authorization"])
            return httpx.Response(200, json=completion())

        with (
            patch("llm_inference.azure.DefaultAzureCredential", return_value=credential),
            patch("llm_inference.azure.get_bearer_token_provider", return_value=token),
            patch.dict("os.environ", {"AZURE_OPENAI_API_KEY": "UNUSED_KEY_CANARY"}),
        ):
            async with provider(handler, auth="entra", api_key=None) as azure:
                response = await azure.generate(request())
        self.assertEqual(headers, ["Bearer BEARER_TOKEN_CANARY_NEVER_LOG"])
        self.assertTrue(credential.closed)
        self.assertNotIn("CANARY", json.dumps(response.receipt))

    async def test_azure_cli_does_not_construct_copilot(self):
        azure = provider(lambda _: httpx.Response(200, json=completion()))
        args = argparse.Namespace(
            provider="azure", models=False, executable=None, azure_auth=None,
            azure_native_json=False, azure_max_completion_tokens=None, request="-",
        )
        import io
        with (
            patch("sys.stdin", io.StringIO(json.dumps({
                "model": "panel-deployment", "system": "s", "user": "u",
                "response_schema": SCHEMA,
            }))),
            patch("llm_inference.__main__.AzureOpenAIProvider", return_value=azure),
            patch("llm_inference.__main__.CopilotProvider") as copilot,
        ):
            result = await cli_run(args)
        self.assertEqual(result["status"], "succeeded")
        copilot.assert_not_called()


class AzureResponsesTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_responses_wire_controls_usage_models_and_hashes(self):
        dispatched = []
        reply = responses_result()
        http_response = httpx.Response(200, json=reply)
        inference_request = request(reasoning_effort="high", timeout_seconds=37)

        def handler(req):
            dispatched.append(req)
            self.assertEqual(req.extensions["timeout"]["read"], 37)
            return http_response

        async with provider(
            handler, api="responses", native_json_schema=True, max_completion_tokens=2048,
        ) as azure:
            self.assertEqual(azure._client.max_retries, 0)
            self.assertFalse(azure._http.follow_redirects)
            result = await azure.generate(inference_request)
        self.assertEqual(len(dispatched), 1)
        wire = dispatched[0]
        self.assertEqual(wire.method, "POST")
        self.assertEqual(str(wire.url), ENDPOINT + "/openai/v1/responses")
        body = json.loads(wire.content)
        system, user, _ = inference_request.prepared()
        self.assertEqual(body["input"], [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
        self.assertEqual(body["model"], "panel-deployment")
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual(body["max_output_tokens"], 2048)
        self.assertEqual(body["text"], {"format": {
            "type": "json_schema", "name": "inference_response", "strict": True,
            "schema": SCHEMA,
        }})
        self.assertEqual(body["tools"], [])
        self.assertEqual(body["tool_choice"], "none")
        for flag in ("parallel_tool_calls", "store", "background", "stream"):
            self.assertIs(body[flag], False)
        for absent in (
            "messages", "instructions", "response_format", "reasoning_effort",
            "max_completion_tokens", "previous_response_id", "conversation",
        ):
            self.assertNotIn(absent, body)
        self.assertEqual(result.text, '{"value":5}')
        self.assertEqual(result.parsed, {"value": 5})
        receipt = result.receipt
        self.assertEqual(receipt["api"], "azure-openai-v1-responses")
        self.assertEqual(receipt["max_completion_tokens"], 2048)
        self.assertEqual(receipt["requested_model"], "panel-deployment")
        self.assertEqual(receipt["observed_model"], "observed-responses-model")
        self.assertEqual(receipt["usage"], reply["usage"])
        self.assertEqual(receipt["response_status"], "completed")
        self.assertEqual(receipt["http_status"], 200)
        self.assertEqual(receipt["adapter_attempts"], 1)
        self.assertEqual(receipt["http_dispatches_observed"], 1)
        self.assertEqual(receipt["sdk_retries"], 0)
        self.assertTrue(receipt["wire_message_hashes_match"])
        self.assertTrue(receipt["billing_complete"])
        self.assertGreaterEqual(receipt["elapsed_seconds"], 0)
        for key, raw in (
            ("system_sha256", system.encode()), ("user_sha256", user.encode()),
            ("wire_body_sha256", wire.content),
            ("wire_response_sha256", http_response.content),
            ("response_sha256", result.text.encode()),
        ):
            self.assertEqual(receipt[key], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("PRIVATE_", json.dumps(receipt))
        self.assertNotIn(KEY, json.dumps(receipt))

    async def test_native_projection_preserves_refs_and_original_local_constraints(self):
        schema = {
            "type": "object",
            "$defs": {"words": {
                "type": "array", "items": {"type": "string", "minLength": 3, "maxLength": 5},
                "minItems": 1, "maxItems": 2, "uniqueItems": True,
            }},
            "properties": {
                "words": {"$ref": "#/$defs/words"},
                "value": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["words", "value"], "additionalProperties": False,
        }
        original = json.dumps(schema, sort_keys=True)
        for bad in (
            {"words": ["same", "same"], "value": 5},
            {"words": ["xx"], "value": 5},
            {"words": ["lengthy"], "value": 5},
            {"words": [], "value": 5},
            {"words": ["one", "two", "three"], "value": 5},
            {"words": ["valid"], "value": 0},
            {"words": ["valid"], "value": 11},
        ):
            bodies = []

            def handler(req):
                bodies.append(json.loads(req.content))
                return httpx.Response(200, json=responses_result(json.dumps(bad)))

            with self.subTest(bad=bad):
                async with provider(handler, api="responses", native_json_schema=True) as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request(response_schema=schema))
                self.assertEqual(caught.exception.code, "schema_violation")
                self.assertEqual(caught.exception.receipt["http_dispatches_observed"], 1)
                self.assertTrue(caught.exception.receipt["wire_message_hashes_match"])
                self.assertEqual(caught.exception.receipt["usage"]["output_tokens"], 10)
                wire = bodies[0]["text"]["format"]["schema"]
                self.assertEqual(wire["$defs"]["words"], {
                    "type": "array", "items": {"type": "string"},
                })
                self.assertEqual(wire["properties"]["words"], {"$ref": "#/$defs/words"})
                self.assertEqual(wire["properties"]["value"], {"type": "integer"})
                self.assertEqual(json.dumps(schema, sort_keys=True), original)

    async def test_responses_wire_hook_rejects_changed_messages_controls_and_endpoint(self):
        for mutation in ("role", "message", "store", "tools", "chat/completions", "responses/other"):
            with self.subTest(mutation=mutation):
                dispatched, returned = [], []

                def handler(req):
                    dispatched.append(req)
                    return httpx.Response(200, json=responses_result())

                async with provider(handler, api="responses") as azure:
                    build_request = azure._http.build_request

                    def tampered_request(*args, **kwargs):
                        wire = build_request(*args, **kwargs)
                        body = json.loads(wire.content)
                        destination = wire.url
                        if mutation == "role":
                            body["input"][0]["role"] = "developer"
                        elif mutation == "message":
                            body["input"][1]["content"] = KEY
                        elif mutation == "store":
                            body["store"] = True
                        elif mutation == "tools":
                            body["tools"] = [{"type": "web_search"}]
                        else:
                            destination = ENDPOINT + "/openai/v1/" + mutation
                        headers = wire.headers.copy()
                        del headers["content-length"]
                        return httpx.Request(
                            wire.method, destination, json=body,
                            headers=headers, extensions=wire.extensions,
                        )

                    with patch.object(
                        azure._http, "build_request", side_effect=tampered_request,
                    ) as build:
                        with self.assertRaises(InferenceError) as caught:
                            returned.append(await azure.generate(request()))
                    self.assertEqual(build.call_count, 1)
                self.assertEqual(caught.exception.code, "boundary_violation")
                receipt = caught.exception.receipt
                self.assertEqual(receipt["adapter_attempts"], 1)
                self.assertEqual(receipt["http_dispatches_observed"], 1)
                self.assertFalse(receipt.get("wire_message_hashes_match", False))
                self.assertIsNone(receipt["usage"])
                self.assertFalse(receipt["billing_complete"])
                self.assertNotIn("response_sha256", receipt)
                self.assertEqual(dispatched, [])
                self.assertEqual(returned, [])
                self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))
                self.assertIsNone(caught.exception.__cause__)

    async def test_untrusted_transport_inference_error_is_not_promoted_to_boundary_failure(self):
        def handler(req):
            raise InferenceError("boundary_violation", KEY)

        async with provider(handler, api="responses") as azure:
            with self.assertRaises(InferenceError) as caught:
                await azure.generate(request())
        self.assertEqual(caught.exception.code, "transport")
        self.assertEqual(caught.exception.receipt["http_dispatches_observed"], 1)
        self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))
        self.assertIsNone(caught.exception.__cause__)

    async def test_responses_reject_incomplete_refusal_operational_and_nontext_output(self):
        message = responses_result()["output"][1]
        fixtures = [
            (responses_result(status="incomplete", incomplete_details={"reason": "max_output_tokens"}),
             "incomplete_response"),
            (responses_result(status="in_progress"), "incomplete_response"),
            (responses_result(status="failed", error={"code": "server_error", "message": KEY}),
             "provider_error"),
            (responses_result(incomplete_details={"reason": "max_output_tokens"}),
             "incomplete_response"),
            (responses_result(error={"code": "server_error", "message": KEY}), "provider_error"),
            (responses_result(output=[{**message, "status": "incomplete"}]), "incomplete_response"),
            (responses_result(output=[{
                "id": "reasoning", "type": "reasoning", "status": "incomplete", "summary": [],
            }, message]), "incomplete_response"),
            (responses_result(output=[{**message, "content": [
                {"type": "refusal", "refusal": "PRIVATE_REFUSAL_CANARY"},
            ]}]), "refusal"),
            (responses_result(output=[{
                "id": "tool", "type": "function_call", "call_id": "call", "name": "forbidden",
                "arguments": "PRIVATE_TOOL_CANARY",
            }, message]), "boundary_violation"),
            (responses_result(output=[{"id": "unknown", "type": "future_operation"}, message]),
             "boundary_violation"),
            (responses_result(output=[{**message, "role": "user"}]), "invalid_response"),
            (responses_result(output=[{**message, "content": [
                {"type": "output_audio", "data": "PRIVATE_AUDIO_CANARY"},
            ]}]), "invalid_response"),
            (responses_result(output=[{**message, "content": [
                {"type": "output_text", "text": None, "annotations": []},
            ]}]), "invalid_response"),
            (responses_result(output=[]), "empty_response"),
            (responses_result(content='{"value":true}'), "schema_violation"),
            (responses_result(content='```json\n{"value":5}\n```'), "malformed_json"),
        ]
        for reply, expected in fixtures:
            with self.subTest(expected=expected, output=reply["output"]):
                async with provider(
                    lambda _: httpx.Response(200, json=reply), api="responses",
                ) as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request())
                self.assertEqual(caught.exception.code, expected)
                receipt = caught.exception.receipt
                self.assertEqual(receipt["api"], "azure-openai-v1-responses")
                self.assertEqual(receipt["http_dispatches_observed"], 1)
                self.assertEqual(receipt["usage"], reply["usage"])
                self.assertEqual(receipt["http_status"], 200)
                self.assertNotIn("PRIVATE_", json.dumps(caught.exception.to_dict()))
                self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))

    async def test_responses_http_errors_never_retry_or_fall_back(self):
        for status, expected in (
            (429, "rate_limit"), (500, "provider_error"), (400, "bad_request"),
            (401, "authentication"), (307, "bad_request"),
        ):
            calls = []

            def handler(req):
                calls.append(req)
                return httpx.Response(
                    status, json={"error": {"message": KEY}},
                    headers={"Location": "https://evil.example/response"},
                )

            with self.subTest(status=status):
                async with provider(handler, api="responses") as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request())
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(calls), 1)
                self.assertEqual(str(calls[0].url), ENDPOINT + "/openai/v1/responses")
                receipt = caught.exception.receipt
                self.assertEqual(receipt["http_dispatches_observed"], 1)
                self.assertEqual(receipt["http_status"], status)
                self.assertTrue(receipt["wire_message_hashes_match"])
                self.assertFalse(receipt["billing_complete"])
                self.assertIsNone(receipt["usage"])
                self.assertNotIn(KEY, json.dumps(caught.exception.to_dict()))
                self.assertIsNone(caught.exception.__cause__)

    async def test_screened_visible_draft_survives_local_rejection_without_reasoning_or_wire_body(self):
        for content, code in (('{"value":true}', "schema_violation"), ("invalid JSON", "malformed_json")):
            with self.subTest(code=code):
                async with provider(
                    lambda _: httpx.Response(200, json=responses_result(content)), api="responses",
                ) as azure:
                    with self.assertRaises(InferenceError) as caught:
                        await azure.generate(request())
                self.assertEqual(code, caught.exception.code)
                self.assertEqual(content, caught.exception.response_text)
                self.assertNotIn("PRIVATE_", caught.exception.response_text)
                self.assertNotIn(content, json.dumps(caught.exception.to_dict()))

    async def test_absent_usage_is_unknown_and_plain_text_is_visible_only(self):
        async with provider(
            lambda _: httpx.Response(200, json=responses_result("Visible answer.", usage=None)),
            api="responses",
        ) as azure:
            result = await azure.generate(request(response_schema=None))
        self.assertEqual(result.text, "Visible answer.")
        self.assertIsNone(result.parsed)
        self.assertIsNone(result.receipt["usage"])
        self.assertFalse(result.receipt["billing_complete"])
        self.assertNotIn("PRIVATE_", json.dumps(result.receipt))

    async def test_cli_passes_responses_selection_and_rejects_it_for_copilot(self):
        azure = provider(
            lambda _: httpx.Response(200, json=responses_result()), api="responses",
        )
        args = argparse.Namespace(
            provider="azure", models=False, executable=None, azure_auth=None,
            azure_api="responses", azure_native_json=True, azure_max_completion_tokens=2048,
            request="-",
        )
        with (
            patch("sys.stdin", io.StringIO(json.dumps({
                "model": "panel-deployment", "system": "s", "user": "u",
                "response_schema": SCHEMA,
            }))),
            patch("llm_inference.__main__.AzureOpenAIProvider", return_value=azure) as factory,
            patch("llm_inference.__main__.CopilotProvider") as copilot,
        ):
            result = await cli_run(args)
        self.assertEqual(result["receipt"]["api"], "azure-openai-v1-responses")
        factory.assert_called_once_with(
            auth="api_key", api="responses", native_json_schema=True, max_completion_tokens=2048,
        )
        copilot.assert_not_called()
        args.provider = "copilot"
        with self.assertRaises(InferenceError) as caught:
            await cli_run(args)
        self.assertEqual(caught.exception.code, "unsupported_control")


class ComparisonTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_language_fixtures_are_read_only_before_client_startup(self):
        for runner, scope in (
            (compare_run, "synthetic_azure_copilot_compatibility"),
            (probe_run, "synthetic_transport_not_triage_acceptance"),
        ):
            with (
                self.subTest(scope=scope),
                tempfile.TemporaryDirectory() as work,
                patch.dict("os.environ", {
                    "AZURE_OPENAI_ENDPOINT": ENDPOINT, "AZURE_OPENAI_API_KEY": KEY,
                }),
                patch("tools.compare_inference.AzureOpenAIProvider.__aenter__") as azure_start,
                patch("tools.probe_inference.CopilotProvider.__aenter__") as copilot_start,
            ):
                path = Path(work) / "historical.json"
                original = json.dumps({"scope": scope, "records": []}).encode()
                path.write_bytes(original)
                args = argparse.Namespace(
                    output=str(path), azure_deployment="panel", azure_auth="api_key",
                    copilot_model="gpt-6-sol", azure_only=False, case=None, include_native=False,
                )
                with self.assertRaises(InferenceError) as caught:
                    await runner(args)
                self.assertEqual(caught.exception.code, "configuration")
                self.assertEqual(path.read_bytes(), original)
                azure_start.assert_not_called()
                copilot_start.assert_not_called()

    async def test_resuming_does_not_hide_a_retained_shutdown_failure(self):
        async def handler(req):
            return httpx.Response(200, json=completion("SYSTEM_OK"))

        azure = provider(handler)
        close = azure.close

        async def failing_close():
            await close()
            raise InferenceError("cleanup", "Synthetic shutdown failure")

        with (
            tempfile.TemporaryDirectory() as work,
            patch("tools.compare_inference.cases", return_value={
                "role": ({"system": "Reply SYSTEM_OK.", "user": "Go."}, "SYSTEM_OK"),
            }),
            patch("tools.compare_inference.provenance", return_value={"source_sha256": {}}),
            patch("tools.compare_inference.AzureOpenAIProvider", return_value=azure) as factory,
        ):
            path = Path(work) / "ledger.json"
            args = argparse.Namespace(
                output=str(path), azure_deployment="panel", azure_auth="api_key",
                copilot_model="gpt-6-sol", azure_only=True, case=None, include_native=False,
            )
            with patch.object(azure, "close", failing_close):
                with self.assertRaises(InferenceError):
                    await compare_run(args)
            self.assertEqual(json.loads(path.read_text())["records"][0]["status"], "pass")
            factory.return_value = provider(handler)
            self.assertEqual(await compare_run(args), 1)
            retained = json.loads(path.read_text())
            self.assertEqual(len(retained["records"]), 1)
            self.assertEqual(retained["lifecycle_error"]["error_class"], "cleanup")

    def test_matching_data_is_not_claimed_to_be_model_equivalence(self):
        report = {"records": [
            {"case": "json", "arm": arm, "status": "pass", "actual": {"x": 1},
             "text": text, "receipt": {"system_sha256": "s", "user_sha256": "u"}}
            for arm, text in (("azure", '{"x":1}'), ("copilot", '{ "x": 1 }'))
        ]}
        summarize(report)
        item = next(item for item in report["comparisons"] if item["case"] == "json")
        self.assertEqual(item["status"], "observed_match")
        self.assertFalse(item["exact_text_match"])
        self.assertIn("not_model_or_provider_equivalence", report["conclusion"])

    async def test_budget_is_checked_before_any_client_starts(self):
        with tempfile.TemporaryDirectory() as work, patch.dict("os.environ", {
            "AZURE_OPENAI_ENDPOINT": ENDPOINT, "AZURE_OPENAI_API_KEY": KEY,
        }):
            path = Path(work) / "ledger.json"
            args = argparse.Namespace(
                output=str(path), azure_deployment="panel", azure_auth="api_key",
                copilot_model="gpt-6-sol", azure_only=False, case=["json"],
                include_native=False,
            )
            with patch("tools.compare_inference.AzureOpenAIProvider.__aenter__") as start:
                with patch("tools.compare_inference.provenance", side_effect=RuntimeError("STOP")):
                    with self.assertRaises(RuntimeError):
                        await compare_run(args)
                # Construct matching preflight configuration without model sends.
                from llm_inference.azure import AzureOpenAIProvider as Azure
                configuration = {
                    "azure_deployment": "panel", "azure_auth": "api_key",
                    "copilot_model": "gpt-6-sol", "azure_only": False,
                    "reasoning_effort": "low", "azure_max_completion_tokens": 1024,
                    "copilot_max_completion_tokens": "unavailable",
                    "uncontrolled": [
                        "sampling", "backend_alias_versions", "copilot_http_retries",
                        "provider_prompt_processing", "azure_only_output_token_cap",
                    ],
                    "azure_endpoint_sha256": Azure().configuration()["endpoint_sha256"],
                }
                path.write_text(json.dumps({
                    "scope": "synthetic_azure_copilot_compatibility",
                    "fixture_version": FIXTURE_VERSION,
                    "configuration": configuration,
                    "records": [{"case": "fixture", "arm": "azure"}] * BUDGET,
                }), "utf-8")
                with self.assertRaises(InferenceError) as caught:
                    await compare_run(args)
                self.assertEqual(caught.exception.code, "budget")
                start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
