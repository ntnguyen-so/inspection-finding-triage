from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_triage as runbook
from triage.source_context import execution_policy_hash


class RunbookTests(unittest.TestCase):
    def test_builds_fresh_copilot_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(runbook, "triage_main", return_value=0) as triage:
                result = runbook.main(
                    ["--provider", "copilot", "--runs", str(root),
                     "--output", str(root / "tickets.json")]
                )

            self.assertEqual(0, result)
            config_path = Path(triage.call_args.args[0][triage.call_args.args[0].index("--config") + 1])
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("copilot_delivery", config["execution_mode"])
            self.assertEqual("gpt-6.1-sol", config["model"])
            self.assertEqual(180, config["timeout_seconds"])
            self.assertEqual(
                "sha256-b215857575e443ba5fd9cb56a19f3079003cd68acb03fdf0e33ca7fbed59e097",
                config["knowledge_version"],
            )
            self.assertTrue(config["attempt_ledger"].endswith(".experimental-ledger.json"))
            self.assertIn("--allow-inference", triage.call_args.args[0])

    def test_builds_strict_azure_delivery_with_deployment_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = {
                "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
                "AZURE_OPENAI_API_KEY": "secret",
            }
            with patch.dict(os.environ, environment, clear=False), patch.object(
                runbook, "triage_main", return_value=0
            ) as triage:
                result = runbook.main(
                    ["--provider", "azure", "--model", "triage-deployment",
                     "--runs", str(root), "--output", str(root / "tickets.json")]
                )

            self.assertEqual(0, result)
            config_path = Path(triage.call_args.args[0][triage.call_args.args[0].index("--config") + 1])
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("strict", config["execution_mode"])
            self.assertEqual("triage-deployment", config["model"])
            self.assertEqual(300, config["timeout_seconds"])
            self.assertEqual("gpt-6.1-sol-2026-09-29", config["azure_expected_model"])
            self.assertTrue(config["attempt_ledger"].endswith("attempts.ledger.json"))

    def test_committed_activation_matches_current_execution_policy(self):
        activation = json.loads(
            (runbook.ROOT / "config" / "triage-activation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            activation["execution_policy_sha256"],
            execution_policy_hash(),
        )


if __name__ == "__main__":
    unittest.main()
