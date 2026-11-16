"""Bounded Copilot development integration; never baseline/test/final acceptance."""

from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import time

from llm_inference import CopilotProvider, InferenceError
from triage.contracts import TriageError, digest, require
from triage.inputs import FINDING_FIELDS, read_inputs
from triage.workflow import RunConfig, save_json, validate_output
from triage_knowledge import KnowledgeStore, Review, TableSource, build_context, starter_candidate
from triage_knowledge.workflow_export import WorkflowExport

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "candidate-pack" / "candidate-pack"
SMOKE_IDS = ("F-1005", "F-1010", "F-1012")
SEND_LIMIT = 6


def hashes() -> dict:
    paths = [ROOT / "pyproject.toml", Path(__file__), ROOT / "docs" / "05_TRIAGE_WORKFLOW.md",
             ROOT / "eval" / "spec" / "split.json", ROOT / "eval" / "spec" / "acceptance.json"]
    for package in ("triage", "llm_inference", "triage_knowledge"):
        paths.extend(sorted((ROOT / package).glob("*.py")))
    return {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}


async def catalog() -> dict:
    async with CopilotProvider() as provider:
        return {"configuration": provider.configuration(), "models": provider.models(),
                "generation_sends": 0, "usd_cost": None}


def triage_command(findings: Path, registry: Path, export: Path, config: Path, target: Path) -> list[str]:
    return [
        sys.executable, "-B", "-m", "triage", "--provider", "copilot",
        "--findings", str(findings), "--registry", str(registry),
        "--context-export", str(export), "--legacy-replay", "--config", str(config),
        "--output", str(target / "tickets.experimental.json"), "--evidence", str(target / "run"),
        "--allow-inference",
    ]


def repeat_run(parent: Path, target: Path, model: str) -> tuple[list[str], dict]:
    parent = parent.resolve()
    original = json.loads((parent / "experiment.json").read_text())
    report = json.loads((parent / "run" / "run.json").read_text())
    config = RunConfig(**json.loads((parent / "config.json").read_text()))
    config.validate()
    require(config.execution_mode == "copilot_experiment" and config.model == model
            and asdict(config) == report["config"]
            and config.phase_attempt_budget == original["selection"]["application_send_ceiling"]
            and Path(config.attempt_ledger).resolve() == parent / "phase.experimental-ledger.json",
            "repeat_contract", "A repeat must retain the exact original model/configuration/phase ledger")
    selection = original["selection"].copy()
    for name, field in (("selected.csv", "findings_sha256"), ("registry.csv", "registry_sha256"),
                        ("context.json", "context_export_sha256")):
        require(digest((parent / name).read_bytes()) == selection[field],
                "repeat_contract", "Repeat source/export differs from original")
    ledger = json.loads(Path(config.attempt_ledger).read_text())
    require(ledger["budget"] == config.phase_attempt_budget,
            "repeat_contract", "Repeat phase ledger ceiling differs from recorded configuration")
    require(len(ledger["reservations"]) < config.phase_attempt_budget,
            "attempt_budget", "No authorized application sends remain")
    selection["attempt_ledger"] = config.attempt_ledger
    selection["prior_application_send_reservations"] = len(ledger["reservations"])
    return triage_command(parent / "selected.csv", parent / "registry.csv", parent / "context.json",
                          parent / "config.json", target), selection


def prepare_run(target: Path, model: str, split: dict, phase_budget: int = SEND_LIMIT) -> tuple[list[str], dict]:
    require(type(phase_budget) is int and 1 <= phase_budget <= 12,
            "configuration", "Smoke phase budget must be an explicit ceiling from 1 to 12")
    require(set(SMOKE_IDS) <= set(split["partitions"]["development"]),
            "selection", "Smoke selection must be development-only")
    groups = {item["group_id"]: len(item["finding_ids"]) for item in split["groups"]
              if set(item["finding_ids"]) & set(SMOKE_IDS)}
    require(len(groups) == len(SMOKE_IDS) and all(size == 1 for size in groups.values()),
            "selection", "Smoke selection must not split a bound context group")
    raw = (SOURCE / "data" / "inspection_findings.csv").read_bytes()
    rows = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            if row["finding_id"] in SMOKE_IDS]
    require(len(rows) == len(SMOKE_IDS), "selection", "Smoke selection is incomplete")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FINDING_FIELDS)
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda row: row["finding_id"]))
    findings_path = target / "selected.csv"
    findings_path.write_bytes(stream.getvalue().encode("utf-8"))
    registry_path = target / "registry.csv"
    registry_path.write_bytes((SOURCE / "data" / "equipment_registry.csv").read_bytes())
    inputs = read_inputs(findings_path, registry_path)
    cutoff = max(row["reported_date"] for row in rows) + "T23:59:59+00:00"
    domain = SOURCE / "reference" / "domain_knowledge.md"
    locator = str(domain.relative_to(ROOT))
    store = KnowledgeStore(target / "experiment-knowledge", domain, domain_locator=locator)
    candidate_hash = store.save_draft(starter_candidate(domain.read_bytes(), locator), expected_digest=None)
    now = datetime.now(timezone.utc).isoformat()
    version = store.publish(Review(
        candidate_hash, "Copilot-assisted developer", "AI-assisted contract check",
        "User-authorized integration experiment only; no human/expert approval or production activation.",
        now,
    ), published_at=now)
    snapshot = store.resolve_knowledge(version)
    findings_source = TableSource.from_bytes(findings_path.read_bytes(),
                                            source_id="findings", kind="finding_input")
    registry_source = TableSource.from_bytes(registry_path.read_bytes(),
                                            source_id="registry", kind="registry_input")
    bundle = build_context(findings_source, registry_source, snapshot, cutoff)
    export = target / "context.json"
    export.write_bytes(WorkflowExport.from_bundle(
        snapshot, bundle, selected_findings=findings_source, registry=registry_source,
        assessment_time=cutoff,
    ).encoded)
    config = RunConfig(
        model=model, knowledge_version=version, assessment_time=cutoff,
        phase_attempt_budget=phase_budget, attempt_ledger=str(target / "phase.experimental-ledger.json"),
        max_context_bytes=128_000, timeout_seconds=90, reasoning_effort=None,
        execution_mode="copilot_experiment",
    )
    save_json(target / "config.json", asdict(config))
    command = triage_command(findings_path, registry_path, export, target / "config.json", target)
    return command, {
        "finding_ids": list(SMOKE_IDS), "assessment_time": cutoff, "knowledge_version": version,
        "selection_reason": "Three singleton development groups: voted detection, refuge ventilation, evacuation.",
        "group_sizes_verified_from_manifest": groups,
        "findings_sha256": inputs.findings_hash, "registry_sha256": inputs.registry_hash,
        "context_export_sha256": digest(export.read_bytes()),
        "knowledge_review": "ai_assisted_experiment_only_not_human_or_expert_approved",
        "application_send_ceiling": phase_budget, "nominal_application_sends": len(SMOKE_IDS),
        "attempt_ledger": config.attempt_ledger,
        "http_attempts": None, "usd_cost": None, "output_token_cap": None,
        "budget_note": "Reservations bound application sends only; hidden HTTP retries/billing are unknown.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New experiment directory; never reused")
    parser.add_argument("--catalog-only", action="store_true", help="List metadata; no generation")
    parser.add_argument("--model", help="Explicit catalog model, never auto/fallback")
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--repeat-from", type=Path, help="Reuse unchanged sources/config and spent phase ledger")
    parser.add_argument("--repeat-reason", help="Required concrete reason; never resets or enlarges budget")
    parser.add_argument("--phase-budget", type=int, help="Authorized new-phase ceiling (default 6, maximum 12)")
    args = parser.parse_args(argv)
    target = args.output.resolve()
    owned_target, stage = False, "preflight"
    try:
        require(args.catalog_only or (args.allow_inference and bool(args.model)),
                "configuration", "Live experiment requires explicit --model and --allow-inference")
        require((args.repeat_from is None) == (args.repeat_reason is None)
                and (args.repeat_reason is None or bool(args.repeat_reason.strip())),
                "configuration", "Repeats require both --repeat-from and a concrete --repeat-reason")
        require(args.repeat_from is None or args.phase_budget is None,
                "configuration", "A repeat cannot replace the original phase budget")
        require(args.phase_budget is None or 1 <= args.phase_budget <= 12,
                "configuration", "Smoke phase budget must be from 1 to 12")
        target.mkdir(parents=True, exist_ok=False)
        owned_target = True
        if args.catalog_only:
            data = asyncio.run(catalog())
            save_json(target / "catalog.json", data)
            print(json.dumps(data, ensure_ascii=True))
            return 0
        integrity = subprocess.run([sys.executable, "-B", "-m", "eval.validate"],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
        (target / "reference-validation.txt").write_text(integrity.stdout + integrity.stderr, encoding="utf-8")
        require(integrity.returncode == 0, "reference_integrity", "Frozen integrity failed before inference")
        split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
        command, selection = (repeat_run(args.repeat_from, target, args.model) if args.repeat_from
                              else prepare_run(target, args.model, split,
                                               args.phase_budget if args.phase_budget is not None else SEND_LIMIT))
        before = hashes()
        provenance = {
            "created_at": datetime.now(timezone.utc).isoformat(), "scope": "copilot_development_integration",
            "acceptance_eligible": False, "selection": selection, "command": command,
            "repeat_from": str(args.repeat_from.resolve()) if args.repeat_from else None,
            "repeat_reason": args.repeat_reason,
            "source_hashes_before": before,
            "git_revision": subprocess.run(["git", "--no-pager", "rev-parse", "HEAD"], cwd=ROOT,
                                           capture_output=True, text=True, check=True).stdout.strip(),
            "dirty_worktree": subprocess.run(["git", "--no-pager", "status", "--short"], cwd=ROOT,
                                             capture_output=True, text=True, check=True).stdout,
        }
        save_json(target / "experiment.json", provenance)
        stage = "running"
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        (target / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (target / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
        stage = "collecting"
        record_path = target / "run" / "run.json"
        record = json.loads(record_path.read_text()) if record_path.exists() else {}
        sends = record.get("application_sends", [])
        isolation = all(
            identifier not in send["provider_input"]["user"] and identifier not in send["provider_input"]["system"]
            for send in sends for identifier in set(split["partitions"]["test"])
        ) if sends else None
        if sends:
            isolation = isolation and all(
                set(json.loads(send["provider_input"]["user"])["context"]["finding_ids"]) == set(SMOKE_IDS)
                for send in sends
            )
        after = hashes()
        output = target / "tickets.experimental.json"
        valid = False
        if completed.returncode == 0:
            stage = "validating_output"
            source_root = args.repeat_from.resolve() if args.repeat_from else target
            inputs = read_inputs(source_root / "selected.csv", source_root / "registry.csv")
            validate_output(json.loads(output.read_text()), inputs.data["findings"])
            valid = True
        result = {
            "status": ("experimental_draft_generated" if isolation is True and before == after
                       else "draft_generated_but_evidence_invalid") if valid else "integration_failed",
            "cli_exit_code": completed.returncode, "output_contract_valid": valid,
            "acceptance_eligible": False, "semantic_status": "not_reviewed",
            "test_descriptions_sent": False if isolation is True else (
                "isolation_failure" if isolation is False else "unverified_no_sends_captured"),
            "application_send_reservations": len(sends), "http_attempts": None, "usd_cost": None,
            "phase_application_send_reservations": len(json.loads(
                Path(selection["attempt_ledger"]).read_text())["reservations"])
                if selection.get("attempt_ledger") and Path(selection["attempt_ledger"]).exists() else None,
            "code_stable_during_run": before == after, "source_hashes_after": after,
            "output_sha256": digest(output.read_bytes()) if output.exists() else None,
            "elapsed_seconds": time.monotonic() - started,
            "usage_receipts": [send.get("receipt") for send in sends],
            "remaining_gates": [
                "Strict total HTTP-attempt and raw-endpoint compliance are not established by Copilot.",
                "No calibrated semantic acceptance, X01 repeat, frozen test or final delivery is claimed.",
                "Catalog/usage billing units are not USD and do not establish monetary savings.",
            ],
        }
        save_json(target / "observation.json", result)
        print(json.dumps({key: value for key, value in result.items()
                          if key not in {"usage_receipts", "source_hashes_after"}}, ensure_ascii=True))
        return 0 if valid and isolation is True and before == after else 1
    except (TriageError, InferenceError, OSError, ValueError, TypeError) as error:
        code = error.code if isinstance(error, (TriageError, InferenceError)) else "experiment_io_or_contract"
        diagnostic = {"status": "integration_failed", "error_class": code,
                      "collector_error": type(error).__name__, "stage": stage,
                      "acceptance_eligible": False, "http_attempts": None, "usd_cost": None}
        if owned_target:
            try:
                save_json(target / "observation.json", diagnostic)
            except OSError:
                diagnostic["evidence_persistence_error"] = "io"
        print(json.dumps(diagnostic), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
