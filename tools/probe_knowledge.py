"""Four-send Copilot B02 development observation, never acceptance or final generation."""

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

from llm_inference import CopilotProvider, InferenceError, InferenceRequest
from triage.assessment import request_for, validate_assessment
from triage.contracts import TriageError
from triage.inputs import EQUIPMENT_FIELDS, FINDING_FIELDS, read_inputs, validate_context
from triage_knowledge import (
    EvaluationOverlay, KnowledgeStore, Review, TableSource, build_context, starter_candidate,
)
from triage_knowledge.contracts import canonical_bytes, sha256
from triage_knowledge.knowledge import _write
from triage_knowledge.workflow_export import WorkflowExport

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "candidate-pack" / "candidate-pack"
LEDGER = ROOT / "eval" / "results" / "knowledge" / "copilot-b02.experimental-ledger.json"
CONDITIONS = ("positive-before", "positive-after", "negative-before", "negative-after")


def save(path: Path, value: object) -> None:
    _write(path, (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode(),
           replace=path.exists())


def hashes() -> dict:
    paths = [Path(__file__), ROOT / "pyproject.toml", ROOT / "docs" / "06_KNOWLEDGE_DESIGN_DECISION.md",
             ROOT / "eval" / "spec" / "probes.json", ROOT / "eval" / "spec" / "split.json"]
    for package in ("triage", "llm_inference", "triage_knowledge"):
        paths.extend(sorted((ROOT / package).glob("*.py")))
    return {str(path.relative_to(ROOT)): sha256(path.read_bytes()) for path in paths}


def csv_data(columns, rows) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def prepare(target: Path, model: str) -> dict:
    target.mkdir(parents=True, exist_ok=False)
    validation = subprocess.run([sys.executable, "-B", "-m", "eval.validate"], cwd=ROOT,
                                capture_output=True, text=True)
    save(target / "reference-validation.json",
         {"exit_code": validation.returncode, "stdout": validation.stdout, "stderr": validation.stderr})
    if validation.returncode:
        raise ValueError("Frozen reference integrity failed.")
    probe = json.loads((ROOT / "eval" / "spec" / "probes.json").read_text())["b02"]
    split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
    raw = (SOURCE / "data" / "inspection_findings.csv").read_bytes()
    development = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
                   if row["finding_id"] in set(split["partitions"]["development"])]
    if {row["finding_id"] for row in development} != set(split["partitions"]["development"]):
        raise ValueError("Incomplete development selection.")
    if probe["negative_control_finding"] not in split["partitions"]["development"]:
        raise ValueError("Negative control is not development-only.")
    registry = list(csv.DictReader(io.StringIO(
        (SOURCE / "data" / "equipment_registry.csv").read_bytes().decode("utf-8-sig"), newline="")))
    registry.append(probe["positive_input"]["equipment"])
    (target / "registry.csv").write_bytes(csv_data(EQUIPMENT_FIELDS, registry))
    domain = SOURCE / "reference" / "domain_knowledge.md"
    store = KnowledgeStore(target / "experiment-knowledge", domain)
    candidate = starter_candidate(domain.read_bytes(), store.domain_locator)
    digest = store.save_draft(candidate, expected_digest=None)
    now = datetime.now(timezone.utc).isoformat()
    version = store.publish(Review(
        digest, "Copilot-assisted developer", "AI-assisted component review",
        "Temporary isolated experiment only, not owner/expert approval or production activation.", now,
    ), published_at=now)
    snapshot = store.resolve_knowledge(version)
    cutoff = "2026-06-22T23:59:59+00:00"
    cases = {}
    for input_kind, rows in (("positive", [probe["positive_input"]["finding"]]), ("negative", development)):
        finding_path = target / f"{input_kind}.csv"
        finding_path.write_bytes(csv_data(FINDING_FIELDS, rows))
        inputs = read_inputs(finding_path, target / "registry.csv")
        selected = TableSource.from_bytes(finding_path.read_bytes(), source_id="findings", kind="evaluation_input")
        registered = TableSource.from_bytes((target / "registry.csv").read_bytes(),
                                            source_id="registry", kind="registry_input")
        finding_id = (probe["positive_input"]["finding"]["finding_id"] if input_kind == "positive"
                      else probe["negative_control_finding"])
        for policy in ("before", "after"):
            condition = f"{input_kind}-{policy}"
            raw_overlay = canonical_bytes({
                "scope": "Pressure Safety Valve with observed seat passing below set pressure; not tag-only defects.",
                "dimension": "likelihood", "guidance": probe["policies"][policy]["text"],
            })
            overlay = EvaluationOverlay("probe-policy-overlay", raw_overlay, sha256(raw_overlay))
            bundle = build_context(selected, registered, snapshot, cutoff,
                                   purpose="evaluation_probe", overlay_ref=overlay)
            export = WorkflowExport.from_bundle(snapshot, bundle, selected, registered, cutoff,
                                                purpose="evaluation_probe", overlay_ref=overlay)
            (target / f"{condition}.native.json").write_bytes(bundle.encoded)
            (target / f"{condition}.export.json").write_bytes(export.encoded)
            checked, context_text, _ = validate_context(
                export, inputs, version, cutoff, 200_000, purpose="isolated_probe", overlay_ref=export.overlay_ref)
            finding = inputs.data["findings"][finding_id]
            actual = request_for(model, context_text, finding_id, finding["equipment_id"], 120, "low")
            system, user, _ = actual.prepared()
            # Same prepared assessment messages, text capture so malformed completions remain available.
            request = InferenceRequest(model, system, user, timeout_seconds=120, reasoning_effort="low")
            request.prepared()
            save(target / f"{condition}.request.json", asdict(request))
            cases[condition] = {
                "finding": finding, "context_hash": checked["context_hash"],
                "native_context_hash": bundle.context_hash,
                "policy_version": probe["policies"][policy]["version"], "overlay_sha256": sha256(raw_overlay),
                "expected_positive_likelihood": probe["expected"][f"positive_{policy}_likelihood"]
                if input_kind == "positive" else None,
            }
    files = {str(path.relative_to(target)): sha256(path.read_bytes())
             for path in sorted(target.rglob("*")) if path.is_file()}
    plan = {
        "created_at": now, "scope": "isolated_copilot_knowledge_B02_development_not_baseline",
        "acceptance_eligible": False, "model": model, "reasoning_effort": "low",
        "temperature": None, "sampling_control": "unavailable_through_copilot",
        "nominal_requests": 4, "application_send_ceiling": 4, "retries": 0,
        "http_attempts": None, "usd_budget": None, "usd_cost": None,
        "budget_note": "Four one-shot application sends, not a USD/hidden-HTTP ceiling. Do not reset ledger.",
        "capture_mode": "text_capture_of_exact_prepared_triage_assessment_messages",
        "knowledge_version": version, "assessment_time": cutoff, "cases": cases,
        "negative_semantic_status": "needs_review_no_calibrated_reviewer",
        "source_hashes": hashes(), "artifact_hashes": files, "phase_ledger": str(LEDGER),
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
    }
    save(target / "plan.json", plan)
    return plan


async def run(target: Path, *, ledger_path: Path = LEDGER, factory=CopilotProvider) -> dict:
    plan = json.loads((target / "plan.json").read_text())
    if (hashes() != plan["source_hashes"] or set(plan["cases"]) != set(CONDITIONS)
            or plan["application_send_ceiling"] != 4 or plan["retries"] != 0):
        raise ValueError("Prepared experiment source/configuration changed.")
    for name, digest in plan["artifact_hashes"].items():
        if sha256((target / name).read_bytes()) != digest:
            raise ValueError(f"Prepared artifact changed: {name}")
    ledger = {"phase": "copilot-knowledge-b02", "application_send_ceiling": 4,
              "output": str(target), "slots": {name: {"state": "reserved"} for name in CONDITIONS}}
    _write(ledger_path, json.dumps(ledger, indent=2).encode(), replace=False)
    results = {}
    try:
        async with factory() as provider:
            save(target / "provider-configuration.json", provider.configuration())
            for name in CONDITIONS:
                body = json.loads((target / f"{name}.request.json").read_text())
                request = InferenceRequest(**body)
                system, user, _ = request.prepared()
                ledger["slots"][name] = {"state": "attempt_reserved", "at": datetime.now(timezone.utc).isoformat()}
                save(ledger_path, ledger)
                result = {"assessment_valid": False, "likelihood": None, "raw_response_available": False}
                try:
                    response = await provider.generate(request)
                    result.update(receipt=response.receipt, raw_response_available=True)
                    (target / f"{name}.response.txt").write_text(response.text, encoding="utf-8")
                    exported = json.loads((target / f"{name}.export.json").read_text())["bundle"]
                    assessment = validate_assessment(response.text, plan["cases"][name]["finding"],
                                                     exported["source_index"])
                    save(target / f"{name}.assessment.json", assessment)
                    result.update(assessment_valid=True, likelihood=assessment["likelihood_of_failure"]["score"])
                except InferenceError as error:
                    result.update(error_class=error.code, receipt=error.receipt)
                except TriageError as error:
                    result.update(error_class=error.code, validation_message=str(error))
                receipt = result.get("receipt", {})
                result["actual_message_audit_verified"] = (
                    receipt.get("system_sha256") == sha256(system.encode())
                    and receipt.get("user_sha256") == sha256(user.encode())
                    and {entry["kind"] for entry in receipt.get("message_audit", [])}
                    == {"system.message", "user.message"}
                    and all(entry.get("matches_sdk_input") is True
                            for entry in receipt.get("message_audit", []))
                    and receipt.get("boundary_violation") is None)
                results[name] = result
                save(target / f"{name}.result.json", result)
                ledger["slots"][name]["state"] = "completed_once"
                save(ledger_path, ledger)
    except (InferenceError, OSError, ValueError, TypeError, KeyError) as error:
        results["collector_failure"] = (error.to_dict() if isinstance(error, InferenceError)
                                         else {"error_class": type(error).__name__, "status": "failed"})
    positives = all(results.get(f"positive-{policy}", {}).get("assessment_valid")
                    and results[f"positive-{policy}"]["likelihood"]
                    == plan["cases"][f"positive-{policy}"]["expected_positive_likelihood"]
                    for policy in ("before", "after"))
    stable = hashes() == plan["source_hashes"]
    mechanically_valid = all(results.get(name, {}).get("assessment_valid")
                             and results[name].get("actual_message_audit_verified") for name in CONDITIONS)
    observed = positives and mechanically_valid and stable and "collector_failure" not in results
    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": "positive_policy_response_observed_negative_review_pending" if observed else "failed_or_inconclusive",
        "acceptance_eligible": False, "positive_expected_scores_observed": positives,
        "negative_semantic_status": "needs_review_no_calibrated_reviewer",
        "model": plan["model"], "application_send_ceiling": 4,
        "attempt_reservations": sum(slot["state"] != "reserved" for slot in ledger["slots"].values()),
        "http_attempts": None, "usd_cost": None, "source_stable_during_run": stable,
        "results": results, "phase_ledger": str(ledger_path),
        "limitations": [
            "Direct assessment-component probe, not full workflow publication, recovery or semantic acceptance.",
            "Copilot hidden HTTP attempts, output-token cap and USD billing remain unknown.",
            "Raw completions are retained after successful text capture; transport/audit failures may expose only hashes.",
            "No frozen test, final tickets or normal shipping overlay was generated.",
        ],
    }
    save(target / "observation.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--allow-inference", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            if not args.model or LEDGER.exists():
                raise ValueError("Preparation requires a model and an unused experiment ledger.")
            data = prepare(args.output.resolve(), args.model)
            print(json.dumps({"status": "prepared_no_sends", "model": data["model"], "conditions": list(CONDITIONS)}))
        else:
            if not args.allow_inference:
                raise ValueError("Actual sends require --allow-inference.")
            data = asyncio.run(run(args.output.resolve()))
            print(json.dumps({key: value for key, value in data.items() if key != "results"}))
            return 0 if data["status"] == "positive_policy_response_observed_negative_review_pending" else 1
        return 0
    except (InferenceError, TriageError, ValueError, OSError) as error:
        print(json.dumps({"status": "experiment_failed", "error_class": getattr(error, "code", type(error).__name__),
                          "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
