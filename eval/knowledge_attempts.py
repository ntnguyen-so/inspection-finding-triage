"""Persistent application-send accounting; Copilot HTTP counts remain unknown."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       allow_nan=False, indent=2) + "\n").encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def _read(path: Path) -> dict:
    def pairs(items: list) -> dict:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate ledger key")
            result[key] = value
        return result
    def invalid_constant(value: str) -> None:
        raise ValueError(f"Nonfinite ledger value: {value}")

    result = json.loads(path.read_text("utf-8"), object_pairs_hook=pairs,
                        parse_constant=invalid_constant)
    if not isinstance(result, dict):
        raise ValueError("Ledger must be an object")
    return result


def _replace(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class AttemptLedger:
    """Single-writer ledger with reservations surviving crashes and failed sends."""

    def __init__(self, path: Path, plan: dict):
        self.path = Path(path)
        if not self.path.name.endswith(".experimental-ledger.json"):
            raise ValueError("Copilot needs a distinct .experimental-ledger.json")
        if (set(plan) != {"phase", "slots", "maximum_attempts", "per_slot_attempts",
                          "schedule", "development_slots", "recoverable_codes"}
                or not isinstance(plan["phase"], str) or not plan["phase"].strip()
                or not isinstance(plan["slots"], dict) or not 1 <= len(plan["slots"]) <= 13
                or any(not isinstance(k, str) or not k or not isinstance(v, str)
                       or len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
                       for k, v in plan["slots"].items())
                or type(plan["maximum_attempts"]) is not int
                or not 1 <= plan["maximum_attempts"] <= 26
                or type(plan["per_slot_attempts"]) is not int
                or not 1 <= plan["per_slot_attempts"] <= 2):
            raise ValueError("Invalid frozen attempt plan")
        for field in ("schedule", "development_slots", "recoverable_codes"):
            values = plan[field]
            if (not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values)
                    or len(values) != len(set(values))):
                raise ValueError("Invalid frozen schedule or retry allowlist")
        development = set(plan["development_slots"])
        if (set(plan["schedule"]) != set(plan["slots"])
                or not development <= plan["slots"].keys()
                or set(plan["schedule"][:len(development)]) != development):
            raise ValueError("Development slots must precede evaluation")
        self.plan = json.loads(encoded(plan))
        self.binding = fingerprint(self.plan)
        if self.path.exists():
            self._load()
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("xb") as stream:
                stream.write(encoded({"contract": "knowledge-attempt-ledger-v1",
                                      "plan": self.plan, "plan_sha256": self.binding,
                                      "attempts": []}))
                stream.flush()
                os.fsync(stream.fileno())

    def _load(self) -> dict:
        data = _read(self.path)
        if (set(data) != {"contract", "plan", "plan_sha256", "attempts"}
                or data["contract"] != "knowledge-attempt-ledger-v1"
                or data["plan"] != self.plan or data["plan_sha256"] != self.binding
                or not isinstance(data["attempts"], list)):
            raise ValueError("Attempt plan changed or ledger malformed")
        counts = dict.fromkeys(self.plan["slots"], 0)
        for number, attempt in enumerate(data["attempts"], 1):
            if (not isinstance(attempt, dict)
                    or set(attempt) != {"number", "slot", "request_sha256",
                                      "reserved_at", "state", "outcome"}
                    or attempt["number"] != number
                    or type(attempt["number"]) is not int
                    or not isinstance(attempt["slot"], str) or attempt["slot"] not in counts
                    or attempt["request_sha256"] != self.plan["slots"][attempt["slot"]]
                    or attempt["state"] not in {"reserved", "finished"}
                    or not isinstance(attempt["reserved_at"], str)
                    or (attempt["state"] == "reserved" and attempt["outcome"] is not None)
                    or (attempt["state"] == "finished"
                        and (not isinstance(attempt["outcome"], dict)
                             or attempt["outcome"].get("status") not in {"success", "failed"}))):
                raise ValueError("Invalid application-attempt history")
            counts[attempt["slot"]] += 1
        if (len(data["attempts"]) > self.plan["maximum_attempts"]
                or any(n > self.plan["per_slot_attempts"] for n in counts.values())):
            raise ValueError("Ledger already exceeds the frozen ceiling")
        return data

    def reserve(self, slot: str, request_sha256: str) -> int:
        data = self._load()
        if self.plan["slots"].get(slot) != request_sha256:
            raise ValueError("Request is not in the frozen phase")
        previous = [a for a in data["attempts"] if a["slot"] == slot]
        if any(a["state"] == "reserved" for a in previous):
            raise ValueError("Interrupted send is unresolved; never silently resend")
        if any(a["outcome"].get("status") == "success" for a in previous):
            raise ValueError("A successful slot cannot be repeated under its old identity")
        if previous and previous[-1]["outcome"].get("error_class") not in self.plan["recoverable_codes"]:
            raise ValueError("Previous failure is not recoverable under the frozen plan")
        if (len(previous) >= self.plan["per_slot_attempts"]
                or len(data["attempts"]) >= self.plan["maximum_attempts"]):
            raise ValueError("Frozen application-send budget exhausted")
        number = len(data["attempts"]) + 1
        data["attempts"].append({
            "number": number, "slot": slot, "request_sha256": request_sha256,
            "reserved_at": datetime.now(timezone.utc).isoformat(),
            "state": "reserved", "outcome": None,
        })
        _replace(self.path, data)
        return number

    def finish(self, number: int, outcome: dict) -> None:
        data = self._load()
        if (type(number) is not int or not 1 <= number <= len(data["attempts"])
                or data["attempts"][number - 1]["state"] != "reserved"
                or not isinstance(outcome, dict)
                or outcome.get("status") not in {"success", "failed"}):
            raise ValueError("Invalid attempt completion")
        encoded(outcome)
        data["attempts"][number - 1].update(state="finished", outcome=outcome)
        _replace(self.path, data)

    def observation(self) -> dict:
        data = self._load()
        return {"plan_sha256": self.binding, "application_attempts_reserved":
                len(data["attempts"]), "maximum_application_attempts":
                self.plan["maximum_attempts"], "http_attempts": None,
                "usd_cost": None, "strict_accounting_pass": False,
                "attempts": data["attempts"]}


def inspect_ledger(path: Path) -> dict:
    """Read-only crash accounting; never creates a ledger or resends a request."""
    data = _read(Path(path))
    if "plan" not in data:
        raise ValueError("Missing frozen plan")
    return AttemptLedger(Path(path), data["plan"]).observation()
