from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path


TOKEN_FIELDS = (
    "inputTokens",
    "outputTokens",
    "cacheReadTokens",
    "cacheWriteTokens",
    "reasoningTokens",
)


def summarize(
    run_path: Path,
    *,
    input_rate: Decimal,
    output_rate: Decimal,
    cache_read_rate: Decimal,
    cache_write_rate: Decimal,
    pricing_source: str,
    checked_on: str,
) -> dict:
    rates = (input_rate, output_rate, cache_read_rate, cache_write_rate)
    if any(rate < 0 for rate in rates):
        raise ValueError("Pricing rates must be nonnegative")
    date.fromisoformat(checked_on)
    raw = run_path.read_bytes()
    run = json.loads(raw)
    sends = run.get("application_sends")
    if run.get("run_status") != "published" or not isinstance(sends, list) or not sends:
        raise ValueError("Expected a published run with application_sends")

    totals = {field: 0 for field in TOKEN_FIELDS}
    request_cost_units = Decimal(0)
    nano_aiu = Decimal(0)
    finding_ids = []
    models = set()
    for send in sends:
        finding_id = send.get("finding_id")
        if not isinstance(finding_id, str) or not finding_id:
            raise ValueError("Every application send requires a finding_id")
        finding_ids.append(finding_id)
        receipt = send.get("receipt")
        usage = receipt.get("usage") if isinstance(receipt, dict) else None
        if not isinstance(usage, list) or not usage:
            raise ValueError("Every application send requires receipt usage")
        for item in usage:
            if not isinstance(item, dict):
                raise ValueError("Usage entries must be objects")
            model = item.get("model")
            if not isinstance(model, str) or not model:
                raise ValueError("Every usage entry requires a model")
            models.add(model)
            for field in TOKEN_FIELDS:
                value = item.get(field, 0)
                if type(value) is not int or value < 0:
                    raise ValueError(f"Invalid {field}")
                totals[field] += value
            cost = item.get("cost", 0)
            if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
                raise ValueError("Invalid request cost units")
            request_cost_units += Decimal(str(cost))
            copilot_usage = item.get("copilotUsage") or {}
            total_nano_aiu = copilot_usage.get("totalNanoAiu", 0)
            if (
                isinstance(total_nano_aiu, bool)
                or not isinstance(total_nano_aiu, (int, float))
                or total_nano_aiu < 0
            ):
                raise ValueError("Invalid Copilot AI units")
            nano_aiu += Decimal(str(total_nano_aiu))
    if len(models) != 1:
        raise ValueError("Expected exactly one metered model")
    unique_findings = len(set(finding_ids))

    uncached = (
        totals["inputTokens"]
        - totals["cacheReadTokens"]
        - totals["cacheWriteTokens"]
    )
    if uncached < 0:
        raise ValueError("Cache token counts exceed input tokens")

    million = Decimal(1_000_000)
    simple = (
        Decimal(totals["inputTokens"]) * input_rate
        + Decimal(totals["outputTokens"]) * output_rate
    ) / million
    cache_aware = (
        Decimal(uncached) * input_rate
        + Decimal(totals["cacheReadTokens"]) * cache_read_rate
        + Decimal(totals["cacheWriteTokens"]) * cache_write_rate
        + Decimal(totals["outputTokens"]) * output_rate
    ) / million

    return {
        "contract": "delivery-cost-summary-v1",
        "source_run": str(run_path),
        "source_run_sha256": hashlib.sha256(raw).hexdigest(),
        "application_sends": len(sends),
        "findings": unique_findings,
        "measured_usage": {
            **totals,
            "uncachedInputTokens": uncached,
            "requestCostUnits": float(request_cost_units),
            "aiUnits": float(nano_aiu / Decimal(1_000_000_000)),
        },
        "pricing_assumption": {
            "source": pricing_source,
            "checked_on": checked_on,
            "model": next(iter(models)),
            "tier": "Standard short context",
            "usd_per_million_tokens": {
                "input": float(input_rate),
                "output": float(output_rate),
                "cache_read": float(cache_read_rate),
                "cache_write_30m": float(cache_write_rate),
            },
        },
        "api_equivalent_usd": {
            "simple_input_output": float(simple),
            "simple_per_ticket": float(simple / Decimal(unique_findings)),
            "cache_aware_30m_write_scenario": float(cache_aware),
        },
        "actual_copilot_usd": None,
        "limitations": [
            "API-equivalent values are pricing scenarios, not a Copilot invoice.",
            "Copilot AI-unit-to-USD conversion and hidden HTTP attempts are not exposed.",
            "Cache-aware repricing assumes OpenAI 30-minute cache-write semantics.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize measured run usage and declared API-equivalent cost."
    )
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-rate", type=Decimal, default=Decimal("2"))
    parser.add_argument("--output-rate", type=Decimal, default=Decimal("10"))
    parser.add_argument("--cache-read-rate", type=Decimal, default=Decimal("0.1"))
    parser.add_argument("--cache-write-rate", type=Decimal, default=Decimal("2.5"))
    parser.add_argument(
        "--pricing-source",
        default="https://developers.openai.com/api/docs/pricing",
    )
    parser.add_argument("--checked-on", default=date.today().isoformat())
    args = parser.parse_args()
    result = summarize(
        args.run,
        input_rate=args.input_rate,
        output_rate=args.output_rate,
        cache_read_rate=args.cache_read_rate,
        cache_write_rate=args.cache_write_rate,
        pricing_source=args.pricing_source,
        checked_on=args.checked_on,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
