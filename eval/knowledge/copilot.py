"""Bounded experimental sends through llm_inference, never a production reviewer."""
from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Callable

from llm_inference import InferenceError, InferenceProvider, InferenceRequest

from .attempts import AttemptLedger, encoded, fingerprint

RECOVERABLE = frozenset({"timeout", "transport", "malformed_json", "schema_violation"})


def request_record(request: InferenceRequest) -> dict:
    system, user, _ = request.prepared()
    return {"configuration": asdict(request), "prepared_system": system,
            "prepared_user": user}


def _write_once(path: Path, value: dict) -> None:
    raw = encoded(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


async def run_requests(
    provider: InferenceProvider, requests: dict[str, InferenceRequest], *,
    output: Path, ledger_path: Path, phase: str,
    validate_response: Callable[[str, object], dict],
    development_slots: frozenset[str], allow_inference: bool = False,
    max_application_attempts: int = 26, max_attempts_per_slot: int = 2,
) -> dict:
    if not allow_inference:
        raise ValueError("Explicit inference authorization is required")
    if not requests or not development_slots <= requests.keys():
        raise ValueError("Invalid frozen request schedule")
    if (type(max_application_attempts) is not int or not 1 <= max_application_attempts <= 26
            or type(max_attempts_per_slot) is not int or not 1 <= max_attempts_per_slot <= 2):
        raise ValueError("Application/per-slot ceilings must be integers in 1..26 and 1..2")
    profiles = {(r.model, r.system, fingerprint(r.response_schema),
                 r.reasoning_effort, r.timeout_seconds) for r in requests.values()}
    if len(profiles) != 1:
        raise ValueError("All extraction slots must share the frozen profile")
    records = {slot: request_record(request) for slot, request in requests.items()}
    plan = {"phase": phase, "slots": {slot: fingerprint(record)
                                    for slot, record in records.items()},
            "maximum_attempts": max_application_attempts, "per_slot_attempts": max_attempts_per_slot,
            "schedule": list(requests), "development_slots": sorted(development_slots),
            "recoverable_codes": sorted(RECOVERABLE)}
    ledger = AttemptLedger(ledger_path, plan)
    output.mkdir(parents=True, exist_ok=True)
    # Existing observations are immutable; resuming requires explicit adjudication.
    if any(output.glob("attempt-*.json")):
        raise ValueError("Observation directory already contains attempts")
    _write_once(output / "request-plan.json", {
        "phase": phase, "plan_sha256": ledger.binding,
        "requests": records, "schedule": list(requests),
        "recoverable_codes": sorted(RECOVERABLE),
        "development_slots": sorted(development_slots),
    })
    results: dict[str, dict] = {}
    stopped = False
    stop_reason = "development_gate_failed"
    for slot, request in requests.items():
        if stopped:
            results[slot] = {"status": "unexecuted", "reason": stop_reason}
            continue
        for _ in range(max_attempts_per_slot):
            if ledger.observation()["application_attempts_reserved"] >= max_application_attempts:
                results.setdefault(slot, {"status": "unexecuted", "reason": "application_budget_exhausted"})
                stopped, stop_reason = True, "application_budget_exhausted"
                break
            number = ledger.reserve(slot, plan["slots"][slot])
            attempt = {"slot": slot, "number": number,
                       "request_sha256": plan["slots"][slot]}
            try:
                response = await provider.generate(request)
            except InferenceError as error:
                outcome = {"status": "failed", "error_class": error.code,
                           "receipt": error.receipt}
                if error.code in {"malformed_json", "schema_violation"}:
                    outcome["raw_invalid_output"] = "unavailable_from_adapter"
                _write_once(output / f"attempt-{number:04d}.json", {**attempt, **outcome})
                ledger.finish(number, outcome)
                results[slot] = outcome
                if error.code in RECOVERABLE:
                    continue
                break
            attempt.update(response_text=response.text, parsed=response.parsed,
                           receipt=response.receipt)
            _write_once(output / f"response-{number:04d}.json", attempt)
            try:
                validation = validate_response(slot, response.parsed)
                if not isinstance(validation, dict) or validation.get("accepted") is not True:
                    raise ValueError("Source validator did not explicitly accept the proposal")
            except ValueError as error:
                # Semantic/reference failures are retained and never retried.
                outcome = {"status": "failed", "error_class": "proposal_validation",
                           "message": str(error)}
            else:
                outcome = {"status": "success", "validation": validation}
            _write_once(output / f"attempt-{number:04d}.json", {**attempt, **outcome})
            ledger.finish(number, outcome)
            results[slot] = {**outcome, "attempt": number}
            break
        if slot in development_slots and results[slot]["status"] != "success":
            stopped = True
    report = {"contract": "knowledge-copilot-observation-v1",
              "status": "experimental_observation_not_qualification",
              "results": results, "accounting": ledger.observation(),
              "human_review_benefit": "unexecuted",
              "c1_qualified": False}
    _write_once(output / "observation.json", report)
    return report
