from __future__ import annotations

import asyncio
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from llm_inference import CopilotProvider, InferenceError, InferenceRequest
from llm_inference.__main__ import main
from llm_inference.contracts import strict_json, validate_content
from llm_inference.copilot import EventAudit, child_environment, session_options

MODEL = "fixture-model"
SCHEMA = {
    "type": "object",
    "properties": {"score": {"type": "integer", "minimum": 1, "maximum": 10}},
    "required": ["score"],
    "additionalProperties": False,
}


def event(kind: str, data: dict | None = None, agent: str | None = None):
    return SimpleNamespace(
        to_dict=lambda: {"type": kind, "data": data or {}, "agentId": agent}
    )


def usage(model: str = MODEL, **data):
    return event("assistant.usage", {
        "model": model, "isByok": False, "finishReason": "stop",
        "availableToolCount": 0, "inputTokens": 12, "outputTokens": 3, **data,
    })


class FakeSession:
    def __init__(self, client, options):
        self.client, self.options = client, options

    async def send_and_wait(self, prompt, **options):
        self.client.sends.append((prompt, options))
        if self.client.hang:
            await asyncio.sleep(10)
        if self.client.send_error:
            raise RuntimeError("PRIVATE_PROVIDER_ERROR")
        for item in self.client.events:
            self.options["on_event"](item)
        return SimpleNamespace(data=SimpleNamespace(content=self.client.content))

    async def abort(self):
        self.client.aborts += 1
        if self.client.abort_error:
            raise RuntimeError("PRIVATE_ABORT_ERROR")


class FakeClient:
    def __init__(self):
        self.events = [usage()]
        self.content = '{"score": 4}'
        self.created, self.deleted, self.sends = [], [], []
        self.aborts = self.stops = self.force_stops = 0
        self.hang = self.send_error = self.delete_error = self.start_error = False
        self.stop_error = self.abort_error = False

    async def start(self):
        if self.start_error:
            raise RuntimeError("PRIVATE_STARTUP_ERROR")

    async def get_status(self):
        return SimpleNamespace(version="fixture-version")

    async def list_models(self):
        return [SimpleNamespace(id=MODEL, to_dict=lambda: {
            "id": MODEL, "provider": {"id": "copilot", "kind": "copilot"},
            "supportedReasoningEfforts": ["low"],
        })]

    async def create_session(self, **options):
        self.created.append(options)
        return FakeSession(self, options)

    async def delete_session(self, session_id):
        self.deleted.append(session_id)
        if self.delete_error:
            raise RuntimeError("PRIVATE_CLEANUP_ERROR")

    async def stop(self):
        self.stops += 1
        if self.stop_error:
            raise RuntimeError("PRIVATE_STOP_ERROR")

    async def force_stop(self):
        self.force_stops += 1


class ContractTests(unittest.TestCase):
    def test_strict_json_rejects_ambiguous_values(self):
        for text in (
            '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}',
            '```json\n{"score":4}\n```', '{"score":4} trailing',
        ):
            with self.subTest(text=text), self.assertRaises((ValueError, RecursionError)):
                strict_json(text)

    def test_json_content_validates_without_repair(self):
        _, _, validator = InferenceRequest(MODEL, "system", "user", SCHEMA).prepared()
        self.assertEqual(validate_content('{"score":4}', validator), {"score": 4})
        for text in ('{"score":true}', '{"score":0}', '{"score":11}',
                     '{"score":1,"extra":1}', '{}'):
            with self.subTest(text=text), self.assertRaises(InferenceError) as caught:
                validate_content(text, validator)
            self.assertEqual(caught.exception.code, "schema_violation")
        with self.assertRaises(InferenceError) as caught:
            validate_content('```{"score":4}```', validator)
        self.assertEqual(caught.exception.code, "malformed_json")

    def test_text_is_not_implicitly_parsed_or_stripped(self):
        self.assertIsNone(validate_content("  {not JSON}  ", None))
        for content in ("", " ", None, "x" * 128_001):
            with self.subTest(content_type=type(content)), self.assertRaises(InferenceError):
                validate_content(content, None)

    def test_request_rejects_invalid_values_before_dispatch(self):
        cases = [
            {"model": "auto"}, {"model": "fusion"}, {"system": ""},
            {"user": 3}, {"timeout_seconds": 0}, {"timeout_seconds": True},
            {"timeout_seconds": float("nan")}, {"timeout_seconds": 301},
            {"reasoning_effort": 2}, {"user": "x" * 256_001},
            {"user": "\ud800"},
            {"response_schema": []}, {"response_schema": {"type": "wrong"}},
            {"response_schema": {"$ref": "https://example.com/schema"}},
            {"response_schema": {"$dynamicRef": "#local"}},
            {"response_schema": {"$schema": "http://json-schema.org/draft-07/schema#"}},
        ]
        for overrides in cases:
            with self.subTest(overrides=list(overrides)), self.assertRaises(InferenceError):
                InferenceRequest(**{"model": MODEL, "system": "sys", "user": "usr",
                                    **overrides}).prepared()

    def test_schema_snapshot_is_local_and_no_roles_are_serialized(self):
        system, user, validator = InferenceRequest(MODEL, "sys", "usr", SCHEMA).prepared()
        self.assertTrue(system.startswith("sys\n\nReturn exactly"))
        self.assertEqual(user, "usr")
        self.assertEqual(validator.schema, SCHEMA)
        self.assertIsNot(validator.schema, SCHEMA)

    def test_environment_omits_agent_provider_and_telemetry_controls(self):
        with patch.dict("os.environ", {
            "COPILOT_ALLOW_ALL": "true", "COPILOT_PROVIDER_API_KEY": "not-a-secret",
            "COPILOT_MODEL": "unexpected", "OTEL_EXPORTER_OTLP_ENDPOINT": "external",
            "ANTHROPIC_AUTH_TOKEN": "fixture", "COPILOT_GITHUB_TOKEN": "fixture-auth",
            "NODE_OPTIONS": "unexpected",
        }, clear=True):
            env = child_environment()
        self.assertEqual(env, {
            "COPILOT_TELEMETRY_DISABLED": "true",
            "COPILOT_GITHUB_TOKEN": "fixture-auth",
        })

    def test_cli_rejects_unknown_provider_controls_without_starting_runtime(self):
        with (
            patch("sys.argv", ["llm_inference", "--request", "-"]),
            patch("sys.stdin", io.StringIO(json.dumps({
                "model": MODEL, "system": "s", "user": "u", "temperature": 0,
            }))),
            patch("llm_inference.__main__.CopilotProvider") as provider,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(main(), 1)
            provider.assert_not_called()
        self.assertEqual(json.loads(stderr.getvalue())["error_class"], "unsupported_control")

    def test_cli_depth_failure_is_a_json_diagnostic(self):
        with (
            patch("sys.argv", ["llm_inference", "--request", "-"]),
            patch("sys.stdin", io.StringIO("[" * 1500 + "0" + "]" * 1500)),
            patch("llm_inference.__main__.CopilotProvider") as provider,
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            self.assertEqual(main(), 1)
            provider.assert_not_called()
        self.assertEqual(json.loads(stderr.getvalue())["error_class"], "invalid_request")


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeClient()
        self.constructor = patch(
            "llm_inference.copilot.CopilotClient", return_value=self.fake
        )
        self.factory = self.constructor.start()
        self.addCleanup(self.constructor.stop)
        self.provider = CopilotProvider(executable=__file__)
        await self.provider.__aenter__()
        self.addAsyncCleanup(self.provider.close)

    def request(self, **overrides):
        return InferenceRequest(**{
            "model": MODEL, "system": "system", "user": "user",
            "response_schema": SCHEMA, **overrides,
        })

    async def test_roles_sessions_usage_and_restricted_options(self):
        for _ in range(2):
            response = await self.provider.generate(self.request(reasoning_effort="low"))
            self.assertEqual(response.parsed, {"score": 4})
            self.assertTrue(response.receipt["session_deleted"])
            self.assertEqual(response.receipt["inference_calls_observed"], 1)
            self.assertIsNone(response.receipt["http_attempts"])
            self.assertIsNone(response.receipt["usd_cost"])
        self.assertEqual(len(set(self.fake.deleted)), 2)
        for options in self.fake.created:
            self.assertEqual(options["system_message"]["mode"], "replace")
            for key, value in session_options(options["system_message"]["content"]).items():
                self.assertEqual(options[key], value)
            self.assertEqual(options["reasoning_effort"], "low")
        self.assertEqual([send[0] for send in self.fake.sends], ["user", "user"])
        self.assertEqual(self.factory.call_args.kwargs["log_level"], "none")
        self.assertNotEqual(
            self.factory.call_args.kwargs["working_directory"], str(Path.cwd())
        )

    async def test_returned_catalog_cannot_mutate_enabled_models(self):
        self.provider.models()[0]["provider"]["kind"] = "unexpected"
        await self.provider.generate(self.request())

    async def test_no_retry_after_transport_failure(self):
        self.fake.send_error = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "transport")
        self.assertEqual(len(self.fake.sends), 1)
        self.assertEqual(self.fake.aborts, 1)
        self.assertTrue(caught.exception.receipt["session_deleted"])
        self.assertNotIn("PRIVATE", json.dumps(caught.exception.to_dict()))

    async def test_timeout_aborts_and_deletes_owned_session(self):
        self.fake.hang = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request(timeout_seconds=0.01))
        self.assertEqual(caught.exception.code, "timeout")
        self.assertEqual(self.fake.aborts, 1)
        self.assertEqual(len(self.fake.deleted), 1)
        self.assertEqual(len(self.fake.sends), 1)

    async def test_cancellation_aborts_and_deletes_session(self):
        self.fake.hang = True
        task = asyncio.create_task(self.provider.generate(self.request()))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.fake.aborts, 1)
        self.assertEqual(len(self.fake.deleted), 1)

    async def test_cancellation_during_delete_finishes_cleanup_and_poisons_client(self):
        entered, release = asyncio.Event(), asyncio.Event()
        delete = self.fake.delete_session

        async def blocked_delete(session_id):
            entered.set()
            await release.wait()
            await delete(session_id)

        self.fake.delete_session = blocked_delete
        task = asyncio.create_task(self.provider.generate(self.request()))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(self.fake.deleted), 1)
        self.assertTrue(self.provider._poisoned)
        with self.assertRaises(InferenceError):
            await self.provider.generate(self.request())

    async def test_abort_failure_still_attempts_deletion(self):
        self.fake.send_error = self.fake.abort_error = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "cleanup")
        self.assertEqual(len(self.fake.deleted), 1)
        self.assertEqual(caught.exception.receipt["primary_error_class"], "transport")
        self.assertTrue(caught.exception.receipt["session_deleted"])
        self.assertEqual(
            caught.exception.receipt["cleanup_errors"][0]["operation"], "abort"
        )

    async def test_cleanup_failure_poisons_provider(self):
        self.fake.delete_error = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "cleanup")
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "lifecycle")
        self.assertEqual(len(self.fake.sends), 1)

    async def test_invalid_json_keeps_receipt_and_does_not_retry(self):
        self.fake.content = "NOT_JSON"
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "malformed_json")
        self.assertEqual(caught.exception.receipt["adapter_attempts"], 1)
        self.assertTrue(caught.exception.receipt["response_sha256"])
        self.assertTrue(caught.exception.receipt["session_deleted"])

    async def test_schema_failure_keeps_receipt(self):
        self.fake.content = '{"score":true}'
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "schema_violation")

    async def test_unavailable_model_and_effort_never_dispatch(self):
        for overrides in ({"model": "missing"}, {"reasoning_effort": "max"}):
            with self.subTest(overrides=overrides), self.assertRaises(InferenceError):
                await self.provider.generate(self.request(**overrides))
        self.assertEqual(self.fake.created, [])
        self.assertEqual(self.fake.sends, [])

    async def test_model_drift_missing_usage_and_multiple_inference_fail(self):
        for events, code in (
            ([], "unverified_attempts"), ([usage("other")], "model_mismatch"),
            ([usage(), usage()], "unverified_attempts"),
            ([usage(finishReason="length")], "incomplete_response"),
            ([usage(isByok=True)], "provider_mismatch"),
            ([event("model.call_start"), event("model.call_start"), usage()],
             "unverified_attempts"),
        ):
            self.fake.events = events
            with self.subTest(code=code), self.assertRaises(InferenceError) as caught:
                await self.provider.generate(self.request())
            self.assertEqual(caught.exception.code, code)

    async def test_forbidden_activity_is_not_success(self):
        for extra in (
            event("tool.execution_start"), event("hook.start"),
            event("session.error"), event("assistant.turn_retry"),
            event("model.call_failure"),
            event("assistant.message", agent="worker"),
            event("assistant.message", {"toolRequests": [{"name": "shell"}]}),
            event("session.mcp_servers_loaded", {"servers": [{"status": "connected"}]}),
            event("session.mcp_server_tools_loaded", {"toolCount": 2}),
            event("model.model_call_success", {"toolTokenCount": 20}),
            event("system.message", {"content": "ambient", "role": "system"}),
            event("user.message", {"content": "unexpected"}),
        ):
            self.fake.events = [extra, usage()]
            with self.subTest(extra=extra.to_dict()), self.assertRaises(InferenceError) as caught:
                await self.provider.generate(self.request())
            self.assertEqual(caught.exception.code, "boundary_violation")

    async def test_correct_runtime_message_hashes_and_zero_tools_are_observed(self):
        request = self.request()
        system, user, _ = request.prepared()
        self.fake.events = [
            event("system.message", {"content": system, "role": "system"}),
            event("user.message", {"content": user}),
            event("session.mcp_servers_loaded", {"servers": []}),
            usage(),
        ]
        response = await self.provider.generate(request)
        self.assertTrue(all(
            item["matches_sdk_input"] for item in response.receipt["message_audit"]
        ))
        self.assertEqual(response.receipt["tool_counts_observed"], [0])

    async def test_binary_drift_never_dispatches(self):
        self.provider._binary_hash = "changed"
        with self.assertRaises(InferenceError) as caught:
            await self.provider.generate(self.request())
        self.assertEqual(caught.exception.code, "configuration")
        self.assertFalse(self.fake.sends)

    async def test_owned_workspace_removed_on_shutdown(self):
        workspace = Path(self.provider._workspace.name)
        await self.provider.close()
        self.assertFalse(workspace.exists())
        with self.assertRaises(InferenceError):
            await self.provider.generate(self.request())

    async def test_shutdown_failure_force_stops_only_owned_runtime(self):
        response = await self.provider.generate(self.request())
        self.fake.stop_error = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.close()
        self.assertEqual(caught.exception.code, "cleanup")
        self.assertEqual(self.fake.force_stops, 1)
        self.assertIsNone(self.provider._workspace)
        self.assertEqual(caught.exception.receipt["session_id"], response.receipt["session_id"])
        self.assertEqual(caught.exception.receipt["inference_calls_observed"], 1)

    async def test_context_shutdown_failure_preserves_primary_error_and_usage(self):
        self.fake.content = "INVALID_JSON"
        with self.assertRaises(InferenceError) as primary:
            await self.provider.generate(self.request())
        self.fake.stop_error = True
        with self.assertRaises(InferenceError) as caught:
            await self.provider.__aexit__(InferenceError, primary.exception, None)
        self.assertEqual(caught.exception.code, "cleanup")
        self.assertEqual(caught.exception.receipt["primary_error_class"], "malformed_json")
        self.assertEqual(caught.exception.receipt["inference_calls_observed"], 1)
        self.assertTrue(caught.exception.receipt["dispatched"])
        self.assertTrue(caught.exception.receipt["session_deleted"])

    async def test_cancellation_during_close_waits_for_owned_runtime(self):
        entered, release = asyncio.Event(), asyncio.Event()
        stop = self.fake.stop

        async def blocked_stop():
            entered.set()
            await release.wait()
            await stop()

        self.fake.stop = blocked_stop
        task = asyncio.create_task(self.provider.close())
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.fake.stops, 1)
        self.assertIsNone(self.provider._client)
        self.assertIsNone(self.provider._workspace)

    async def test_failed_force_stop_retains_owned_resources_for_explicit_cleanup(self):
        async def failed_force_stop():
            raise OSError("PRIVATE_FORCE_STOP_ERROR")

        self.fake.stop_error = True
        self.fake.force_stop = failed_force_stop
        with self.assertRaises(InferenceError):
            await self.provider.close()
        self.assertIs(self.provider._client, self.fake)
        self.assertTrue(Path(self.provider._workspace.name).exists())
        self.assertTrue(self.provider._poisoned)
        self.fake.stop_error = False
        await self.provider.close()
        self.assertIsNone(self.provider._workspace)

    async def test_concurrent_requests_are_serialized_and_use_distinct_sessions(self):
        active = maximum = 0
        create = self.fake.create_session

        async def create_with_slow_send(**options):
            session = await create(**options)
            send = session.send_and_wait

            async def slow_send(prompt, **send_options):
                nonlocal active, maximum
                active += 1
                maximum = max(maximum, active)
                try:
                    await asyncio.sleep(0.01)
                    return await send(prompt, **send_options)
                finally:
                    active -= 1

            session.send_and_wait = slow_send
            return session

        self.fake.create_session = create_with_slow_send
        results = await asyncio.gather(
            self.provider.generate(self.request(user="first")),
            self.provider.generate(self.request(user="second")),
        )
        self.assertEqual(maximum, 1)
        self.assertNotEqual(results[0].receipt["session_id"], results[1].receipt["session_id"])
        self.assertEqual([item[0] for item in self.fake.sends], ["first", "second"])


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_startup_stops_owned_runtime_and_preserves_safe_error(self):
        fake = FakeClient()
        fake.start_error = True
        with patch("llm_inference.copilot.CopilotClient", return_value=fake):
            provider = CopilotProvider(executable=__file__)
            with self.assertRaises(InferenceError) as caught:
                await provider.__aenter__()
            self.assertEqual(caught.exception.code, "startup")
            self.assertIsNone(provider._workspace)
            self.assertEqual(fake.stops, 1)


class AuditTests(unittest.TestCase):
    def test_permission_requests_are_rejected_and_mark_boundary_failure(self):
        from copilot.rpc import PermissionDecisionReject
        audit = EventAudit()
        self.assertIsInstance(audit.permission({}, {}), PermissionDecisionReject)
        with self.assertRaises(InferenceError):
            audit.verify(MODEL)


if __name__ == "__main__":
    unittest.main()
