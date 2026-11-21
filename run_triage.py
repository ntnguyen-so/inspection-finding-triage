"""Create an isolated live-run workspace and invoke the validated triage CLI."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from triage.__main__ import main as triage_main


ROOT = Path(__file__).resolve().parent
DEFAULT_COPILOT_MODEL = "gpt-6.1-sol"
AZURE_MODEL_NAME = "gpt-6.1-sol"
AZURE_MODEL_VERSION = "2026-09-29"
AZURE_OBSERVED_MODEL = f"{AZURE_MODEL_NAME}-{AZURE_MODEL_VERSION}"


def build_config(
    provider: str,
    model: str,
    ledger: Path,
    knowledge_version: str,
    reasoning_effort: str | None,
) -> dict:
    """Build the explicit provider and evidence configuration for one fresh run."""
    return {
        "model": model,
        "knowledge_version": knowledge_version,
        "assessment_time": "2026-07-01T00:00:00+00:00",
        "phase_attempt_budget": 42,
        "attempt_ledger": str(ledger.resolve()),
        "max_context_bytes": 128000,
        "timeout_seconds": 300 if provider == "azure" else 180,
        "reasoning_effort": reasoning_effort,
        "execution_mode": "copilot_delivery" if provider == "copilot" else "strict",
        "minimum_request_interval_seconds": 0,
        "azure_max_completion_tokens": 8192,
        "azure_api": "chat_completions",
        "azure_expected_model": AZURE_OBSERVED_MODEL if provider == "azure" else None,
    }


def parser() -> argparse.ArgumentParser:
    """Define the convenience CLI without duplicating triage validation rules."""
    result = argparse.ArgumentParser(
        description="Generate tickets.json with fresh configuration, evidence and attempt paths."
    )
    result.add_argument("--provider", choices=("copilot", "azure"), required=True)
    result.add_argument(
        "--model",
        help="Copilot catalog model or Azure OpenAI deployment name. The Azure "
        f"deployment must serve {AZURE_MODEL_NAME} version {AZURE_MODEL_VERSION}. "
        f"Copilot defaults to {DEFAULT_COPILOT_MODEL}.",
    )
    result.add_argument(
        "--reasoning-effort",
        default="medium",
        help="Provider-supported reasoning effort; use 'none' to omit the control.",
    )
    result.add_argument("--output", type=Path, default=ROOT / "tickets.json")
    result.add_argument("--runs", type=Path, default=ROOT / ".runs")
    return result


def main(argv: list[str] | None = None) -> int:
    """Create collision-resistant run paths, then delegate to ``triage``."""
    args = parser().parse_args(argv)
    if args.provider == "azure" and not args.model:
        parser().error("--model is required for Azure and must be the deployment name")
    if args.provider == "azure" and (
        not os.environ.get("AZURE_OPENAI_ENDPOINT")
        or not os.environ.get("AZURE_OPENAI_API_KEY")
    ):
        parser().error(
            "Azure requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY"
        )

    model = args.model or DEFAULT_COPILOT_MODEL
    reasoning_effort = (
        None if args.reasoning_effort.lower() == "none" else args.reasoning_effort
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = args.runs.resolve() / f"{timestamp}-{args.provider}"
    run.mkdir(parents=True, exist_ok=False)
    activation = ROOT / "config" / "triage-activation.json"
    activation_payload = json.loads(activation.read_text(encoding="utf-8"))
    ledger_name = (
        "attempts.experimental-ledger.json"
        if args.provider == "copilot"
        else "attempts.ledger.json"
    )
    config = run / "config.json"
    config.write_text(
        json.dumps(
            build_config(
                args.provider,
                model,
                run / ledger_name,
                activation_payload["knowledge_version"],
                reasoning_effort,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return triage_main(
        [
            "--provider",
            args.provider,
            "--findings",
            str(ROOT / "docs" / "candidate-pack" / "candidate-pack" / "data"
                / "inspection_findings.csv"),
            "--registry",
            str(ROOT / "docs" / "candidate-pack" / "candidate-pack" / "data"
                / "equipment_registry.csv"),
            "--knowledge-store",
            str(ROOT / "knowledge" / "source-first"),
            "--activation",
            str(activation),
            "--config",
            str(config),
            "--output",
            str(args.output.resolve()),
            "--evidence",
            str(run / "evidence"),
            "--allow-inference",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
