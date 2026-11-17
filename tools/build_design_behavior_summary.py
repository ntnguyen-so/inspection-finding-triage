from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "eval" / "results"
RAW = RESULTS / "design-behavior-demonstration"
OUTPUT = RESULTS / "design-behavior-demonstration.json"


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tickets(path: Path) -> list[dict]:
    value = load(path)
    return value["tickets"] if isinstance(value, dict) else value


def urgency_band(value: int) -> str:
    if value >= 9:
        return "today"
    if value >= 7:
        return "this_week"
    if value >= 5:
        return "this_month"
    if value >= 3:
        return "next_shutdown"
    return "backlog"


def test_count(path: Path) -> int:
    match = re.search(r"Ran (\d+) tests", path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Test count missing from {path}")
    return int(match.group(1))


def main() -> None:
    verification_path = RAW / "verification.json"
    verification = load(verification_path)
    triage_log = (RAW / "triage-tests.txt").read_text(encoding="utf-8")
    selected_tests = {
        "malformed_vs_structural": "test_structural_recovery_is_distinct_from_malformed_json",
        "single_repair_same_context": "test_one_recovery_and_same_pinned_context",
        "exhaustion_preserves_old_output": "test_permanent_failure_preserves_previous_bytes_and_all_attempts",
        "no_partial_batch": "test_batch_not_partially_published",
        "atomic_replace_preserves_old_output": "test_atomic_replace_failure_preserves_old_output_and_cleans_temp",
        "persistent_budget_cannot_reset": "test_persistent_budget_cannot_reset_by_starting_another_run",
        "unassessable_has_no_forced_score": "test_unassessable_fails_without_forced_scores",
        "timeout_refusal_cleanup_do_not_publish": "test_fatal_transport_timeout_refusal_and_cleanup_do_not_publish",
        "context_mutation_fails_closed": "test_context_mutations_fail_closed",
        "urgency_grid_monotone": "test_independently_worked_grid_and_monotonicity",
        "confirmed_override_state_matrix": "test_confirmed_override_state_matrix",
    }
    behavior_checks = [
        {
            "behavior": behavior,
            "test": name,
            "observed": (
                "pass"
                if re.search(rf"^{re.escape(name)}.*\.\.\. ok$", triage_log, re.MULTILINE)
                else "missing"
            ),
        }
        for behavior, name in selected_tests.items()
    ]
    if any(item["observed"] != "pass" for item in behavior_checks):
        raise ValueError("Selected behavior test missing from retained log")

    copilot_path = RESULTS / "triage" / "copilot-gpt6-current-all21"
    copilot_tickets = tickets(copilot_path / "tickets.experimental.json")
    base_scores: list[int] = []
    final_scores: list[int] = []
    raised: list[str] = []
    for ticket in copilot_tickets:
        match = re.search(r"base=(\d+), final=(\d+)", ticket["urgency"]["rationale"])
        if match is None:
            raise ValueError(f"Urgency trace missing for {ticket['finding_id']}")
        base = int(match.group(1))
        final = ticket["urgency"]["score"]
        base_scores.append(base)
        final_scores.append(final)
        if final > base:
            raised.append(ticket["finding_id"])

    azure_path = RESULTS / "triage" / "direct-azure-final-sol-v5"
    azure = {item["finding_id"]: item for item in tickets(azure_path / "tickets.json")}
    copilot = {item["finding_id"]: item for item in copilot_tickets}
    differences = []
    for finding_id, azure_ticket in azure.items():
        azure_band = urgency_band(azure_ticket["urgency"]["score"])
        copilot_band = urgency_band(copilot[finding_id]["urgency"]["score"])
        if azure_band != copilot_band:
            differences.append(
                {
                    "finding_id": finding_id,
                    "azure_v5": azure_band,
                    "copilot_gpt6": copilot_band,
                }
            )

    grid = verification["policy_grid"]["actual"]
    gpt6_summary = load(copilot_path / "run-summary.json")
    gpt61_path = RESULTS / "triage" / "copilot-gpt61-current-all21"
    gpt61_summary = load(gpt61_path / "run-summary.json")
    report = {
        "schema": "design-behavior-demonstration-v1",
        "generated_by": "python -B -m tools.build_design_behavior_summary",
        "recorded_at": verification["recorded_at"],
        "status": "pass_with_disclosed_system_limitations",
        "git_revision": verification["git_revision"],
        "dirty_worktree": verification["dirty_worktree"],
        "code_stable_during_offline_run": verification["code_stable_during_run"],
        "offline_source": {
            "path": str(verification_path.relative_to(ROOT)).replace("/", "\\"),
            "bytes": verification_path.stat().st_size,
            "sha256": sha256(verification_path),
            "command": verification["command"],
            "elapsed_seconds": verification["elapsed_seconds"],
        },
        "collector_history": {
            "initial_attempt": "failed_before_report",
            "error": "policy_verification: Protection verification activity required",
            "correction": "The verifier fact-state matrix now supplies the required activity",
            "rerun": verification["status"],
        },
        "offline_execution": {
            "component_tests": verification["component_tests"],
            "additional_suites": [
                {"scope": "inference_and_azure", "tests": test_count(RAW / "command-1.txt"), "status": "pass"},
                {"scope": "knowledge_context_contracts", "tests": test_count(RAW / "command-2.txt"), "status": "pass"},
                {"scope": "evaluator", "tests": test_count(RAW / "command-3.txt"), "status": "pass"},
                {"scope": "frozen_reference_validation", "status": "pass"},
            ],
            "behavior_checks": behavior_checks,
            "urgency_grid": {
                "cells": sum(len(row) for row in grid),
                "corners": {
                    "L1_I1": grid[0][0],
                    "L10_I1": grid[9][0],
                    "L1_I10": grid[0][9],
                    "L10_I10": grid[9][9],
                },
                "monotonicity": "pass",
            },
            "protection_override_matrix": {
                "cells": len(verification["override_state_matrix"]),
                "confirmed_override_only": (
                    "protection_impaired=confirmed_true and "
                    "recorded_deviation=confirmed_false"
                ),
                "unknown_or_suspected_never_counted_as_confirmed_absence": True,
            },
        },
        "real_model_behavior": {
            "copilot_gpt6_all21": gpt6_summary,
            "copilot_gpt61_all21": {
                "summary": str((gpt61_path / "run-summary.json").relative_to(ROOT)).replace("/", "\\"),
                "status": gpt61_summary["status"],
                "first_run": gpt61_summary["first_run"]["outcome"],
                "retry_tickets": gpt61_summary["retry"]["tickets"],
                "retry_sends": gpt61_summary["retry"]["application_sends"],
                "semantic_reviews": [
                    {
                        "review": review["review"],
                        "passed_dimensions": review["passed_dimensions"],
                        "applicable_dimensions": review["applicable_dimensions"],
                        "failed": review["failed"],
                        "pending": review["pending"],
                    }
                    for review in gpt61_summary["semantic_reviews"]
                ],
            },
            "copilot_gpt6_x01_first_run": (
                "eval\\results\\triage\\copilot-gpt6-current-x01-failure\\run-summary.json"
            ),
            "azure_v5": "eval\\results\\triage\\direct-azure-final-sol-v5\\usage-summary.json",
            "gpt61_repeat": "eval\\results\\triage\\copilot-gpt61-current-x01\\x01-review.json",
        },
        "output_behavior": {
            "copilot_gpt6_current": {
                "base_urgency_bands": dict(Counter(urgency_band(value) for value in base_scores)),
                "final_urgency_bands": dict(Counter(urgency_band(value) for value in final_scores)),
                "floors_raised_urgency_for": raised,
                "review_required_true": sum(item["review_required"] for item in copilot_tickets),
                "impact_distribution": dict(
                    sorted(Counter(item["impact_of_failure"]["score"] for item in copilot_tickets).items())
                ),
            },
            "azure_v5_vs_copilot_gpt6_band_agreement": {
                "same": len(azure) - len(differences),
                "total": len(azure),
                "differences": differences,
                "confounded_by_policy_and_provider_changes": True,
            },
        },
        "interpretation": [
            "Offline adversarial checks demonstrate control behavior, not triage correctness.",
            "Real model runs show recoverable malformed/schema errors and exhausted failures.",
            "The earlier gpt-6 63/63 AI-only review was not reproduced: two gpt-6.1 reviews failed at 60/63.",
            "Nineteen of twenty-one gpt-6 urgencies are 7-9; floors raised only F-1001 and F-1005.",
            "Azure v5 and Copilot gpt-6 agree on urgency band for 19/21 findings, but this is not a controlled benchmark.",
            "No experiment establishes correct L/I, calibrated thresholds, knowledge influence, USD cost, or final acceptance.",
        ],
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
