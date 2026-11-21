"""Native source-first consumer boundary; selection stays in triage_knowledge."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from triage_knowledge import (
    KnowledgeError, SourceKnowledgeStore, TableSource, build_source_context,
    strategy_binding, validate_source_context,
)
from triage_knowledge.contracts import canonical_bytes, strict_json

from .assessment_policy import ASSESSMENT_POLICY_SHA256, assessment_policy
from .contracts import TriageError, digest, nonblank, require, timestamp
from .inputs import Inputs, missing_partner_gaps, validate_rows
from .prompt import DEFAULT_ASSESSMENT_PROMPT_VERSION, assessment_prompt, prompt_from_identity


def execution_policy_hash() -> str:
    """Hash top-level ``triage`` modules; provider adapters are pinned elsewhere."""
    root = Path(__file__).parent
    manifest = {
        path.name: digest(path.read_bytes())
        for path in sorted(root.glob("*.py"))
    }
    return digest(canonical_bytes(manifest))


def retrieval_index_hash(candidate: dict) -> str:
    """Hash retrieval-relevant release metadata without mutable review prose."""
    items = {item_id: {
        "revision_id": item["revision_id"], "review_state": item["review_state"],
        **{key: item["revision"][key] for key in
           ("source_id", "source_sha256", "spans", "scopes", "aliases",
            "status", "effective_from", "effective_until")},
    } for item_id, item in candidate["items"].items()}
    return digest(canonical_bytes({"items": items, "context_links": candidate["context_links"],
                                   "replacements": candidate["replacements"]}))


def activation_candidate(store: SourceKnowledgeStore, version: str, *,
                         prompt_version: str = DEFAULT_ASSESSMENT_PROMPT_VERSION) -> dict:
    """Prepare pins only; a candidate is deliberately not an activation approval."""
    release = store.resolve_release(version)
    return {
        "contract": "triage-activation-v2", "knowledge_version": version,
        "strategy": strategy_binding(),
        "retrieval_index_sha256": retrieval_index_hash(release["candidate"]),
        "assessment_policy_sha256": ASSESSMENT_POLICY_SHA256,
        "execution_policy_sha256": execution_policy_hash(),
        "assessment_prompt": assessment_prompt(prompt_version).identity(), "review": None,
    }


class _PinnedStore(SourceKnowledgeStore):
    def __init__(self, store: SourceKnowledgeStore, version: str, release: dict):
        super().__init__(store.root)
        self._version = version
        self._release = canonical_bytes(release)

    def resolve_release(self, releaseid):
        require(releaseid == self._version, "knowledge_version", "Pinned knowledge release changed")
        return strict_json(self._release)


class NativeContext:
    """Prepare a source-first context only after validating all activation pins."""

    def __init__(self, store: Path, activation: dict):
        self.store_path = Path(store)
        self._activation = canonical_bytes(activation)
        self._probe = None
        self._input_kind = "finding_input"
        self._input_purpose = None

    def prepare(self, inputs: Inputs, version: str, assessment_time: str,
                max_bytes: int) -> tuple[dict, str, dict]:
        try:
            return self._prepare(inputs, version, assessment_time, max_bytes)
        except KnowledgeError as error:
            raise TriageError(error.code, str(error)) from error
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
            raise TriageError("context_contract", "Malformed native context dependency result") from error

    def _prepare(self, inputs: Inputs, version: str, assessment_time: str,
                 max_bytes: int) -> tuple[dict, str, dict]:
        activation = strict_json(self._activation)
        require(isinstance(activation, dict) and set(activation) == {
            "contract", "knowledge_version", "strategy", "retrieval_index_sha256",
            "assessment_policy_sha256", "execution_policy_sha256", "assessment_prompt", "review",
        } and activation["contract"] == "triage-activation-v2",
                "knowledge_activation", "Explicit source-first activation contract required")
        review = activation["review"]
        require(isinstance(review, dict) and set(review) ==
                {"reviewer", "reason", "reviewed_at", "source_policy_compatible"}
                and nonblank(review["reviewer"]) and nonblank(review["reason"])
                and review["source_policy_compatible"] is True,
                "knowledge_activation", "Review exact source/policy compatibility before activation")
        timestamp(review["reviewed_at"])
        require(activation["knowledge_version"] == version
                and activation["strategy"] == strategy_binding()
                and activation["assessment_policy_sha256"] == ASSESSMENT_POLICY_SHA256
                and activation["execution_policy_sha256"] == execution_policy_hash()
                and prompt_from_identity(activation["assessment_prompt"]).identity() ==
                activation["assessment_prompt"],
                "knowledge_activation", "Release, strategy or workflow policy differs from activation")
        cutoff = timestamp(assessment_time)
        data = inputs.data
        validate_rows(data["findings"], data["registry"])
        require(all(date.fromisoformat(row["reported_date"]) <= cutoff.date()
                    for row in data["findings"].values()),
                "assessment_time", "A finding is later than the assessment cutoff")
        require(digest(inputs.findings_raw) == inputs.findings_hash
                and digest(inputs.registry_raw) == inputs.registry_hash,
                "input_binding_mismatch", "Input bytes differ from their independent hashes")
        policy, input_kind = assessment_policy(), self._input_kind
        probe = strict_json(self._probe) if self._probe is not None else None
        if probe is not None:
            require(set(probe) == {
                "contract", "experiment_id", "input_kind", "findings_sha256", "registry_sha256",
                "assessment_policy", "assessment_policy_sha256",
            } and probe["contract"] == "triage-isolated-probe-v1"
                    and nonblank(probe["experiment_id"])
                    and probe["input_kind"] in {"evaluation_input", "finding_input"}
                    and probe["findings_sha256"] == inputs.findings_hash
                    and probe["registry_sha256"] == inputs.registry_hash
                    and isinstance(probe["assessment_policy"], dict)
                    and digest(canonical_bytes(probe["assessment_policy"])) ==
                    probe["assessment_policy_sha256"],
                    "context_overlay", "Isolated probe inputs/policy must match independently trusted pins")
            policy, input_kind = probe["assessment_policy"], probe["input_kind"]
            require({key: value for key, value in policy.items() if key != "isolated_experiment"} ==
                    assessment_policy() and isinstance(policy.get("isolated_experiment"), dict)
                    and policy["isolated_experiment"].get("experiment_id") == probe["experiment_id"],
                    "context_overlay", "Only the separately labelled experimental policy may differ")
        findings = TableSource.from_bytes(inputs.findings_raw, source_id="findings", kind=input_kind)
        registry = TableSource.from_bytes(inputs.registry_raw, source_id="registry", kind="registry_input")
        require({row["finding_id"]: row for row in findings.rows} == data["findings"]
                and {row["equipment_id"]: row for row in registry.rows} == data["registry"],
                "input_binding_mismatch", "Validated rows differ from independent CSV bytes")
        store = SourceKnowledgeStore(self.store_path)
        try:
            release = store.resolve_release(version)
        except KnowledgeError as error:
            raise TriageError(error.code, str(error)) from error
        except OSError as error:
            raise TriageError("unknown_or_invalid_release", "Pinned source-first release unavailable") from error
        require(activation["retrieval_index_sha256"] == retrieval_index_hash(release["candidate"]),
                "strategy_binding_mismatch", "Reviewed retrieval index differs from activation")
        pinned = _PinnedStore(store, version, release)
        native = build_source_context(
            pinned, findings, registry, knowledge_version=version, assessment_time=assessment_time,
            expected_strategy=activation["strategy"], assessment_policy=policy,
            max_bytes=max_bytes, **({"input_purpose": self._input_purpose}
                                    if self._input_purpose else {}),
        )
        validated = validate_source_context(
            native, findings, registry, pinned, knowledge_version=version,
            assessment_time=assessment_time, expected_strategy=activation["strategy"],
            expected_assessment_policy=policy, max_bytes=max_bytes,
            **({"expected_input_purpose": self._input_purpose}
               if self._input_purpose else {}),
        )
        bundle, evidence = validated.to_dict(), validated.evidence()
        result = evidence["retrieval"]
        require(result["retrieval_index_sha256"] == activation["retrieval_index_sha256"],
                "strategy_binding_mismatch", "Validated retrieval index differs from activation")
        expected_manifest = [
            {"source_id": "findings", "kind": input_kind, "sha256": inputs.findings_hash},
            {"source_id": "registry", "kind": "registry_input", "sha256": inputs.registry_hash},
        ]
        require(evidence["source_manifest"] == expected_manifest,
                "context_manifest", "Native evidence differs from authorized input manifests")
        return bundle, validated.encoded.decode("utf-8"), {
            "content_hash": version.removeprefix("sha256-"), "activation": activation,
            "activation_sha256": digest(self._activation), "native_evidence": evidence,
            "consumer_validation": "module_owned_independent_rebuild_from_trusted_inputs_and_pins",
            "gaps": missing_partner_gaps(data),
            **({"isolated_experiment": probe} if probe else {}),
        }


class IsolatedProbeContext(NativeContext):
    """Explicit test-only handoff; the normal CLI cannot construct this variant."""

    def __init__(self, store: Path, activation: dict, experiment: dict):
        require(isinstance(experiment, dict), "context_overlay", "Explicit isolated experiment pins required")
        super().__init__(store, activation)
        self._input_purpose = "isolated_probe"
        self._probe = canonical_bytes(experiment)


class IsolatedKnowledgeReleaseContext(NativeContext):
    """Evaluation-only probe: evaluation inputs, production policy, experimental output."""

    def __init__(self, store: Path, activation: dict):
        super().__init__(store, activation)
        self._input_kind = "evaluation_input"
        self._input_purpose = "isolated_probe"
