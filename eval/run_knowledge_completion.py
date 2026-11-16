"""Bounded v3 extraction/selector experiment; no inference without --allow-inference.

Plan: python -B -m eval.run_knowledge_completion --plan-only
Authorized execution additionally requires --output <new-results-child>.
Save --plan-only JSON first, then supply that exact reviewed plan via --freeze.
This is non-blind programmatic regression evidence, never automatic C1 adoption.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
from statistics import median
from typing import Any

from llm_inference import InferenceError

from . import run_knowledge as existing
from .knowledge_attempts import AttemptLedger, fingerprint, inspect_ledger
from .knowledge_copilot import RECOVERABLE, request_record, run_requests
from .knowledge_eval import (
    ROOT, Suite, assess_attempts, assess_repeats, assess_retrieval,
    canonical_hash, load_suite, read_json,
)
from .knowledge_query_inputs import load_registry_fixture


RESULTS = existing.RESULTS
PRIOR_LEDGER = RESULTS / "source-first-completion.experimental-ledger.json"
LEDGER = RESULTS / "source-first-completion-v3.experimental-ledger.json"
CUMULATIVE_MAXIMUM = 26
PROFILE = {
    "version": "source-first-completion-v3", "provider": "copilot",
    "model": "gpt-6-luna", "reasoning_effort": "medium", "timeout_seconds": 120,
    "fallback": False,
}
REVISION_DISCLOSURE = (
    "Post-development generic prompt correction after v2's third development "
    "proposal failed critical semantic validation. All thirteen v3 slots are "
    "fresh requests; no accepted v2 outputs are reused. The v2 ledger and "
    "observations remain unchanged. This is not a blind test or C1 qualification."
)
DISCLOSURE = (
    "SOFTWARE-ONLY fixture review of ALL unchanged raw C1 groups. "
    "Not genuine editorial review, human approval, engineering approval or "
    "review-effort evidence. No expected labels repair proposals. "
    "Published releases are isolated experimental fixtures, not production adoption."
)


def code_identity(root: Path = ROOT) -> dict[str, Any]:
    """Content identity without invoking Git or claiming a known revision/dirty state."""
    inventory = {}
    for directory in ("eval", "triage_knowledge", "llm_inference"):
        paths = list((root / directory).glob("*.py"))
        if directory == "eval":
            paths.extend((root / directory / "tests").glob("*.py"))
        for path in sorted(paths):
            inventory[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "revision": None, "dirty_status": None,
        "provenance_limitation": "Git was not invoked; current executable bytes are pinned.",
        "files_sha256": inventory, "code_sha256": canonical_hash(inventory),
    }


def prior_accounting() -> dict[str, Any]:
    ledgers = []
    for relative in (existing.LEDGER, PRIOR_LEDGER):
        path = ROOT / relative
        raw = path.read_bytes()
        observed = inspect_ledger(path)
        if path.read_bytes() != raw:
            raise ValueError("Prior extraction ledger changed during inspection")
        if any(attempt["state"] != "finished" for attempt in observed["attempts"]):
            raise ValueError("Prior extraction ledger has unresolved reserved sends")
        ledgers.append({
            "path": str(relative), "sha256": hashlib.sha256(raw).hexdigest(),
            "application_attempts_reserved": observed["application_attempts_reserved"],
            "spent_states": [
                {key: attempt[key] for key in ("number", "slot", "state", "request_sha256")}
                | {"status": attempt["outcome"]["status"],
                   "error_class": attempt["outcome"].get("error_class")}
                for attempt in observed["attempts"]
            ],
        })
    return {
        "ledgers": ledgers,
        "application_attempts_reserved": sum(row["application_attempts_reserved"] for row in ledgers),
    }


def verify_cumulative_budget(freeze, *, require_current=False):
    prior = prior_accounting()
    if prior != freeze["prior_extraction_accounting"]:
        raise ValueError("Prior extraction ledgers differ from their frozen hashes/accounting")
    maximum = CUMULATIVE_MAXIMUM - prior["application_attempts_reserved"]
    if (freeze["maximum_cumulative_application_attempts"] != CUMULATIVE_MAXIMUM
            or freeze["maximum_application_attempts"] != maximum):
        raise ValueError("Cumulative extraction ceiling cannot be increased or reset")
    path = ROOT / freeze["ledger"]
    if path.exists():
        current = inspect_ledger(path)
        if current["maximum_application_attempts"] != maximum:
            raise ValueError("Current ledger ceiling does not match the cumulative remainder")
        count = current["application_attempts_reserved"]
    elif require_current:
        raise ValueError("The current application-send ledger is missing")
    else:
        count = 0
    total = prior["application_attempts_reserved"] + count
    if total > CUMULATIVE_MAXIMUM:
        raise ValueError("Cumulative extraction application-send budget exceeded")
    return {
        "status": "pass", "prior_extraction_reserved": prior["application_attempts_reserved"],
        "current_reserved": count, "cumulative_reserved": total,
        "maximum_cumulative_application_attempts": CUMULATIVE_MAXIMUM,
        "remaining_application_attempts": CUMULATIVE_MAXIMUM - total,
    }


def build_plan(suite: Suite, identity: dict[str, Any]):
    """Freeze the original slots in development/shared/evaluation/repeat order."""
    runtime = importlib.import_module("triage_knowledge.source")
    schedule = [
        row["source_id"] + ".primary"
        for partition in ("development", "shared_smoke", "evaluation")
        for row in suite.manifest["sources"] if row["partition"] == partition
    ] + [slot for slot in suite.manifest["slot_ids"] if ".repeat" in slot]
    if (len(schedule) != 13 or len(set(schedule)) != 13
            or set(schedule) != set(suite.manifest["slot_ids"])
            or sum(row["partition"] == "development" for row in suite.manifest["sources"]) != 4
            or schedule[4] != "original_domain.primary"):
        raise ValueError("Completion requires the original thirteen-slot denominator")
    documents = {sid: existing.document_for(suite, sid) for sid in suite.sources}
    requests = {
        slot: runtime.extraction_request(
            documents[slot.rsplit(".", 1)[0]], model=PROFILE["model"],
            reasoning_effort=PROFILE["reasoning_effort"],
            timeout_seconds=PROFILE["timeout_seconds"],
        ) for slot in schedule
    }
    # The existing driver calls its fail-stop set "development_slots". Include
    # every slot so an evaluation semantic failure cannot permit later sends.
    stop_slots = frozenset(schedule)
    registry_fixture = load_registry_fixture(suite)
    if registry_fixture is None:
        raise ValueError("Completion requires the frozen shared registry fixture")
    registry_pin = {key: registry_fixture[key] for key in ("path", "sha256", "registry_sha256")}
    prior = prior_accounting()
    maximum_attempts = CUMULATIVE_MAXIMUM - prior["application_attempts_reserved"]
    if maximum_attempts < 1:
        raise ValueError("No cumulative extraction application-send budget remains")
    freeze = {
        "contract": "knowledge-completion-freeze-v3", "profile": dict(PROFILE),
        "code_identity": identity,
        "reference_version": suite.manifest["version"],
        "grader_version": suite.manifest.get("grader_version"),
        "manifest_sha256": hashlib.sha256(
            (ROOT / "eval" / "spec" / "knowledge_extraction.json").read_bytes()
        ).hexdigest(),
        "reference_sha256": suite.manifest["reference_sha256"],
        "source_hashes": {sid: hashlib.sha256(raw).hexdigest() for sid, raw in suite.sources.items()},
        "source_paths": {row["source_id"]: row["path"] for row in suite.manifest["sources"]},
        "reference_path": suite.manifest["reference"],
        "schedule": schedule, "development_and_original_prefix": schedule[:5],
        "driver_development_slots": sorted(stop_slots),
        "driver_stop_policy": "All slots fail-stop; driver field is NOT a partition declaration.",
        "repeat_source_ids": list(suite.manifest["repeat_source_ids"]),
        "request_hashes": {slot: fingerprint(request_record(req)) for slot, req in requests.items()},
        "query_input_policy": "Unchanged frozen subjects; identical fixed source-literal/input registry for all C0/C1 queries.",
        "query_registry_fixture": registry_pin,
        "registry_construction": registry_fixture["construction"],
        "dispatch_readiness": {
            "status": "ready_explicit_cli_authorization",
            "note": "Parent must freeze this exact reviewed plan first; --freeze and --allow-inference are both required.",
        },
        "prior_extraction_accounting": prior, "revision_disclosure": REVISION_DISCLOSURE,
        "cumulative_budget_scope": "Original extraction + completion v2 + v3 only; historical B02 and the separate two-send handoff cohort are not extraction attempts.",
        "maximum_cumulative_application_attempts": CUMULATIVE_MAXIMUM,
        "maximum_application_attempts": maximum_attempts, "maximum_attempts_per_slot": 2,
        "recoverable_codes": sorted(RECOVERABLE), "semantic_retry_allowed": False,
        "assessment_time": existing.ASSESSMENT_TIME,
        "ledger": str(LEDGER), "review_disclosure": DISCLOSURE,
        "exposure": suite.manifest.get("exposure"),
        "study_kind": "non_blind_regression_not_new_blind_test",
        "C0_role": "Unchanged raw C0 negative selection baseline; not a positive selection gate.",
        "prior_experiment": {
            "ledger": str(existing.LEDGER), "changed_or_resumed": False,
            "reported_application_sends": 1, "reported_unexecuted_slots": 12,
            "reported_result": "invalid_local_proof_development_proposal",
            "provenance": "Prior observation supplied in authorization; not regraded here.",
        },
        "existing_runner_pending_exit": 2,
        "integration_strategy": {"selectable": "C1 experimental source-first selector", "selected": False},
        "human_effort": "unexecuted", "usd_cost": None, "C1_qualified": False,
    }
    phase = PROFILE["version"] + "-" + canonical_hash(freeze)
    ledger_plan = {
        "phase": phase, "slots": freeze["request_hashes"],
        "maximum_attempts": maximum_attempts, "per_slot_attempts": 2,
        "schedule": schedule, "development_slots": sorted(stop_slots),
        "recoverable_codes": sorted(RECOVERABLE),
    }
    return requests, documents, freeze, ledger_plan


def plan_record(freeze, ledger_plan):
    return {"freeze": freeze, "ledger_plan": ledger_plan, "dispatch": False}


def verify_freeze(freeze: dict[str, Any]) -> None:
    if code_identity() != freeze["code_identity"]:
        raise ValueError("Executable bytes changed after freeze")
    pins = {
        str(Path("eval") / "spec" / "knowledge_extraction.json"): freeze["manifest_sha256"],
        freeze["reference_path"]: freeze["reference_sha256"],
        freeze["query_registry_fixture"]["path"]: freeze["query_registry_fixture"]["sha256"],
    }
    pins.update({freeze["source_paths"][sid]: digest for sid, digest in freeze["source_hashes"].items()})
    for path, digest in pins.items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Frozen source/reference bytes changed")


class CapturedProvider:
    """Capture the exact request at the existing provider boundary, not a reconstruction."""

    def __init__(self, provider, requests, freeze, writer):
        self.provider, self.freeze, self.writer = provider, freeze, writer
        self.slots = {id(request): slot for slot, request in requests.items()}
        self.number = 0

    async def generate(self, request):
        try:
            verify_freeze(self.freeze)
            verify_cumulative_budget(self.freeze, require_current=True)
            slot = self.slots[id(request)]
            actual = request_record(request)
            if fingerprint(actual) != self.freeze["request_hashes"][slot]:
                raise ValueError("Request changed after freeze")
        except (ValueError, KeyError) as error:
            raise InferenceError("freeze_mismatch", str(error)) from error
        self.number += 1
        self.writer.write(f"actual-requests\\request-{self.number:04d}.json", {
            "slot": slot, "request": actual,
            "request_sha256": fingerprint(actual),
            "capture_boundary": "immediately_before_CopilotProvider.generate",
            "sdk_internal_http_payload": "not_exposed",
        })
        return await self.provider.generate(request)


def _status(values) -> str:
    values = list(values)
    return "fail" if "fail" in values else "pass" if values and all(v == "pass" for v in values) else "unexecuted"


def attempt_assessment(suite, driver, requests):
    rows, counts = [], {}
    for attempt in driver["accounting"]["attempts"]:
        slot = attempt["slot"]
        counts[slot] = counts.get(slot, 0) + 1
        outcome = attempt["outcome"] or {}
        error = outcome.get("error_class")
        status = (
            "reserved" if attempt["state"] == "reserved" else
            "accepted" if outcome.get("status") == "success" else
            "structural_error" if error in {"malformed_json", "schema_violation"} else
            "transport_error" if error in {"transport", "timeout"} else
            "semantic_error" if error == "proposal_validation" else "refused"
        )
        request = requests[slot]
        rows.append({
            "slot_id": slot, "attempt": counts[slot], "status": status, "error_code": error,
            "source_sha256": hashlib.sha256(suite.sources[slot.rsplit(".", 1)[0]]).hexdigest(),
            "prompt_sha256": canonical_hash(request.system),
            "schema_sha256": canonical_hash(request.response_schema),
            "settings_sha256": canonical_hash(PROFILE),
            "model": request.model, "provider": "copilot",
        })
    return {"normalized_attempts": rows, "assessment": assess_attempts(suite, rows)}


def selector_diagnostic(suite, writer, extractions, *, freeze_sha256: str, registry_fixture):
    """Run all queries on partition-separated, software-reviewed raw C1 fixtures."""
    store_type = importlib.import_module("triage_knowledge.source_store").SourceKnowledgeStore
    runtime = importlib.import_module("triage_knowledge.retrieval")
    profile = {
        "experiment_id": PROFILE["version"] + "-" + freeze_sha256,
        "profile_version": PROFILE["version"], "freeze_sha256": freeze_sha256,
        "qualification": "unqualified_software_fixture",
    }
    observed, partitions = {}, {}
    registry_rows = registry_fixture["fixture"]["registry"]
    registry_pin = {key: registry_fixture[key] for key in ("path", "sha256", "registry_sha256")}
    for partition in ("development", "evaluation"):
        members = existing._partition_members(suite, partition)
        if not members <= extractions.keys():
            raise ValueError("No complete raw C1 primary partition")
        store = store_type(writer.root / "software-fixture-stores" / partition,
                           experimental_profile=profile)
        digest = store.create_draft([extractions[sid] for sid in sorted(members)])
        candidate, loaded = store.load_draft()
        if digest != loaded or any(item["review_state"] != "pending" for item in candidate["items"].values()):
            raise ValueError("Raw C1 draft unexpectedly reviewed")
        before = existing._candidate_content(candidate)
        for item_id in sorted(candidate["items"]):
            digest = store.review_item(
                item_id, expected_digest=digest, reviewer=existing.SOFTWARE_REVIEWER,
                reason=DISCLOSURE,
            )
        reviewed, loaded = store.load_draft()
        if (digest != loaded or existing._candidate_content(reviewed) != before
                or any(item["review_state"] != "reviewed" for item in reviewed["items"].values())):
            raise ValueError("Software review changed raw C1 content or missed groups")
        release_id = store.publish(
            expected_digest=digest, author=existing.SOFTWARE_REVIEWER,
            reviewer=existing.SOFTWARE_REVIEWER, reason=DISCLOSURE,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        partitions[partition] = {
            "source_ids": sorted(members), "release_id": release_id,
            "experimental_profile": profile, "raw_content_sha256": before,
            "review_kind": "synthetic_software_fixture",
            "review_disclosure": DISCLOSURE, "reviewed_group_count": len(reviewed["items"]),
            "human_approval_established": False,
        }
        for case_id, query_spec in suite.queries.items():
            if query_spec["source_id"] not in members:
                continue
            # Only authorized types form the runtime input. Expected atoms stay
            # inside the independent scorer, never the store, SDK or module.
            query = existing.query_rows(query_spec["subject_types"], shared_registry_rows=registry_rows)
            binding = existing.query_binding(query)
            result = runtime.get_triage_knowledge(
                store, query, knowledge_version=release_id,
                assessment_time=existing.ASSESSMENT_TIME,
                expected_strategy=runtime.strategy_binding(),
                allowed_input_binding=binding, max_bytes=64000,
            )
            raw, payload = result.to_dict(), result.provider_payload()
            adapted = existing.adapt_result(result)
            row = {
                "case_id": case_id, "source_id": query_spec["source_id"],
                "partition": partition, "query_context": query,
                "authorized_input_binding": binding.to_dict(),
                "query_registry_fixture": registry_pin,
                "result": raw, "provider_payload": payload,
                "local_evidence": result.evidence, "adapted_result": adapted,
                "assessment": assess_retrieval(suite, case_id, adapted),
                "captures_sha256": {
                    "result": canonical_hash(raw), "provider_payload": canonical_hash(payload),
                    "local_evidence": canonical_hash(result.evidence),
                },
                "synthetic_review_only": True, "human_approval_established": False,
                "selective_qualification": False,
            }
            observed[case_id] = row
            writer.write(f"queries\\{case_id}.json", row)
    if len(observed) != 24 or set(observed) != set(suite.queries):
        raise ValueError("Selector did not execute all twenty-four frozen queries")
    return {"partitions": partitions, "queries": observed, "review_disclosure": DISCLOSURE}


def _query_checks(suite, selector):
    queries = selector["queries"]
    recall, efficiency = {}, {}
    for case_id, row in queries.items():
        grade = row["assessment"]
        recall[case_id] = {
            "status": "pass" if grade.get("recall") == 1.0 and grade.get("broadening_ok") is True
            and grade.get("status") in {"pass", "fail"} else
            "unexecuted" if grade.get("status") == "needs_review" else "fail",
            "recall": grade.get("recall"), "broadening_ok": grade.get("broadening_ok"),
        }
    for case_id in suite.manifest["efficiency_case_ids"]:
        grade = queries[case_id]["assessment"]
        reduction = grade.get("irrelevant_byte_reduction")
        efficiency[case_id] = {
            "status": "pass" if grade.get("irrelevant_baseline_bytes", 0) > 0
            and reduction is not None
            and reduction >= suite.manifest["thresholds"]["each_scoped_irrelevant_byte_reduction"] else "fail",
            "reduction": reduction, "baseline_bytes": grade.get("irrelevant_baseline_bytes"),
            "returned_bytes": grade.get("irrelevant_returned_bytes"),
        }
    return {
        "retrieval": {"status": _status(row["assessment"]["status"] for row in queries.values()),
                      "query_count": len(queries)},
        "recall": {"status": _status(row["status"] for row in recall.values()), "cases": recall},
        "efficiency": {
            "status": _status(row["status"] for row in efficiency.values()), "cases": efficiency,
            "median_reduction": median(row["reduction"] for row in efficiency.values())
            if len(efficiency) == 8 and all(row["reduction"] is not None for row in efficiency.values()) else None,
        },
    }


async def run_completion(
    suite: Suite, writer: existing.EvidenceWriter, *, allow_inference=False, approved_plan=None,
):
    if not allow_inference:
        raise ValueError("Explicit --allow-inference is required")
    if approved_plan is None:
        raise ValueError("The earlier reviewed --freeze plan is required")
    requests, documents, freeze, plan = build_plan(suite, code_identity())
    if canonical_hash(approved_plan) != canonical_hash(plan_record(freeze, plan)):
        raise ValueError("Reviewed freeze plan differs from the current prepared experiment")
    verify_freeze(freeze)
    verify_cumulative_budget(freeze)
    registry_fixture = load_registry_fixture(suite)
    if registry_fixture is None:
        raise ValueError("Completion requires its frozen registry fixture")
    writer.write("freeze.json", freeze)
    writer.write("approved-plan.json", approved_plan)
    writer.write("prepared-requests.json", {slot: request_record(req) for slot, req in requests.items()})
    writer.write("query-registry-fixture.json", (ROOT / registry_fixture["path"]).read_bytes())
    ledger = AttemptLedger(ROOT / LEDGER, plan)
    if ledger.observation()["application_attempts_reserved"]:
        raise ValueError("Completion ledger already spent; no automatic resume or reset")
    verify_cumulative_budget(freeze, require_current=True)
    for sid, raw in suite.sources.items():
        writer.write(f"sources\\{sid}.bin", raw)

    baseline = existing.run_offline(
        suite, existing.EvidenceWriter(writer.root / "C0baseline"),
        identity={"code": freeze["code_identity"], "experiment_freeze": canonical_hash(freeze)},
        synthetic_review_diagnostic=True,
    )
    if baseline.get("query_registry_fixture") != freeze["query_registry_fixture"]:
        raise ValueError("C0 and C1 must use the identical frozen global registry fixture")
    checks = {
        "C0_hard_extraction": {
            "status": _status(row["assessment"]["status"] for row in baseline["source_assessments"]),
            "source_count": len(baseline["source_assessments"]),
        },
        "C0_negative_baseline_observed": {
            "status": "pass" if baseline["query_count"] == 24
            and len(baseline["source_assessments"]) == 9
            and all(part["review_status"] == "synthetic_software_fixture"
                    for part in baseline["partitions"].values()) else "fail",
            "selection_status": baseline["status"],
            "positive_selection_required": False,
        },
        "hard_extraction": {"status": "unexecuted"},
        "primary_revalidation": {"status": "unexecuted"},
        "repeats": {"status": "unexecuted"}, "attempts": {"status": "unexecuted"},
        "retrieval": {"status": "unexecuted"}, "recall": {"status": "unexecuted"},
        "efficiency": {"status": "unexecuted"},
        "execution": {"status": "pass"},
    }
    captured, validated = {}, {}
    validator = existing.make_validator(suite, documents, lambda name, row: (
        writer.write(name, row), captured.__setitem__(row["slot_id"], row)
    ))
    driver = None
    # C0 remains a measured negative baseline, not a prerequisite for C1 sends.
    try:
        from llm_inference import CopilotProvider
        verify_cumulative_budget(freeze, require_current=True)
        async with CopilotProvider() as provider:
            driver = await run_requests(
                CapturedProvider(provider, requests, freeze, writer), requests,
                output=writer.root / "calls", ledger_path=ROOT / LEDGER, phase=plan["phase"],
                validate_response=validator, development_slots=frozenset(requests),
                allow_inference=True,
                max_application_attempts=freeze["maximum_application_attempts"],
                max_attempts_per_slot=freeze["maximum_attempts_per_slot"],
            )
        writer.write("driver-observation.json", driver)
        attempts = attempt_assessment(suite, driver, requests)
        writer.write("attempt-assessment.json", attempts)
        checks["attempts"] = attempts["assessment"]
        checks["hard_extraction"] = {
            "status": "fail" if any(row["status"] == "failed"
                                  or row.get("reason") == "application_budget_exhausted"
                                  for row in driver["results"].values())
            else "pass" if len(driver["results"]) == 13
            and all(row["status"] == "success" for row in driver["results"].values())
            and len(captured) == 13 else "unexecuted",
            "slots": {slot: row["status"] for slot, row in driver["results"].items()},
        }
        if checks["hard_extraction"]["status"] == "pass":
            primary_grades = {}
            revalidate = existing.make_validator(suite, documents)
            for slot in freeze["schedule"]:
                if not slot.endswith(".primary"):
                    continue
                sid = slot.rsplit(".", 1)[0]
                # Revalidate original raw proposals, never normalized/expected metadata.
                try:
                    primary_grades[slot] = revalidate(slot, captured[slot]["raw_proposal"])
                except ValueError as error:
                    primary_grades[slot] = {"accepted": False, "error": str(error)}
                    break
                validated[sid] = importlib.import_module("triage_knowledge.source").validate_proposal(
                    documents[sid], captured[slot]["raw_proposal"],
                )
            checks["primary_revalidation"] = {
                "status": "pass" if len(validated) == 9 else "fail",
                "source_count": len(validated),
            }
            writer.write("primary-revalidation.json", primary_grades)
            checks["repeats"] = assess_repeats(
                suite,
                [row["observation"] for slot, row in captured.items() if slot.endswith(".primary")],
                [{"slot_id": slot, "proposal": row["observation"]}
                 for slot, row in captured.items() if ".repeat" in slot],
            )
            if checks["repeats"]["status"] == "pass" and checks["primary_revalidation"]["status"] == "pass":
                verify_freeze(freeze)
                selector = selector_diagnostic(
                    suite, writer, validated, freeze_sha256=canonical_hash(freeze),
                    registry_fixture=registry_fixture,
                )
                writer.write("selector-observation.json", selector)
                checks.update(_query_checks(suite, selector))
    except (InferenceError, OSError, ValueError, KeyError, TypeError) as error:
        failure = {
            "status": "fail", "error_class": getattr(error, "code", type(error).__name__),
            "message": str(error), "receipt": getattr(error, "receipt", None),
        }
        writer.write("execution-failure.json", failure)
        checks["execution"] = failure
    try:
        cumulative = verify_cumulative_budget(freeze, require_current=True)
    except (OSError, ValueError, KeyError, TypeError) as error:
        cumulative = {"status": "fail", "error": str(error)}
    checks["cumulative_budget"] = cumulative
    overall = _status(row["status"] for row in checks.values())
    report = {
        "contract": "knowledge-completion-observation-v3", "profile": PROFILE,
        "freeze_sha256": canonical_hash(freeze), "code_identity": freeze["code_identity"],
        "approved_plan_sha256": canonical_hash(approved_plan),
        "query_registry_fixture": freeze["query_registry_fixture"],
        "checks": checks, "programmatic_status": overall,
        "C0_negative_baseline": {
            "path": "C0baseline\\observation.json", "status": baseline["status"],
            "query_assessments": baseline["query_assessments"],
        },
        "accounting": ledger.observation(), "human_effort": "unexecuted",
        "cumulative_accounting": cumulative,
        "prior_extraction_accounting": freeze["prior_extraction_accounting"],
        "revision_disclosure": REVISION_DISCLOSURE,
        "human_approval_established": False, "review_disclosure": DISCLOSURE,
        "strict_http_accounting": "unexecuted_or_unknown",
        "usd_cost": None, "C1_qualified": False, "system_acceptance": "not_established",
        "integration_strategy": freeze["integration_strategy"],
        "qualification_status": "pending_not_selected",
        "exit_code": 0 if overall == "pass" else 1 if overall == "fail" else 2,
    }
    writer.write("completion.json", report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--freeze", type=Path, help="Earlier reviewed --plan-only JSON, required for inference")
    args = parser.parse_args(argv)
    writer = None
    try:
        if args.plan_only and args.allow_inference:
            raise ValueError("--plan-only and --allow-inference are mutually exclusive")
        if args.plan_only and args.freeze is not None:
            raise ValueError("--freeze supplies an earlier plan to inference, not to --plan-only")
        if args.plan_only:
            _, _, freeze, plan = build_plan(load_suite(), code_identity())
            print(json.dumps(plan_record(freeze, plan), indent=2))
            return 2
        if args.output is None:
            raise ValueError("--output is required except with --plan-only")
        output = (ROOT / args.output).resolve()
        if output == (ROOT / RESULTS).resolve() or not output.is_relative_to((ROOT / RESULTS).resolve()):
            raise ValueError("Output must be a new child under eval\\results\\knowledge\\extraction")
        if not args.allow_inference:
            print(json.dumps({"status": "unexecuted", "dispatch": False, "C1_qualified": False}))
            return 2
        if args.freeze is None:
            raise ValueError("--allow-inference requires an earlier reviewed --freeze plan")
        approved_plan = read_json((ROOT / args.freeze).resolve())
        writer = existing.EvidenceWriter(output)
        report = asyncio.run(run_completion(
            load_suite(), writer, allow_inference=True, approved_plan=approved_plan,
        ))
        print(json.dumps({"programmatic_status": report["programmatic_status"],
                          "C1_qualified": False, "output": str(output)}))
        return report["exit_code"]
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        diagnostic = {"status": "failed", "error": str(error), "C1_qualified": False}
        if writer is not None:
            try:
                writer.write("failure.json", diagnostic)
            except OSError as evidence_error:
                diagnostic["evidence_error"] = str(evidence_error)
        print(json.dumps(diagnostic))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
