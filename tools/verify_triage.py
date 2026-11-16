"""Collect offline production-component evidence; not model or system acceptance."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

from tests import triage_support
from triage.policy import base_urgency, derive_policy


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprints() -> dict:
    files = [ROOT / "pyproject.toml", ROOT / "README.md", ROOT / "AGENTS.md",
             ROOT / "docs" / "05_TRIAGE_WORKFLOW.md", Path(__file__),
             ROOT / "tools" / "probe_triage.py", ROOT / "tools" / "integrate_triage.py",
             ROOT / "tools" / "probe_native_knowledge.py"]
    for package in ("triage", "llm_inference", "triage_knowledge"):
        files.extend(sorted((ROOT / package).glob("*.py")))
    files.extend(ROOT / "tests" / name for name in (
        "__init__.py", "test_triage.py", "test_copilot_triage.py", "triage_support.py",
        "test_inference.py", "test_azure.py", "test_source_workflow.py", "test_knowledge_workflow.py",
        "test_source_context.py", "test_source_knowledge.py", "test_integration_triage.py",
        "test_native_knowledge_probe.py", "test_probe_knowledge_context.py",
    ))
    files.extend(sorted((ROOT / "eval").glob("*.py")))
    files.extend(sorted((ROOT / "eval" / "tests").glob("*.py")))
    files.extend(sorted((ROOT / "eval" / "spec").glob("*.json")))
    files.extend([ROOT / "docs" / "06_KNOWLEDGE_DESIGN_DECISION.md",
                  ROOT / "tests" / "knowledge_support.py"])
    files.extend([ROOT / "eval" / "spec" / "split.json", ROOT / "eval" / "spec" / "acceptance.json"])
    return {str(path.relative_to(ROOT)): sha256(path) for path in files}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory; never reused")
    args = parser.parse_args(argv)
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before = fingerprints()
    git = subprocess.run(["git", "--no-pager", "rev-parse", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "--no-pager", "status", "--short", "--untracked-files=normal"],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout
    (target / "worktree.txt").write_text(dirty, encoding="utf-8")
    triage_support.ARTIFACT_ROOT = target / "synthetic-component-artifacts"
    triage_support.ARTIFACT_ROOT.mkdir()
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        "tests.test_triage", "tests.test_copilot_triage", "tests.test_source_workflow",
        "tests.test_knowledge_workflow", "tests.test_integration_triage", "tests.test_native_knowledge_probe",
    ])
    try:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    finally:
        triage_support.ARTIFACT_ROOT = None
    (target / "triage-tests.txt").write_text(log.getvalue(), encoding="utf-8")
    commands = []
    for arguments in (
        ["-B", "-m", "unittest", "tests.test_inference", "tests.test_azure", "-q"],
        ["-B", "-m", "unittest", "tests.test_source_context", "tests.test_source_knowledge",
         "tests.test_probe_knowledge_context", "-q"],
        ["-B", "-m", "unittest", "discover", "-s", "eval\\tests", "-p", "test_*.py", "-q"],
        ["-B", "-m", "eval.validate"],
        ["-B", "-m", "eval.assess", "--partition", "development", "--checklist"],
        ["-I", "-B", "-c", "import triage, triage_knowledge; from triage.policy import base_urgency; assert base_urgency(1,10)==8; print(triage.__file__); print(triage_knowledge.__file__)"],
    ):
        command = [sys.executable, *arguments]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        name = f"command-{len(commands) + 1}.txt"
        (target / name).write_text(completed.stdout + completed.stderr, encoding="utf-8")
        commands.append({"command": command, "exit_code": completed.returncode, "log": name})
    grid = [[base_urgency(likelihood, impact) for impact in range(1, 11)] for likelihood in range(1, 11)]
    matrix = []
    for impairment in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
        for deviation in ("confirmed_true", "confirmed_false", "suspected", "unknown"):
            values = triage_support.facts()
            values["protection_impaired"]["state"] = impairment
            values["recorded_deviation"].update(state=deviation, verification_activity="Check deviation log.")
            actual = derive_policy(1, 1, values, [], sce=False, gaps=[])
            matrix.append({"protection_impaired": impairment, "recorded_deviation": deviation,
                           "actual_policy": actual})
    after = fingerprints()
    unchanged = before == after
    successful = result.wasSuccessful() and all(x["exit_code"] == 0 for x in commands) and unchanged
    scenarios = {}
    covered = {"A01", "A02", "A03", "B01", "C01", "C02", "C03", "D02"}
    for identifier in (
        "A01", "A02", "A03", "A04", "B01", "B02", "B03", "C01", "C02",
        "C03", "C04", "D01", "D02", "D03", "D04", "X01", "X02",
    ):
        scenarios[identifier] = {
            "status": ("deterministic_component_evidence_only" if successful else "failed_component_verification")
            if identifier in covered else "not_executed",
            "system_acceptance": "not_established",
        }
    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, "-B", "-m", "tools.verify_triage", *sys.argv[1:]],
        "status": "offline_checks_passed" if successful else "offline_checks_failed",
        "scope": "Production workflow/native source-first store, release, retrieval, builder and CLI with synthetic declarations/inference; NOT human content approval or real-model acceptance.",
        "git_revision": git, "dirty_worktree": bool(dirty), "code_stable_during_run": unchanged,
        "stability_scope": "Executed workflow/inference/knowledge dependencies and regression tests; not unrelated concurrent files or a whole-system freeze.",
        "hashes_before": before, "hashes_after": after,
        "reference_version": json.loads((ROOT / "eval" / "spec" / "split.json").read_text())["version"],
        "component_tests": {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                            "skipped": len(result.skipped), "log": "triage-tests.txt"},
        "commands": commands,
        "policy_grid": {"rows": "likelihood 1..10", "columns": "impact 1..10", "actual": grid,
                        "independent_expected": "Literal hand-worked table in tests\\test_triage.py"},
        "override_state_matrix": matrix,
        "real_provider_dispatches": 0, "live_generation_usage": None, "live_generation_cost_usd": None,
        "cost_note": "No real provider invoked; synthetic receipts do not measure model billing.",
        "elapsed_seconds": time.monotonic() - started,
        "scenarios": scenarios,
        "remaining_gates": [
            "Native bundle-3 delivery passes software fixtures; actual provider-bound B01 and native B02 remain unexecuted.",
            "The explicit isolated-probe native API has software coverage; this offline collector does not execute real B02.",
            "Genuine owner-approved maintained knowledge release; B01-B03 actual provider-bound/maintenance evidence.",
            "Owner final system design and provider/model/settings/pricing/phase+review budget sign-off.",
            "Calibrated semantic reviewer; real development generation, semantic review and X01 repeats.",
            "Prerequisite-gated frozen test, automated all-input final tickets and delivery reproduction.",
        ],
    }
    upstream = ROOT / "eval" / "results" / "knowledge" / "extraction" / "source-first-verification-1" / "readiness.json"
    store = ROOT / "knowledge" / "source-first"
    report["system_release_preflight"] = {
        "status": "blocked_not_system_accepted",
        "scope": "Read-only checkout observations, not live semantic evaluation or a waiver of prerequisites.",
        "default_source_store": str(store.relative_to(ROOT)),
        "default_source_store_exists": store.exists(),
        "default_store_release_ids": sorted(path.stem for path in (store / "releases").glob("*.json")),
        "owner_design_exists": (ROOT / "DESIGN.md").is_file(),
        "root_final_tickets_exists": (ROOT / "tickets.json").is_file(),
        "upstream_historical_observation": {
            "path": str(upstream.relative_to(ROOT)), "sha256": sha256(upstream) if upstream.exists() else None,
            "note": "Recorded upstream observation only; not qualification of concurrent edits.",
        },
        "native_b02": "isolated_probe_api_available_real_model_not_executed_by_offline_collector",
        "real_development_semantic_review": "not_executed_in_this_run",
        "fixed_config_x01_repeat": "not_executed_in_this_run",
        "frozen_test": "not_opened_prerequisites_unmet",
        "final_all_21_generation": "not_executed_prerequisites_unmet",
        "strict_provider_pricing_and_phase_review_budgets": "not_established_by_offline_checks",
        "automated_software_pass_is_not_release_approval": True,
    }
    artifact_hashes = {str(path.relative_to(target)): sha256(path)
                       for path in sorted(target.rglob("*")) if path.is_file()}
    report["artifact_sha256"] = artifact_hashes
    (target / "verification.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"status": report["status"], "tests": result.testsRun,
                      "report": str(target / "verification.json")}))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
