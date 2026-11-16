from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

from triage_knowledge import (
    KnowledgeError, KnowledgeStore, Review, TableSource, build_context, effective_guidance,
    serialize_context, starter_candidate,
)
from triage_knowledge.contracts import canonical_bytes, sha256, strict_json
from triage_knowledge.knowledge import _write
from triage_knowledge.workflow_export import WorkflowExport


def _csv(fields: list[str], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def development_delivery(root: Path, artifacts: Path, observed_at: str) -> dict:
    split = strict_json((root / "eval" / "spec" / "split.json").read_bytes())
    domain_relative = r"docs\candidate-pack\candidate-pack\reference\domain_knowledge.md"
    source_root = root / "docs" / "candidate-pack" / "candidate-pack"
    raw_findings = (source_root / "data" / "inspection_findings.csv").read_bytes()
    raw_registry = (source_root / "data" / "equipment_registry.csv").read_bytes()
    allowed = set(split["partitions"]["development"])
    reader = csv.DictReader(io.StringIO(raw_findings.decode("utf-8-sig"), newline=""))
    selected_rows = [row for row in reader if row["finding_id"] in allowed]
    registry_reader = csv.DictReader(io.StringIO(raw_registry.decode("utf-8-sig"), newline=""))
    registry_rows = list(registry_reader)
    selected_raw = _csv(reader.fieldnames, selected_rows)
    reversed_raw = _csv(reader.fieldnames, selected_rows[::-1])
    reversed_registry = _csv(registry_reader.fieldnames, registry_rows[::-1])
    with tempfile.TemporaryDirectory() as temporary:
        store = KnowledgeStore(Path(temporary), root / domain_relative, domain_locator=domain_relative)
        candidate = starter_candidate(store.domain_path.read_bytes(), domain_relative)
        digest = store.save_draft(candidate, expected_digest=None)
        review = Review(digest, "Software observation", "Software observation",
                        "Temporary component fixture, not owner/domain approval.", observed_at)
        version = store.publish(review, published_at=observed_at)
        snapshot = store.resolve_knowledge(version)
        cutoff = "2026-06-22T23:59:59+00:00"
        selected = TableSource.from_bytes(selected_raw, source_id="findings", kind="finding_input")
        registry = TableSource.from_bytes(raw_registry, source_id="registry", kind="registry_input")
        bundle = build_context(selected, registry, snapshot, cutoff)
        reversed_bundle = build_context(
            TableSource.from_bytes(reversed_raw, source_id="findings", kind="finding_input"),
            TableSource.from_bytes(reversed_registry, source_id="registry", kind="registry_input"),
            snapshot, cutoff)
        payload = bundle.payload
        checks = {
            "exact_development_membership": set(bundle.finding_ids) == allowed,
            "no_test_finding_membership": not set(bundle.finding_ids) & set(split["partitions"]["test"]),
            "required_B01_findings_present": {"F-1003", "F-1017", "F-1016"} <= set(bundle.finding_ids),
            "correct_primary_comments": all(
                payload["registry"][row["equipment_id"]]["engineer_comment"]
                == next(item["engineer_comment"] for item in registry_rows
                        if item["equipment_id"] == row["equipment_id"]) for row in selected_rows),
            "complete_original_domain": payload["domain"]["text"] == snapshot.domain_bytes.decode("utf-8"),
            "row_reversal_semantic_hash_equal": bundle.context_hash == reversed_bundle.context_hash,
            "row_reversal_raw_hashes_differ": selected.raw_sha256 != sha256(reversed_raw),
            "row_reversal_source_index_equal": bundle.source_index == reversed_bundle.source_index,
            "no_evaluation_source_kinds": not any(
                item["kind"].startswith("evaluation_") for item in bundle.to_dict()["source_manifest"]),
        }
        files = {
            "selected-development.csv": selected_raw,
            "temporary-fixture-release.json": snapshot.release_bytes,
            "context-v1.json": serialize_context(bundle),
            "context-reversed-v1.json": serialize_context(reversed_bundle),
            "workflow-v0.json": WorkflowExport.from_bundle(snapshot, bundle, selected, registry, cutoff).encoded,
        }
        lifecycle_observations = {}
        variants = {
            "retired": {"status": "retired", "retirement_reason": "Software-fixture withdrawal only."},
            "not_yet_effective": {"effective_from": "2026-06-23T00:00:00Z"},
            "expired": {"effective_until": cutoff},
        }
        for state, change in variants.items():
            changed = strict_json(canonical_bytes(candidate))
            changed["base_release_id"] = version
            changed["guidance"]["psv-assessment"]["lifecycle"].update(change)
            digest = store.save_draft(changed, expected_digest=digest)
            changed_version = store.publish(Review(
                digest, "Software observation", "Software observation",
                "Temporary lifecycle fixture, not owner/domain approval.", observed_at,
            ), published_at=observed_at)
            changed_snapshot = store.resolve_knowledge(changed_version)
            changed_bundle = build_context(selected, registry, changed_snapshot, cutoff)
            changed_export = WorkflowExport.from_bundle(changed_snapshot, changed_bundle, selected, registry, cutoff)
            active, excluded = effective_guidance(changed_snapshot.candidate, cutoff)
            checks[f"lifecycle_{state}_excluded"] = (
                active == () and excluded == {"psv-assessment": state}
                and changed_bundle.payload["managed_knowledge"]["guidance"] == {}
                and b"psv-assessment" not in changed_bundle.encoded
                and b"psv-assessment" not in changed_export.encoded)
            files.update({
                f"lifecycle-{state}-fixture-release.json": changed_snapshot.release_bytes,
                f"lifecycle-{state}-context-v1.json": changed_bundle.encoded,
                f"lifecycle-{state}-workflow-v0.json": changed_export.encoded,
            })
            lifecycle_observations[state] = {
                "knowledge_version": changed_version, "context_hash": changed_bundle.context_hash,
                "active_guidance_ids": active, "excluded_guidance": excluded,
            }
        checks["lifecycle_original_pin_unchanged"] = (
            store.resolve_knowledge(version).release_bytes == snapshot.release_bytes
            and build_context(selected, registry, snapshot, cutoff).encoded == bundle.encoded)
        artifacts.mkdir(parents=True, exist_ok=False)
        for name, raw in files.items():
            _write(artifacts / name, raw, replace=False)
        return {
            "scope": "offline_source_delivery_not_provider_capture_or_knowledge_influence",
            "checks": checks, "finding_ids": bundle.finding_ids,
            "assessment_time": cutoff, "knowledge_version": version,
            "release_approval": "temporary_software_fixture_not_owner_or_domain_approval",
            "lifecycle": lifecycle_observations,
            "context_hash": bundle.context_hash, "context_bytes": len(serialize_context(bundle)),
            "source_file_sha256": {"findings_original": sha256(raw_findings),
                                   "registry_original": sha256(raw_registry)},
            "artifacts": {str(artifacts / name): sha256(raw) for name, raw in files.items()},
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline knowledge component observations; no model sends.")
    parser.add_argument("--output", type=Path, required=True, help="Append-only observations ledger.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    now = datetime.now(timezone.utc).isoformat()
    observation_id = uuid.uuid4().hex
    paths = [
        *sorted((root / "triage_knowledge").glob("*.py")),
        *sorted((root / "triage").glob("*.py")),
        *sorted((root / "llm_inference").glob("*.py")),
        *sorted((root / "tests").glob("*knowledge*.py")), Path(__file__).resolve(),
        root / "tools" / "probe_knowledge.py",
        root / "tests" / "triage_support.py", root / "tests" / "test_triage.py",
        root / "pyproject.toml", root / "docs" / "06_KNOWLEDGE_CONTEXT.md",
        root / "eval" / "spec" / "acceptance.json", root / "eval" / "spec" / "split.json",
    ]
    before = {str(path.relative_to(root)): sha256(path.read_bytes()) for path in paths}
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), pattern="test_knowledge*.py",
                                               top_level_dir=str(root))
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    validator = subprocess.run([sys.executable, "-B", "-m", "eval.validate"], cwd=root,
                               capture_output=True, text=True)
    artifacts = args.output.parent / "component-artifacts" / observation_id
    try:
        delivery = development_delivery(root, artifacts, now)
    except (KnowledgeError, OSError, csv.Error) as error:
        delivery = {"checks": {"execution_succeeded": False},
                    "error_class": error.code if isinstance(error, KnowledgeError) else type(error).__name__,
                    "message": str(error), "partial_artifact_directory": str(artifacts)}
    after = {str(path.relative_to(root)): sha256(path.read_bytes()) for path in paths}
    success = (result.wasSuccessful() and not result.skipped and validator.returncode == 0
               and all(delivery["checks"].values()) and before == after)
    observation = {
        "id": observation_id, "observed_at": now,
        "command": [sys.executable, "-B", "-m", "tools.verify_knowledge", "--output", str(args.output)],
        "scope": "offline_knowledge_component_and_provisional_workflow_handoff_not_system_acceptance",
        "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
        "reference_version": strict_json((root / "eval" / "spec" / "split.json").read_bytes())["version"],
        "python_version": sys.version,
        "input_sha256_before": before, "input_sha256": after,
        "code_stable_during_run": before == after,
        "component_status": "pass" if success else "failed_or_incomplete",
        "tests": {"run": result.testsRun, "failures": [(t.id(), text) for t, text in result.failures],
                  "errors": [(t.id(), text) for t, text in result.errors],
                  "skipped": [(t.id(), reason) for t, reason in result.skipped], "log": log.getvalue()},
        "reference_validation": {"command": [sys.executable, "-B", "-m", "eval.validate"],
                                 "exit_code": validator.returncode,
                                 "stdout": validator.stdout, "stderr": validator.stderr},
        "development_delivery": delivery,
        "scenario_status": {
            "B01": "component_and_fake_provider_wiring_only_actual_provider_capture_pending",
            "B02": "isolated_overlay_delivery_tested_real_model_behavior_probe_not_run",
            "B03": "editor_path_exercised_final_owner_DESIGN_and_domain_review_pending",
            "D02": "component_gap_and_invalid_primary_checks_only",
            "X01": "context_snapshot_invariance_only_real_decision_stability_not_run",
            "X02": "module_reproduction_only_final_all_21_delivery_not_run",
        },
        "provider_sends": 0, "paid_model_eval_run": False, "frozen_test_assessment_run": False,
        "model": None, "model_usage": None, "model_cost": None,
        "notes": [
            "AppTest is an executable Streamlit form test, not a screenshot or operational approval.",
            "Temporary test reviews and any fake-provider tickets are software fixtures, not owner-approved knowledge or triage quality evidence.",
            "Raw-source/request artifacts remain local. No test descriptions/cards/expected answers were put in production context.",
            "The workflow-v0 projection is provisional; the native version-1 bundle remains the authoritative source artifact.",
            "Other sessions may change this checkout; recorded hashes are not an atomic repository freeze.",
            "Lifecycle cases extend B01-B03 component coverage; frozen reference expectations are unchanged.",
        ],
    }
    ledger = strict_json(args.output.read_bytes()) if args.output.exists() else {"observations": []}
    if not isinstance(ledger, dict) or set(ledger) != {"observations"} or not isinstance(ledger["observations"], list):
        raise ValueError("Invalid observations ledger; refusing to overwrite it.")
    ledger["observations"].append(observation)
    _write(args.output, (json.dumps(ledger, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode(),
           replace=args.output.exists())
    print(json.dumps({"component_status": observation["component_status"],
                      "tests": result.testsRun, "failures": len(result.failures),
                      "errors": len(result.errors), "skipped": len(result.skipped),
                      "code_stable_during_run": before == after,
                      "reference_validation_exit": validator.returncode,
                      "development_delivery": delivery["checks"], "provider_sends": 0,
                      "output": str(args.output)}, indent=2))
    if not success:
        print(log.getvalue(), file=sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
