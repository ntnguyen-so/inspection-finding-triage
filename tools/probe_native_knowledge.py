"""Native, explicitly isolated four-condition B02 experiment; never shipping knowledge."""
from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import asdict
import io
import json
from pathlib import Path

from llm_inference import AzureOpenAIProvider, CopilotProvider
from tools.integrate_triage import ROOT, SOURCE, dispatch_summary, hashes, software_release, write_once
from triage.assessment_policy import assessment_policy
from triage.contracts import TriageError, digest, require
from triage.inputs import EQUIPMENT_FIELDS, FINDING_FIELDS, read_inputs
from triage.source_context import IsolatedProbeContext
from triage.workflow import RunConfig, run_workflow
from triage_knowledge.contracts import canonical_bytes

CONDITIONS = ("positive-before", "positive-after", "negative-before", "negative-after")


def csv_bytes(fields, rows) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def fingerprints() -> dict:
    paths = [Path(__file__), ROOT / "eval" / "spec" / "probes.json"]
    return {**hashes(), **{str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}}


def experiment_for(inputs, probe: dict, when: str) -> dict:
    policy = assessment_policy()
    policy["isolated_experiment"] = {
        "experiment_id": "B02-PSV-maintenance",
        "scope": "Testing-only artificial policy diagnostic, not engineering calibration.",
        "policy_version": probe["policies"][when]["version"],
        "rule_id": probe["policies"][when]["rule_id"], "text": probe["policies"][when]["text"],
    }
    return {
        "contract": "triage-isolated-probe-v1", "experiment_id": "B02-PSV-maintenance",
        "input_kind": "evaluation_input", "findings_sha256": inputs.findings_hash,
        "registry_sha256": inputs.registry_hash, "assessment_policy": policy,
        "assessment_policy_sha256": digest(canonical_bytes(policy)),
    }


def prepare(target: Path, model: str, *, execution_mode: str = "copilot_experiment",
            reasoning_effort: str | None = None, max_completion_tokens: int = 4096,
            timeout_seconds: float = 90, azure_api: str = "chat_completions") -> dict:
    split = json.loads((ROOT / "eval" / "spec" / "split.json").read_text())
    probe = json.loads((ROOT / "eval" / "spec" / "probes.json").read_text())["b02"]
    domain = (SOURCE / "reference" / "domain_knowledge.md").read_bytes()
    require(digest(domain) == split["sources_sha256"]["reference\\domain_knowledge.md"],
            "source_integrity", "Original domain bytes changed")
    raw = (SOURCE / "data" / "inspection_findings.csv").read_bytes()
    registry = (SOURCE / "data" / "equipment_registry.csv").read_bytes()
    require(digest(raw) == split["sources_sha256"]["data\\inspection_findings.csv"]
            and digest(registry) == split["sources_sha256"]["data\\equipment_registry.csv"]
            and probe["negative_control_finding"] in split["partitions"]["development"],
            "source_integrity", "Probe control must retain original development provenance")
    negative = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
                if row["finding_id"] == probe["negative_control_finding"]]
    require(len(negative) == 1, "selection", "Exactly one unchanged negative control required")
    rows = list(csv.DictReader(io.StringIO(registry.decode("utf-8-sig"), newline="")))
    rows.append(probe["positive_input"]["equipment"])
    (target / "registry.csv").write_bytes(csv_bytes(EQUIPMENT_FIELDS, rows))
    (target / "positive.csv").write_bytes(csv_bytes(FINDING_FIELDS, [probe["positive_input"]["finding"]]))
    (target / "negative.csv").write_bytes(csv_bytes(FINDING_FIELDS, negative))
    store, version, activation = software_release(target / "software-store", domain)
    write_once(target / "activation.json", activation)
    ledger = target.parent / ("native-b02-strict-ledger.json" if execution_mode == "strict"
                              else "native-b02.experimental-ledger.json")
    require(not ledger.exists() and ledger.name != "native-e2e.experimental-ledger.json",
            "attempt_ledger", "B02 requires its own unused eight-send phase; never reset old ledgers")
    config = RunConfig(model, version, "2026-07-01T00:00:00+00:00", 8, str(ledger),
                       max_context_bytes=128_000, execution_mode=execution_mode,
                       reasoning_effort=reasoning_effort if execution_mode == "strict" else reasoning_effort or "low",
                       minimum_request_interval_seconds=30 if execution_mode == "strict" else 0,
                       azure_max_completion_tokens=max_completion_tokens, timeout_seconds=timeout_seconds,
                       azure_api=azure_api)
    config.validate()
    cases = {}
    for condition in CONDITIONS:
        kind, when = condition.split("-")
        inputs = read_inputs(target / f"{kind}.csv", target / "registry.csv")
        experiment = experiment_for(inputs, probe, when)
        source = IsolatedProbeContext(store.root, activation, experiment)
        bundle, _, _ = source.prepare(inputs, version, config.assessment_time, config.max_context_bytes)
        write_once(target / f"{condition}.experiment.json", experiment)
        write_once(target / f"{condition}.context.json", bundle)
        cases[condition] = {"finding_ids": sorted(inputs.data["findings"]),
                            "context_hash": bundle["context_hash"],
                            "overlay_sha256": digest(probe["policies"][when]["text"].encode())}
    for kind in ("positive", "negative"):
        packets = [json.loads((target / f"{kind}-{when}.context.json").read_text())
                   for when in ("before", "after")]
        require({k: v for k, v in packets[0].items() if k not in {"assessment_policy", "context_hash"}} ==
                {k: v for k, v in packets[1].items() if k not in {"assessment_policy", "context_hash"}},
                "probe_isolation", "Before/after may differ only in declared policy and derived context hash")
    return {
        "contract": "native-b02-v1", "source_directory": str(target), "config": asdict(config),
        "cases": cases, "code_sha256": fingerprints(),
        "artifact_sha256": {str(p.relative_to(target)): digest(p.read_bytes())
                           for p in target.rglob("*") if p.is_file()},
        "maximum_sends": 8, "nominal_sends": 4, "automatic_repeats": False,
        "acceptance_eligible": False, "http_attempts": None, "usd_cost": None,
        "disclosure": "Software-only fixture publication, isolated evaluation_input and artificial policy; not real KB approval.",
    }


async def execute(plan: dict, target: Path) -> dict:
    source = Path(plan["source_directory"])
    require(fingerprints() == plan["code_sha256"]
            and all(digest((source / name).read_bytes()) == expected
                    for name, expected in plan["artifact_sha256"].items()),
            "freeze_changed", "B02 code/inputs/policies differ from the prepared freeze")
    config = RunConfig(**plan["config"])
    config.validate()
    require(config.phase_attempt_budget == plan["maximum_sends"] == 8
            and Path(config.attempt_ledger).resolve() == source.parent / (
                "native-b02-strict-ledger.json" if config.execution_mode == "strict"
                else "native-b02.experimental-ledger.json"),
            "attempt_budget", "Frozen B02 eight-send ceiling required")
    activation = json.loads((source / "activation.json").read_text())
    probe = json.loads((ROOT / "eval" / "spec" / "probes.json").read_text())["b02"]
    outcomes = {}
    for condition in CONDITIONS:
        inputs = read_inputs(source / f"{condition.split('-')[0]}.csv", source / "registry.csv")
        experiment = json.loads((source / f"{condition}.experiment.json").read_text())
        require(experiment == experiment_for(inputs, probe, condition.split("-")[1]),
                "probe_isolation", "Probe policy must equal the exact frozen convention, not merely self-hash")
        context = IsolatedProbeContext(source / "software-store", activation, experiment)
        try:
            receipt = await run_workflow(
                inputs, context, (lambda: AzureOpenAIProvider(
                    native_json_schema=True, max_completion_tokens=config.azure_max_completion_tokens,
                    api=config.azure_api))
                if config.execution_mode == "strict" else CopilotProvider, config,
                target / f"{condition}.experimental.json", target / condition,
                purpose="isolated_probe")
            outcomes[condition] = {"status": "draft_generated", "receipt": receipt}
        except TriageError as error:
            outcomes[condition] = {"status": "failed", "error_class": error.code}
        write_once(target / f"{condition}.observation.json", outcomes[condition])
    positives = True
    for when in ("before", "after"):
        path = target / f"positive-{when}.experimental.json"
        observed = json.loads(path.read_text())["tickets"][0]["likelihood_of_failure"]["score"] if path.exists() else None
        outcomes[f"positive-{when}"]["observed_likelihood"] = observed
        positives &= observed == probe["expected"][f"positive_{when}_likelihood"]
    report = {
        "status": "four_conditions_completed_review_pending" if positives and all(
            item["status"] == "draft_generated" for item in outcomes.values()) else "failed_or_inconclusive",
        "positive_policy_response_observed": positives, "conditions": outcomes,
        "negative_semantic_status": "pending_calibrated_review",
        "code_stable_during_run": fingerprints() == plan["code_sha256"],
        "phase_reservations": len(json.loads(Path(config.attempt_ledger).read_text())["reservations"])
        if Path(config.attempt_ledger).exists() else 0,
        "acceptance_eligible": False, "http_attempts": None, "usd_cost": None,
    }
    if not report["code_stable_during_run"]:
        report["status"] = "failed_or_inconclusive"
    if config.execution_mode == "strict":
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
    require(bool(args.model) != bool(args.plan), "configuration", "Prepare a model or execute an existing plan")
    target = args.output.resolve()
    target.mkdir(parents=True, exist_ok=False)
    if args.model:
        require(not args.allow_inference, "configuration", "Preparation never dispatches")
        plan = prepare(target, args.model, execution_mode="strict" if args.provider == "azure" else "copilot_experiment",
                       reasoning_effort=args.reasoning_effort,
                       max_completion_tokens=args.azure_max_completion_tokens,
                       timeout_seconds=args.timeout_seconds, azure_api=args.azure_api)
        write_once(target / "plan.json", plan)
        print(json.dumps({"status": "prepared_not_executed", "maximum_sends": 8}))
        return 0
    require(args.allow_inference, "configuration", "Explicit inference authorization required")
    plan = json.loads(args.plan.read_text())
    require(args.provider is None or args.provider == (
        "azure" if plan["config"]["execution_mode"] == "strict" else "copilot"),
        "configuration", "Explicit provider differs from frozen plan")
    write_once(args.plan.parent / "execution-reserved.json", {"output": str(target)})
    write_once(target / "plan.json", plan)
    report = asyncio.run(execute(plan, target))
    print(json.dumps(report))
    return 0 if report["status"] == "four_conditions_completed_review_pending" else 1


if __name__ == "__main__":
    raise SystemExit(main())
