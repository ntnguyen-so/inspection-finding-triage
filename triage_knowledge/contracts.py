"""Strict serialization, identity and immutable table-source contracts."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import hashlib
import io
import json
import re
from typing import Any


class KnowledgeError(ValueError):
    """Source-first knowledge failure with a stable field-aware diagnostic."""
    def __init__(self, code: str, message: str, field: str = ""):
        super().__init__(message)
        self.code = code
        self.field = field

    def diagnostic(self) -> dict:
        return {"status": "failed", "error_class": self.code,
                "field": self.field, "message": str(self)}


def require(condition: object, code: str, message: str, field: str = "") -> None:
    if not condition:
        raise KnowledgeError(code, message, field)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def identifier(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value) is not None


def release_identifier(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256-[a-f0-9]{64}", value) is not None


def timestamp(value: object, field: str) -> datetime:
    require(isinstance(value, str) and "T" in value, "timestamp",
            "An ISO-8601 timestamp with an explicit timezone is required.", field)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise KnowledgeError("timestamp", "Invalid ISO-8601 timestamp.", field) from error
    require(parsed.utcoffset() is not None, "timestamp", "An explicit timezone is required.", field)
    return parsed


def _json_value(value: object) -> None:
    if value is None or type(value) in (str, bool, int):
        return
    if isinstance(value, dict) and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _json_value(item)
        return
    raise KnowledgeError("json_value", "Only finite integer-valued JSON data is supported.")


def canonical_bytes(value: object) -> bytes:
    """Serialize the restricted knowledge JSON domain into canonical UTF-8 bytes."""
    try:
        _json_value(value)
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except KnowledgeError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise KnowledgeError("json_value", "Invalid Unicode or excessive JSON nesting.") from error


def strict_json(raw: bytes | str) -> Any:
    """Decode strict integer-valued JSON while rejecting duplicate keys."""
    require(isinstance(raw, (bytes, str)), "json_decode", "UTF-8 JSON bytes or text are required.")
    def pairs(items: list) -> dict:
        result = {}
        for key, value in items:
            require(key not in result, "json_duplicate", "Duplicate JSON object key.", key)
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise KnowledgeError("json_number", "Floats and nonfinite JSON values are not supported.")

    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        result = json.loads(text, object_pairs_hook=pairs, parse_float=invalid,
                            parse_constant=invalid)
        canonical_bytes(result)
        return result
    except KnowledgeError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise KnowledgeError("json_decode", "Invalid UTF-8 JSON.") from error


def fields(value: object, names: set[str], path: str) -> dict:
    require(isinstance(value, dict) and set(value) == names, "schema",
            "Missing, extra or invalid object fields.", path)
    return value


@dataclass(frozen=True)
class TableSource:
    """Exact CSV bytes bound to an authorized logical source and input kind."""
    source_id: str
    kind: str
    raw: bytes

    def __post_init__(self) -> None:
        require(identifier(self.source_id), "input_source", "Invalid logical source ID.")
        require(isinstance(self.kind, str)
                and self.kind in {"finding_input", "registry_input", "evaluation_input"},
                "input_source", "Invalid table source kind.")
        require(type(self.raw) is bytes, "input_source", "Original CSV bytes are required.")
        self._parse()

    @classmethod
    def from_bytes(cls, raw: bytes, *, source_id: str, kind: str) -> TableSource:
        return cls(source_id, kind, raw)

    def _parse(self) -> list[dict[str, str]]:
        try:
            reader = csv.DictReader(io.StringIO(self.raw.decode("utf-8-sig"), newline=""),
                                    strict=True)
            header = reader.fieldnames
            require(bool(header) and all(nonblank(x) for x in header)
                    and len(header) == len(set(header)), "input_header",
                    "CSV headers must be nonempty and unique.")
            rows = list(reader)
            require(rows and all(set(row) == set(header)
                                and all(isinstance(v, str) for v in row.values())
                                for row in rows), "input_cell",
                    "CSV rows must have exactly the declared fields.")
            return rows
        except (UnicodeError, csv.Error) as error:
            raise KnowledgeError("input_csv", "Invalid UTF-8 CSV.") from error

    @property
    def rows(self) -> list[dict[str, str]]:
        return self._parse()

    @property
    def raw_sha256(self) -> str:
        return sha256(self.raw)
