from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from tools.summarize_run_cost import summarize


class SummarizeRunCostTests(unittest.TestCase):
    def test_summarizes_receipt_usage_without_counting_checkpoint_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            path.write_text(json.dumps({
                "run_status": "published",
                "application_sends": [{
                    "finding_id": "F-1001",
                    "receipt": {
                        "usage": [{
                            "inputTokens": 100,
                            "outputTokens": 20,
                            "cacheReadTokens": 30,
                            "cacheWriteTokens": 60,
                            "reasoningTokens": 5,
                            "cost": 1,
                            "model": "test-model",
                            "copilotUsage": {"totalNanoAiu": 40_000_000_000},
                        }],
                        "accounting_checkpoint": {
                            "totalNanoAiu": 40_000_000_000,
                        },
                    },
                }],
            }), encoding="utf-8")

            result = summarize(
                path,
                input_rate=Decimal("2"),
                output_rate=Decimal("10"),
                cache_read_rate=Decimal("0.1"),
                cache_write_rate=Decimal("2.5"),
                pricing_source="https://example.test/pricing",
                checked_on="2026-11-18",
            )

        self.assertEqual(100, result["measured_usage"]["inputTokens"])
        self.assertEqual(1, result["findings"])
        self.assertEqual("test-model", result["pricing_assumption"]["model"])
        self.assertEqual(10, result["measured_usage"]["uncachedInputTokens"])
        self.assertEqual(40, result["measured_usage"]["aiUnits"])
        self.assertEqual(0.0004, result["api_equivalent_usd"]["simple_input_output"])
        self.assertEqual(
            0.000373,
            result["api_equivalent_usd"]["cache_aware_30m_write_scenario"],
        )


if __name__ == "__main__":
    unittest.main()
