from __future__ import annotations

import hashlib
import re
from datetime import datetime

from llm_inference.contracts import canonical, strict_json


class TriageError(RuntimeError):
    def __init__(self, code: str, message: str, finding_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.finding_id = finding_id
        self.attempts = 0
        self.execution_mode = "strict"

    def diagnostic(self) -> dict:
        result = {
            "run_status": "failed",
            "finding_id": self.finding_id,
            "error_class": self.code,
            "message": str(self),
            "attempts": self.attempts,
            "published_output": False,
        }
        if self.execution_mode in {"copilot_experiment", "copilot_delivery"}:
            result.update(execution_mode=self.execution_mode, acceptance_eligible=False,
                          attempt_accounting_unit="application_sends_http_attempts_unknown")
        return result


def require(condition: object, code: str, message: str) -> None:
    if not condition:
        raise TriageError(code, message)


def nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_copy(value: object) -> object:
    return strict_json(canonical(value))


def timestamp(value: object) -> datetime:
    try:
        require(isinstance(value, str) and "T" in value, "timestamp", "ISO timestamp required")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.utcoffset() is not None, "timestamp", "Explicit timezone required")
        return parsed
    except ValueError as error:
        raise TriageError("timestamp", "Invalid ISO timestamp") from error


def score(value: object) -> int:
    require(type(value) is int and 1 <= value <= 10, "score", "Score must be integer 1-10")
    return value


def sha256_value(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None
