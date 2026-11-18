from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

from .contracts import TriageError, digest, require

DEFAULT_ASSESSMENT_PROMPT_VERSION = "assessment-system-v1"
ASSESSMENT_CONTRACT = "native-assessment-v2"
PLANNED_ASSESSMENT_CONTRACT = "native-assessment-v3"
GROUNDED_PLAN_ASSESSMENT_CONTRACT = "native-assessment-v4"
ASSESSMENT_SCHEMA_CONTRACT = "triage-assessment-schema-v1"
PLANNED_SCHEMA_CONTRACT = "triage-assessment-schema-v2"
GROUNDED_PLAN_SCHEMA_CONTRACT = "triage-assessment-schema-v3"
CONTEXT_CONTRACT_VERSION = 3
_RESOURCES = {
    "assessment-system-v1": (("prompts", "assessment-system-v1.txt"),
                             ASSESSMENT_CONTRACT, ASSESSMENT_SCHEMA_CONTRACT),
    "assessment-system-v2": (("prompts", "assessment-system-v2.txt"),
                             ASSESSMENT_CONTRACT, ASSESSMENT_SCHEMA_CONTRACT),
    "assessment-system-v3": (("prompts", "assessment-system-v3.txt"),
                             ASSESSMENT_CONTRACT, ASSESSMENT_SCHEMA_CONTRACT),
    "assessment-system-v4": (("prompts", "assessment-system-v4.txt"),
                             PLANNED_ASSESSMENT_CONTRACT, PLANNED_SCHEMA_CONTRACT),
    "assessment-system-v5": (("prompts", "assessment-system-v5.txt"),
                             GROUNDED_PLAN_ASSESSMENT_CONTRACT,
                             GROUNDED_PLAN_SCHEMA_CONTRACT),
    "assessment-system-v6": (("prompts", "assessment-system-v6.txt"),
                             GROUNDED_PLAN_ASSESSMENT_CONTRACT,
                             GROUNDED_PLAN_SCHEMA_CONTRACT),
    "assessment-system-v7": (("prompts", "assessment-system-v7.txt"),
                             GROUNDED_PLAN_ASSESSMENT_CONTRACT,
                             GROUNDED_PLAN_SCHEMA_CONTRACT),
    "assessment-system-v8": ((("prompts", "assessment-system-v7.txt"),
                              ("prompts", "assessment-system-v8-addendum.txt")),
                             GROUNDED_PLAN_ASSESSMENT_CONTRACT,
                             GROUNDED_PLAN_SCHEMA_CONTRACT),
}


@dataclass(frozen=True)
class PromptArtifact:
    version: str
    text: str
    sha256: str
    assessment_contract: str
    schema_contract: str

    def identity(self) -> dict:
        return {
            "version": self.version,
            "sha256": self.sha256,
            "assessment_contract": self.assessment_contract,
            "schema_contract": self.schema_contract,
            "context_contract_version": CONTEXT_CONTRACT_VERSION,
        }


@lru_cache(maxsize=None)
def assessment_prompt(version: str = DEFAULT_ASSESSMENT_PROMPT_VERSION) -> PromptArtifact:
    require(version in _RESOURCES, "assessment_prompt", "Unknown assessment prompt version")
    try:
        resource, assessment_contract, schema_contract = _RESOURCES[version]
        resources = resource if isinstance(resource[0], tuple) else (resource,)
        raw = b"\n\n".join(
            files("triage").joinpath(*item).read_bytes() for item in resources
        )
    except OSError as error:
        raise TriageError("assessment_prompt", "Assessment prompt artifact is unavailable") from error
    require(raw and not raw.startswith(b"\xef\xbb\xbf"),
            "assessment_prompt", "Assessment prompt must be nonempty UTF-8 without BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise TriageError("assessment_prompt", "Assessment prompt is not valid UTF-8") from error
    return PromptArtifact(version, text, digest(raw), assessment_contract, schema_contract)


def prompt_from_identity(identity: dict) -> PromptArtifact:
    require(isinstance(identity, dict) and set(identity) == {
        "version", "sha256", "assessment_contract", "schema_contract",
        "context_contract_version",
    }, "assessment_prompt", "Invalid assessment prompt identity")
    artifact = assessment_prompt(identity["version"])
    require(identity == artifact.identity(),
            "assessment_prompt", "Assessment prompt differs from reviewed activation")
    return artifact
