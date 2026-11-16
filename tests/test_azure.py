from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from llm_inference import AzureOpenAIProvider, InferenceError, InferenceRequest
from llm_inference.__main__ import run as cli_run
from llm_inference.azure import azure_base_url
from tools.compare_inference import BUDGET, FIXTURE_VERSION, run as compare_run, summarize
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
            {"max_completion_tokens": 0},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(InferenceError):
                provider(lambda _: httpx.Response(200, json=completion()), **overrides)


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
