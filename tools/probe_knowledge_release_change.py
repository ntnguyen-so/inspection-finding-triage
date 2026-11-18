"""Isolated four-condition experiment for an actual source-first knowledge replacement."""
from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path

from llm_inference import AzureOpenAIProvider, CopilotProvider
from tools.integrate_triage import ROOT, SOURCE, dispatch_summary, hashes, software_release, write_once
from triage.contracts import TriageError, digest, require
from triage.inputs import EQUIPMENT_FIELDS, FINDING_FIELDS, read_inputs
from triage.source_context import IsolatedKnowledgeReleaseContext, activation_candidate
from triage.workflow import RunConfig, run_workflow
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.contracts import canonical_bytes

CONDITIONS = ("positive-before", "positive-after", "negative-before", "negative-after")
CUTOFF = "2026-07-01T00:00:00+00:00"
EFFECTIVE_FROM = "2026-06-30T00:00:00+00:00"
DISCLOSURE = "Evaluation-only knowledge lifecycle experiment; not domain approval."
BEFORE_SOURCE = b"""# PSV low set-pressure scoring
Scope: Pressure Safety Valve

For a functional test showing set-pressure drift 2-3% low while full lift, rated capacity and tight reseat are verified, treat the condition as limited degradation without strong progression: use likelihood 4. For this single-valve compressor-discharge protection scenario, use impact 7 for the consequence if overpressure protection fails. Do not apply this rule to tag, register, certification-date or visual-condition evidence without the functional-test result.
"""
AFTER_SOURCE = b"""# PSV low set-pressure scoring
Scope: Pressure Safety Valve

Updated fleet review establishes that set-pressure drift 2-3% low, even with full lift, rated capacity and tight reseat verified, is a recurrent precursor with strong progression: use likelihood 8. For this single-valve compressor-discharge protection scenario, use impact 7 for the consequence if overpressure protection fails. Do not apply this rule to tag, register, certification-date or visual-condition evidence without the functional-test result.
"""
POSITIVE_FINDING = {
    "finding_id": "F-9002",
    "reported_date": "2026-06-22",
    "equipment_id": "PSV-9002",
    "equipment_type": "Pressure Safety Valve",
    "inspection_type": "Function Test",
    "inspection_method": "Synthetic Bench Test",
    "finding_description": (
        "A controlled test recorded lift at 97.5% of set pressure, 2.5% low. "
        "Full lift and rated capacity were achieved, and the valve reseated tightly. "
        "No prior trend data are available."
    ),
    "reported_by": "Synthetic reporter",
    "reporter_role": "Synthetic fixture role",
}
POSITIVE_EQUIPMENT = {
    "equipment_id": "PSV-9002",
    "equipment_type": "Pressure Safety Valve",
    "service_description": "Synthetic compressor-discharge overpressure protection scenario",
    "criticality_score": "6",
    "reliability_score": "7",
    "safety_critical_element": "Yes",
    "redundancy": "None",
    "engineer_comment": (
        "Evaluation fixture only. The scenario has one relief valve and no credited redundant valve; "
        "the test verified full lift, rated capacity and tight reseat."
    ),
}


def csv_bytes(fields, rows) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def fingerprints() -> dict:
    paths = [Path(__file__), ROOT / "triage" / "source_context.py"]
    return {**hashes(), **{str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}}


def reviewed_activation(store, release: str, reason: str) -> dict:
    activation = activation_candidate(store, release)
    activation["review"] = {
        "reviewer": "SOFTWARE EXPERIMENT ONLY",
        "reason": reason,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "source_policy_compatible": True,
    }
    return activation


def source_item(candidate: dict, source_id: str) -> str:
    matches = [
        item_id for item_id, item in candidate["items"].items()
        if item["revision"]["source_id"] == source_id
    ]
    require(len(matches) == 1, "selection", f"Exactly one item required for {source_id}")
    return matches[0]


def review_pending(store, current: str) -> str:
    candidate, _ = store.load_draft()
    for item_id, item in candidate["items"].items():
        if item["review_state"] == "pending":
            current = store.review_item(
                item_id,
                expected_digest=current,
                reviewer="SOFTWARE EXPERIMENT ONLY",
                reason=DISCLOSURE,
            )
    return current


def prepare(
    target: Path,
    model: str,
    *,
    execution_mode: str = "copilot_experiment",
    reasoning_effort: str | None = None,
    max_completion_tokens: int = 4096,
    timeout_seconds: float = 90,
    azure_api: str = "chat_completions",
) -> dict:
    split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
    probe = json.loads((ROOT / "eval" / "spec" / "probes.json").read_text())["b02"]
    domain = (SOURCE / "reference" / "domain_knowledge.md").read_bytes()
    findings_raw = (SOURCE / "data" / "inspection_findings.csv").read_bytes()
    registry_raw = (SOURCE / "data" / "equipment_registry.csv").read_bytes()
    require(
        digest(domain) == split["sources_sha256"]["reference\\domain_knowledge.md"]
        and digest(findings_raw) == split["sources_sha256"]["data\\inspection_findings.csv"]
        and digest(registry_raw) == split["sources_sha256"]["data\\equipment_registry.csv"],
        "source_integrity",
        "Supplied candidate-pack inputs changed",
    )
    require(
        probe["negative_control_finding"] in split["partitions"]["development"],
        "source_integrity",
        "Negative control must retain development provenance",
    )
    negative = [
        row
        for row in csv.DictReader(io.StringIO(findings_raw.decode("utf-8-sig"), newline=""))
        if row["finding_id"] == probe["negative_control_finding"]
    ]
    require(len(negative) == 1, "selection", "Exactly one unchanged negative control required")
    registry = list(csv.DictReader(io.StringIO(registry_raw.decode("utf-8-sig"), newline="")))
    registry.append(POSITIVE_EQUIPMENT)
    (target / "registry.csv").write_bytes(csv_bytes(EQUIPMENT_FIELDS, registry))
    (target / "positive.csv").write_bytes(
        csv_bytes(FINDING_FIELDS, [POSITIVE_FINDING])
    )
    (target / "negative.csv").write_bytes(csv_bytes(FINDING_FIELDS, negative))
    (target / "before-source.md").write_bytes(BEFORE_SOURCE)
    (target / "after-source.md").write_bytes(AFTER_SOURCE)

    store, _, _ = software_release(target / "knowledge-store", domain)
    _, current = store.load_draft()
    current = store.add_source(
        extract_code(SourceDocument.from_bytes(
            BEFORE_SOURCE,
            name="Evaluation-only prior PSV guidance",
            source_id="psv-policy-before",
        )),
        expected_digest=current,
    )
    before_item = source_item(store.load_draft()[0], "psv-policy-before")
    current = review_pending(store, current)
    before_release = store.publish(
        expected_digest=current,
        author="Knowledge change experiment",
        reviewer="SOFTWARE EXPERIMENT ONLY",
        reason=DISCLOSURE,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    before_activation = reviewed_activation(store, before_release, DISCLOSURE)

    current = store.add_source(
        extract_code(SourceDocument.from_bytes(
            AFTER_SOURCE,
            name="Evaluation-only replacement PSV guidance",
            source_id="psv-policy-after",
        )),
        expected_digest=store.load_draft()[1],
    )
    after_item = source_item(store.load_draft()[0], "psv-policy-after")
    current = store.replace_item(
        before_item,
        after_item,
        effective_from=EFFECTIVE_FROM,
        reason="Simulated approved scoring-policy replacement",
        expected_digest=current,
    )
    current = review_pending(store, current)
    after_release = store.publish(
        expected_digest=current,
        author="Knowledge change experiment",
        reviewer="SOFTWARE EXPERIMENT ONLY",
        reason=DISCLOSURE,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    after_activation = reviewed_activation(store, after_release, DISCLOSURE)
    write_once(target / "before-activation.json", before_activation)
    write_once(target / "after-activation.json", after_activation)

    ledger = target.parent / (
        f"{target.name}.strict-ledger.json"
        if execution_mode == "strict"
        else f"{target.name}.experimental-ledger.json"
    )
    require(not ledger.exists(), "attempt_ledger", "Knowledge-change experiment requires a fresh ledger")
    config = RunConfig(
        model,
        before_release,
        CUTOFF,
        8,
        str(ledger),
        max_context_bytes=128_000,
        execution_mode=execution_mode,
        reasoning_effort=reasoning_effort if execution_mode == "strict" else reasoning_effort or "low",
        minimum_request_interval_seconds=30 if execution_mode == "strict" else 0,
        azure_max_completion_tokens=max_completion_tokens,
        timeout_seconds=timeout_seconds,
        azure_api=azure_api,
    )
    config.validate()

    releases = {"before": before_release, "after": after_release}
    activations = {"before": before_activation, "after": after_activation}
    cases = {}
    for condition in CONDITIONS:
        kind, when = condition.split("-")
        inputs = read_inputs(target / f"{kind}.csv", target / "registry.csv")
        context = IsolatedKnowledgeReleaseContext(store.root, activations[when])
        bundle, _, handoff = context.prepare(
            inputs, releases[when], config.assessment_time, config.max_context_bytes
        )
        write_once(target / f"{condition}.context.json", bundle)
        knowledge = "\n".join(bundle["payload"]["knowledge"].values())
        expected_text = BEFORE_SOURCE.decode().strip() if when == "before" else AFTER_SOURCE.decode().strip()
        require(expected_text in knowledge, "knowledge_change", "Expected PSV revision not delivered")
        require(
            ("likelihood 8" not in knowledge) if when == "before" else ("likelihood 4" not in knowledge),
            "knowledge_change",
            "Superseded PSV revision leaked into provider context",
        )
        cases[condition] = {
            "finding_ids": sorted(inputs.data["findings"]),
            "knowledge_version": releases[when],
            "activation_sha256": digest(canonical_bytes(activations[when])),
            "context_hash": bundle["context_hash"],
            "input_kind": handoff["native_evidence"]["source_manifest"][0]["kind"],
        }

    candidate = store.resolve_release(after_release)["candidate"]
    replacement = next(
        item for item in candidate["replacements"] if item["predecessor_id"] == before_item
    )
    return {
        "contract": "knowledge-release-change-v1",
        "source_directory": str(target),
        "config": asdict(config),
        "cases": cases,
        "releases": releases,
        "items": {"before": before_item, "after": after_item},
        "replacement": replacement,
        "source_sha256": {
            "before": digest(BEFORE_SOURCE),
            "after": digest(AFTER_SOURCE),
        },
        "code_sha256": fingerprints(),
        "artifact_sha256": {
            str(path.relative_to(target)): digest(path.read_bytes())
            for path in target.rglob("*")
            if path.is_file()
        },
        "maximum_sends": 8,
        "nominal_sends": 4,
        "automatic_repeats": False,
        "acceptance_eligible": False,
        "disclosure": DISCLOSURE,
    }


async def execute(plan: dict, target: Path) -> dict:
    source = Path(plan["source_directory"])
    require(
        fingerprints() == plan["code_sha256"]
        and all(
            digest((source / name).read_bytes()) == expected
            for name, expected in plan["artifact_sha256"].items()
        ),
        "freeze_changed",
        "Knowledge-change code or prepared artifacts differ from the frozen plan",
    )
    base_config = dict(plan["config"])
    ledger = Path(base_config["attempt_ledger"])
    require(
        base_config["phase_attempt_budget"] == plan["maximum_sends"] == 8
        and not ledger.exists(),
        "attempt_budget",
        "Fresh eight-send experiment ceiling required",
    )
    outcomes = {}
    for condition in CONDITIONS:
        kind, when = condition.split("-")
        inputs = read_inputs(source / f"{kind}.csv", source / "registry.csv")
        activation = json.loads((source / f"{when}-activation.json").read_text())
        config = RunConfig(**{**base_config, "knowledge_version": plan["releases"][when]})
        context = IsolatedKnowledgeReleaseContext(source / "knowledge-store", activation)
        try:
            receipt = await run_workflow(
                inputs,
                context,
                (
                    lambda: AzureOpenAIProvider(
                        native_json_schema=True,
                        max_completion_tokens=config.azure_max_completion_tokens,
                        api=config.azure_api,
                    )
                )
                if config.execution_mode == "strict"
                else CopilotProvider,
                config,
                target / f"{condition}.experimental.json",
                target / condition,
                purpose="isolated_probe",
            )
            outcomes[condition] = {"status": "draft_generated", "receipt": receipt}
        except TriageError as error:
            outcomes[condition] = {"status": "failed", "error_class": error.code}
        write_once(target / f"{condition}.observation.json", outcomes[condition])

    scores = {}
    for condition in CONDITIONS:
        path = target / f"{condition}.experimental.json"
        ticket = json.loads(path.read_text())["tickets"][0] if path.exists() else None
        scores[condition] = {
            "likelihood": ticket["likelihood_of_failure"]["score"] if ticket else None,
            "impact": ticket["impact_of_failure"]["score"] if ticket else None,
            "urgency": ticket["urgency"]["score"] if ticket else None,
            "review_required": ticket["review_required"] if ticket else None,
        }
        outcomes[condition]["observed"] = scores[condition]
    positive_response = (
        scores["positive-before"]["likelihood"] == 4
        and scores["positive-before"]["impact"] == 7
        and scores["positive-after"]["likelihood"] == 8
        and scores["positive-after"]["impact"] == 7
    )
    negative_stable = scores["negative-before"] == scores["negative-after"]
    negative_excludes_rule_scores = all(
        scores[condition]["likelihood"] not in {4, 8}
        for condition in ("negative-before", "negative-after")
    )
    completed = all(item["status"] == "draft_generated" for item in outcomes.values())
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        "premium_requests": 0,
        "elapsed_seconds": 0.0,
    }
    for condition in CONDITIONS:
        run_path = target / condition / "run.json"
        if not run_path.exists():
            continue
        run = json.loads(run_path.read_text())
        usage["elapsed_seconds"] += run.get("elapsed_seconds", 0)
        for send in run.get("application_sends", []):
            for item in (send.get("receipt") or {}).get("usage", []):
                usage["input_tokens"] += item.get("inputTokens", 0)
                usage["output_tokens"] += item.get("outputTokens", 0)
                usage["cache_read_tokens"] += item.get("cacheReadTokens", 0)
                usage["cache_write_tokens"] += item.get("cacheWriteTokens", 0)
                usage["reasoning_tokens"] += item.get("reasoningTokens", 0)
                usage["premium_requests"] += item.get("cost", 0)
    usage["illustrative_openai_usd"] = round(
        usage["input_tokens"] * 2 / 1_000_000
        + usage["output_tokens"] * 10 / 1_000_000,
        4,
    )
    report = {
        "status": (
            "four_conditions_completed_review_pending"
            if completed and positive_response
            else "failed_or_inconclusive"
        ),
        "positive_release_response_observed": positive_response,
        "negative_control_decision_stable": negative_stable,
        "negative_likelihood_excludes_rule_scores": negative_excludes_rule_scores,
        "conditions": outcomes,
        "semantic_specificity_status": "pending_calibrated_review",
        "code_stable_during_run": fingerprints() == plan["code_sha256"],
        "phase_reservations": (
            len(json.loads(ledger.read_text())["reservations"]) if ledger.exists() else 0
        ),
        "acceptance_eligible": False,
        "http_attempts": None,
        "usd_cost": None,
        "observed_usage": usage,
        "cost_note": (
            "Actual Copilot USD allocation unknown; equivalent uses observed input/output tokens "
            "at assumed OpenAI rates of US$2/M input and US$10/M output without cache discount."
        ),
    }
    if not report["code_stable_during_run"]:
        report["status"] = "failed_or_inconclusive"
    if base_config["execution_mode"] == "strict":
        attempts = []
        for condition in CONDITIONS:
            path = target / condition / "run.json"
            if path.exists():
                attempts.extend(json.loads(path.read_text()).get("attempts", []))
        report.update(dispatch_summary(attempts, report["phase_reservations"]))
    write_once(target / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model")
    parser.add_argument("--provider", choices=("copilot", "azure"))
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--azure-max-completion-tokens", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--azure-api", choices=("chat_completions", "responses"), default="chat_completions")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--allow-inference", action="store_true")
    args = parser.parse_args(argv)
    require(bool(args.model) != bool(args.plan), "configuration", "Prepare a model or execute a plan")
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=False)
    if args.model:
        require(not args.allow_inference, "configuration", "Preparation never dispatches")
        plan = prepare(
            target,
            args.model,
            execution_mode="strict" if args.provider == "azure" else "copilot_experiment",
            reasoning_effort=args.reasoning_effort,
            max_completion_tokens=args.azure_max_completion_tokens,
            timeout_seconds=args.timeout_seconds,
            azure_api=args.azure_api,
        )
        write_once(target / "plan.json", plan)
        print(json.dumps({"status": "prepared_not_executed", "maximum_sends": 8}))
        return 0
    require(args.allow_inference, "configuration", "Explicit inference authorization required")
    plan = json.loads(args.plan.read_text())
    require(
        args.provider is None
        or args.provider
        == ("azure" if plan["config"]["execution_mode"] == "strict" else "copilot"),
        "configuration",
        "Explicit provider differs from frozen plan",
    )
    write_once(args.plan.parent / "execution-reserved.json", {"output": str(target)})
    write_once(target / "plan.json", plan)
    report = asyncio.run(execute(plan, target))
    print(json.dumps(report))
    return 0 if report["status"] == "four_conditions_completed_review_pending" else 1


if __name__ == "__main__":
    raise SystemExit(main())
