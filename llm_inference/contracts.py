from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Protocol

from jsonschema import Draft202012Validator, SchemaError, ValidationError


class InferenceError(RuntimeError):
    def __init__(self, code: str, message: str, receipt: dict | None = None):
        super().__init__(message)
        self.code = code
        self.receipt = receipt if receipt is not None else {}

    def to_dict(self) -> dict:
        return {
            "status": "failed",
            "error_class": self.code,
            "message": str(self),
            "receipt": self.receipt,
        }


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def strict_json(text: str) -> object:
    def finite_float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite JSON number")
        return number

    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_float=finite_float,
    )


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class InferenceRequest:
    model: str
    system: str
    user: str
    response_schema: dict | None = None
    reasoning_effort: str | None = None
    timeout_seconds: float = 90

    def prepared(self) -> tuple[str, str, Draft202012Validator | None]:
        for name in ("model", "system", "user"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InferenceError("invalid_request", f"{name} must be nonempty text")
        if self.model.lower() in {"auto", "fusion"}:
            raise InferenceError("unsupported_control", "An explicit model is required")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= 300
        ):
            raise InferenceError("invalid_request", "Timeout must be in (0, 300] seconds")
        if self.reasoning_effort is not None and not isinstance(
            self.reasoning_effort, str
        ):
            raise InferenceError("invalid_request", "reasoning_effort must be text")
        system, user, validator = self.system, self.user, None
        if self.response_schema is not None:
            if not isinstance(self.response_schema, dict):
                raise InferenceError("invalid_schema", "Schema must be an object")

            def no_references(value: object) -> None:
                if isinstance(value, dict):
                    if "$ref" in value or "$dynamicRef" in value:
                        raise InferenceError(
                            "unsupported_control", "Schema references are not supported"
                        )
                    for child in value.values():
                        no_references(child)
                elif isinstance(value, list):
                    for child in value:
                        no_references(child)

            try:
                schema = strict_json(canonical(self.response_schema))
                no_references(schema)
                if schema.get("$schema", "https://json-schema.org/draft/2020-12/schema") != (
                    "https://json-schema.org/draft/2020-12/schema"
                ):
                    raise InferenceError(
                        "unsupported_control", "Only JSON Schema Draft 2020-12 is supported"
                    )
                Draft202012Validator.check_schema(schema)
                validator = Draft202012Validator(schema)
                system += (
                    "\n\nReturn exactly one JSON value conforming to the following "
                    "JSON Schema. No markdown fences or additional text.\n"
                    + canonical(schema)
                )
            except (ValueError, TypeError, RecursionError, SchemaError) as error:
                raise InferenceError("invalid_schema", "Invalid response schema") from error
        try:
            size = len(system.encode("utf-8")) + len(user.encode("utf-8"))
        except UnicodeError as error:
            raise InferenceError("invalid_request", "Prompts must be valid UTF-8") from error
        if size > 256_000:
            raise InferenceError("invalid_request", "Prompt exceeds 256000 bytes")
        return system, user, validator


def validate_content(text: str, validator: Draft202012Validator | None) -> object:
    if not isinstance(text, str) or not text.strip():
        raise InferenceError("empty_response", "No final assistant text")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise InferenceError("invalid_response", "Response is not valid UTF-8") from error
    if size > 128_000:
        raise InferenceError("response_limit", "Response exceeds 128000 bytes")
    if validator is None:
        return None
    try:
        value = strict_json(text)
    except (ValueError, RecursionError) as error:
        raise InferenceError("malformed_json", "Response is not strict JSON") from error
    try:
        validator.validate(value)
    except ValidationError as error:
        raise InferenceError(
            "schema_violation", "Response does not conform to the response schema"
        ) from error
    return value


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    parsed: object
    receipt: dict


class InferenceProvider(Protocol):
    async def generate(self, request: InferenceRequest) -> InferenceResponse: ...
