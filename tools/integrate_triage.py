"""Bounded native development E2E; isolated fixture approval is never production approval."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import time

from llm_inference.contracts import strict_json
from triage import NativeContext, activation_candidate
from triage.contracts import TriageError, digest, require
from triage.inputs import FINDING_FIELDS, read_inputs
from triage.workflow import RunConfig, checked_copilot_receipt, checked_receipt, save_json, validate_output
from triage_knowledge import KnowledgeError, SourceDocument, SourceKnowledgeStore, extract_code

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "candidate-pack" / "candidate-pack"
PHASE_BUDGET = 52
DEFAULT_COPILOT_MODEL = "gpt-5.6-sol-fast"
DISCLOSURE = (
    "Isolated SOFTWARE-fixture publication/activation of unchanged supplied domain; "
    "not genuine engineer approval, qualified extraction or system acceptance. "
    "Provider accounting is reported separately."
)


def hashes() -> dict:
    paths = [Path(__file__), ROOT / "pyproject.toml",
             ROOT / "eval" / "spec" / "split.json", ROOT / "eval" / "spec" / "acceptance.json"]
    for package in ("triage", "triage_knowledge", "llm_inference"):
        paths.extend(sorted(path for path in (ROOT / package).rglob("*.py")
                            if "__pycache__" not in path.parts))
    return {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}


def write_once(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write("\n")


def dispatch_summary(attempts: list[dict], reservations: int) -> dict:
    receipts = [item.get("receipt") or {} for item in attempts]
    counts = [item.get("http_dispatches_observed") for item in receipts]
    known = sum(count for count in counts if type(count) is int and count >= 0)
    missing = sum(type(count) is not int or count < 0 for count in counts)
    models = sorted({item["observed_model"] for item in receipts
                     if isinstance(item.get("observed_model"), str) and item["observed_model"]})
    return {
        "known_http_dispatches": known, "attempts_without_receipt": missing,
        "unrecorded_reservations": max(0, reservations - len(attempts)),
        "reservation_records_match": reservations == len(attempts),
        "http_attempts": known if missing == 0 and reservations == len(attempts) else None,
        "observed_models": models, "model_tag_consistent": len(models) == 1,
    }


def software_release(path: Path, domain: bytes) -> tuple[SourceKnowledgeStore, str, dict]:
    store = SourceKnowledgeStore(path)
    current = store.create_draft([extract_code(SourceDocument.from_bytes(
        domain, name="Unchanged supplied domain - isolated software fixture", source_id="domain"))])
    candidate, _ = store.load_draft()
    for item_id in candidate["items"]:
        current = store.review_item(item_id, expected_digest=current,
                                    reviewer="SOFTWARE TEST ONLY", reason=DISCLOSURE)
    now = datetime.now(timezone.utc).isoformat()
    release = store.publish(expected_digest=current, author="Integration software fixture",
                            reviewer="SOFTWARE TEST ONLY", reason=DISCLOSURE, reviewed_at=now)
    activation = activation_candidate(store, release)
    activation["review"] = {"reviewer": "SOFTWARE TEST ONLY", "reason": DISCLOSURE,
                            "reviewed_at": now, "source_policy_compatible": True}
    return store, release, activation


def prepare(target: Path, model: str, *, continuation: dict | None = None,
            execution_mode: str = "copilot_experiment", reasoning_effort: str | None = None,
            max_completion_tokens: int = 4096, timeout_seconds: float = 90,
            azure_api: str = "chat_completions",
            minimum_request_interval_seconds: float | None = None) -> dict:
    require(execution_mode in {"strict", "copilot_experiment"}, "configuration", "Explicit provider mode required")
    split = strict_json((ROOT / "eval" / "spec" / "split.json").read_text())
    domain = (SOURCE / "reference" / "domain_knowledge.md").read_bytes()
    require(digest(domain) == split["sources_sha256"]["reference\\domain_knowledge.md"],
            "source_integrity", "Supplied domain differs from frozen input")
    raw = (SOURCE / "data" / "inspection_findings.csv").read_bytes()
    registry = (SOURCE / "data" / "equipment_registry.csv").read_bytes()
    require(digest(raw) == split["sources_sha256"]["data\\inspection_findings.csv"]
            and digest(registry) == split["sources_sha256"]["data\\equipment_registry.csv"],
            "source_integrity", "Supplied CSV bytes differ from frozen inputs")
    rows = [row for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
            if row["finding_id"] in split["partitions"]["development"]]
    require({row["finding_id"] for row in rows} == set(split["partitions"]["development"]),
            "selection", "Development selection incomplete")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FINDING_FIELDS)
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda row: row["finding_id"]))
    (target / "selected.csv").write_bytes(stream.getvalue().encode())
    (target / "registry.csv").write_bytes(registry)
    ledger = target.parent / ("native-strict-development-ledger.json" if execution_mode == "strict"
                              else "native-e2e.experimental-ledger.json")
    if ledger.exists():
        require(isinstance(continuation, dict)
                and set(continuation) == {
                    "reason", "prior_plan_path", "prior_plan_sha256",
                    "prior_ledger_sha256", "prior_reserved_sends",
                }
                and isinstance(continuation["reason"], str) and continuation["reason"].strip()
                and isinstance(continuation["prior_plan_sha256"], str)
                and len(continuation["prior_plan_sha256"]) == 64
                and type(continuation["prior_reserved_sends"]) is int,
                "attempt_ledger", "Continuing a spent phase requires explicit lineage and its unchanged ceiling")
        prior = strict_json(ledger.read_text())
        previous = Path(continuation["prior_plan_path"])
        require(digest(previous.read_bytes()) == continuation["prior_plan_sha256"]
                and digest(ledger.read_bytes()) == continuation["prior_ledger_sha256"]
                and Path(strict_json(previous.read_text())["config"]["attempt_ledger"]).resolve() == ledger
                and prior["budget"] == PHASE_BUDGET
                and prior.get("execution_mode", "strict") == execution_mode
                and len(prior["reservations"]) == continuation["prior_reserved_sends"] < PHASE_BUDGET,
                "attempt_ledger", "Continuing a spent phase requires explicit lineage and its unchanged ceiling")
    else:
        require(continuation is None, "attempt_ledger", "A continuation must retain its existing ledger")
    store, release, activation = software_release(target / "software-store", domain)
    write_once(target / "activation.json", activation)
    config = RunConfig(
        model=model, knowledge_version=release, assessment_time="2026-07-01T00:00:00+00:00",
        phase_attempt_budget=PHASE_BUDGET, attempt_ledger=str(ledger),
        max_context_bytes=128_000, timeout_seconds=timeout_seconds,
        reasoning_effort=reasoning_effort if execution_mode == "strict" else reasoning_effort or "low",
        execution_mode=execution_mode,
        minimum_request_interval_seconds=(
            30 if execution_mode == "strict" else 0
        ) if minimum_request_interval_seconds is None else minimum_request_interval_seconds,
        azure_max_completion_tokens=max_completion_tokens, azure_api=azure_api)
    config.validate()
    write_once(target / "config.json", asdict(config))
    bundle, encoded, _ = NativeContext(store.root, activation).prepare(
        read_inputs(target / "selected.csv", target / "registry.csv"), release,
        config.assessment_time, config.max_context_bytes)
    return {
        "contract": "native-triage-development-e2e-v1", "disclosure": DISCLOSURE,
        "source_directory": str(target), "finding_ids": sorted(split["partitions"]["development"]),
        "model": model, "config": asdict(config),
        "artifact_sha256": {name: digest((target / name).read_bytes())
                           for name in ("selected.csv", "registry.csv", "activation.json", "config.json")},
        "source_sha256": hashes(), "observations": ["development", "one_fixed_configuration_repeat"],
        "planned_context_hash": bundle["context_hash"], "planned_context_bytes": len(encoded.encode()),
        "nominal_sends_per_observation": len(rows), "maximum_sends_per_finding": 2,
        "phase_send_ceiling": PHASE_BUDGET, "http_attempts": None, "usd_ceiling": None,
        "cost_limit": (f"52 retry-free HTTP dispatches, {max_completion_tokens} completion tokens per dispatch; USD measured separately."
                       if execution_mode == "strict" else "Application-send ceiling only; Copilot HTTP/USD controls unavailable."),
        "human_content_approval": False, "acceptance_eligible": False,
        "continuation": continuation,
    }


def validate_plan(plan: dict) -> Path:
    require(plan["contract"] == "native-triage-development-e2e-v1"
            and plan["source_sha256"] == hashes() and plan["phase_send_ceiling"] == PHASE_BUDGET,
            "freeze_changed", "Native E2E code/configuration changed; never silently refresh pins")
    source = Path(plan["source_directory"])
    require(all(digest((source / name).read_bytes()) == expected
                for name, expected in plan["artifact_sha256"].items()),
            "freeze_changed", "Native E2E selected inputs or activation changed")
    config = strict_json((source / "config.json").read_text())
    require(config == plan["config"] and config["phase_attempt_budget"] == PHASE_BUDGET
            and Path(config["attempt_ledger"]).resolve() ==
            source.parent / ("native-strict-development-ledger.json" if config["execution_mode"] == "strict"
                             else "native-e2e.experimental-ledger.json"),
            "freeze_changed", "Phase ledger or configuration differs from the declared plan")
    return source


def execute(plan: dict, target: Path) -> dict:
    source = validate_plan(plan)
    output = target / "tickets.experimental.json"
    strict = plan["config"]["execution_mode"] == "strict"
    ledger = Path(plan["config"]["attempt_ledger"])
    starting_reservations = len(strict_json(ledger.read_text())["reservations"]) if ledger.exists() else 0
    command = [
        sys.executable, "-B", "-m", "triage", "--provider", "azure" if strict else "copilot",
        "--findings", str(source / "selected.csv"), "--registry", str(source / "registry.csv"),
        "--knowledge-store", str(source / "software-store"),
        "--activation", str(source / "activation.json"), "--config", str(source / "config.json"),
        "--output", str(output), "--evidence", str(target / "run"), "--allow-inference",
    ]
    write_once(target / "execution.json", {
        "command": command, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": subprocess.run(["git", "--no-pager", "rev-parse", "HEAD"], cwd=ROOT,
                                       capture_output=True, text=True, check=True).stdout.strip(),
        "dirty_worktree": subprocess.run(["git", "--no-pager", "status", "--short"], cwd=ROOT,
                                         capture_output=True, text=True, check=True).stdout,
        "disclosure": DISCLOSURE,
        "phase_reservations_before_dispatch": starting_reservations,
    })
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    (target / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (target / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    report = {
        "status": "experimental_e2e_failed",
        "cli_exit_code": completed.returncode, "output_contract_valid": False,
        "actual_native_context_delivery": False, "code_stable_during_run": None,
        "application_sends": None, "phase_send_ceiling": PHASE_BUDGET,
        "http_attempts": None, "usd_cost": None, "semantic_status": "not_reviewed",
        "output_sha256": digest(output.read_bytes()) if output.exists() else None,
        "elapsed_seconds": time.monotonic() - started, "acceptance_eligible": False,
        "disclosure": DISCLOSURE,
    }
    try:
        record_path = target / "run" / "run.json"
        record = strict_json(record_path.read_text()) if record_path.exists() else {}
        sends = record.get("attempts" if strict else "application_sends", [])
        report["application_sends"] = len(sends)
        report["phase_application_send_reservations"] = (
            len(strict_json(ledger.read_text())["reservations"]) if ledger.exists() else 0)
        if strict:
            report.update(dispatch_summary(
                sends, report["phase_application_send_reservations"] - starting_reservations))
        inputs = read_inputs(source / "selected.csv", source / "registry.csv")
        for send in sends:
            system, user = send["provider_input"]["system"], send["provider_input"]["user"]
            context = strict_json(user)["context"]
            require(context["contract_version"] == 3 and context["finding_ids"] == plan["finding_ids"]
                    and context["context_hash"] == plan["planned_context_hash"]
                    and context["payload"]["findings"] == inputs.data["findings"]
                    and context["payload"]["registry"] == inputs.data["registry"],
                    "context_isolation", "Captured request differs from authorized rows or planned context")
            if send.get("receipt"):
                if strict:
                    checked_receipt(send["receipt"])
                    require(send["receipt"].get("wire_message_hashes_match") is True
                            and send["receipt"].get("system_sha256") == digest(system.encode())
                            and send["receipt"].get("user_sha256") == digest(user.encode()),
                            "context_isolation", "Direct-provider wire messages differ from captured inputs")
                else:
                    checked_copilot_receipt(send["receipt"], plan["model"], system, user)
        report["actual_native_context_delivery"] = bool(sends) and all(
            send.get("receipt", {}).get("http_dispatches_observed" if strict else "inference_calls_observed") == 1
            for send in sends)
        report["code_stable_during_run"] = hashes() == plan["source_sha256"]
        if completed.returncode == 0:
            validate_output(strict_json(output.read_text()), inputs.data["findings"])
            receipt = strict_json(completed.stdout)
            require(receipt["output_sha256"] == digest(output.read_bytes()), "publication_hash",
                    "Publication receipt differs from persisted tickets")
            report["output_contract_valid"] = True
        if all(report[name] is True for name in (
                "output_contract_valid", "actual_native_context_delivery", "code_stable_during_run")):
            report["status"] = "experimental_e2e_pass"
    except (TriageError, OSError, ValueError, TypeError, KeyError) as error:
        report.update(verification_error_class=getattr(error, "code", type(error).__name__),
                      verification_error=str(error))
    write_once(target / "observation.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New observation directory")
    parser.add_argument(
        "--model",
        help=f"Provider model/deployment; Copilot defaults to {DEFAULT_COPILOT_MODEL}",
    )
    parser.add_argument("--provider", choices=("copilot", "azure"))
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--azure-max-completion-tokens", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--minimum-request-interval-seconds", type=float)
    parser.add_argument("--azure-api", choices=("chat_completions", "responses"), default="chat_completions")
    parser.add_argument("--plan", type=Path, help="Execute a previously prepared immutable plan")
    parser.add_argument("--repeat-from", type=Path, help="One fixed-config repeat of a successful run")
    parser.add_argument("--allow-inference", action="store_true")
    args = parser.parse_args(argv)
    target = args.output.resolve()
    created = False
    try:
        preparation_model = args.model
        if args.plan is None and args.repeat_from is None and args.provider != "azure":
            preparation_model = preparation_model or DEFAULT_COPILOT_MODEL
        require(not (args.plan and args.repeat_from), "configuration", "Choose plan or repeat, not both")
        require((args.plan is not None or args.repeat_from is not None) != bool(preparation_model),
                "configuration", "Choose explicit model preparation or an existing plan")
        target.mkdir(parents=True, exist_ok=False)
        created = True
        if args.plan or args.repeat_from:
            require(args.allow_inference, "inference_not_authorized", "Execution needs --allow-inference")
            origin = args.repeat_from.resolve() if args.repeat_from else args.plan.parent.resolve()
            plan = strict_json((origin / "plan.json").read_text())
            source = validate_plan(plan)
            require(args.provider is None or args.provider == (
                "azure" if plan["config"]["execution_mode"] == "strict" else "copilot"),
                "configuration", "Explicit provider differs from frozen plan")
            if args.repeat_from:
                require(strict_json((origin / "observation.json").read_text())["status"] ==
                        "experimental_e2e_pass", "repeat_contract", "Repeat requires a successful first run")
                marker = source / "repeat-reserved.json"
            else:
                require(args.plan.resolve() == source / "plan.json", "freeze_changed", "Use original plan")
                marker = source / "development-reserved.json"
            write_once(marker, {"output": str(target), "reserved_at": datetime.now(timezone.utc).isoformat()})
            write_once(target / "plan.json", plan)
            report = execute(plan, target)
            print(json.dumps(report))
            return 0 if report["status"] == "experimental_e2e_pass" else 1
        require(not args.allow_inference, "configuration", "Prepare first, then execute the frozen plan")
        plan = prepare(target, preparation_model,
                       execution_mode="strict" if args.provider == "azure" else "copilot_experiment",
                       reasoning_effort=args.reasoning_effort,
                       max_completion_tokens=args.azure_max_completion_tokens,
                       timeout_seconds=args.timeout_seconds, azure_api=args.azure_api,
                       minimum_request_interval_seconds=args.minimum_request_interval_seconds)
        write_once(target / "plan.json", plan)
        print(json.dumps({"status": "prepared_not_executed", "plan": str(target / "plan.json"),
                          "phase_send_ceiling": PHASE_BUDGET, "disclosure": DISCLOSURE}))
        return 0
    except (TriageError, KnowledgeError, OSError, ValueError, TypeError, KeyError) as error:
        diagnostic = {"status": "failed", "error_class": getattr(error, "code", type(error).__name__),
                      "message": str(error), "acceptance_eligible": False}
        if created and not (target / "observation.json").exists():
            save_json(target / "observation.json", diagnostic)
        print(json.dumps(diagnostic), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
