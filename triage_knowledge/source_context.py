from __future__ import annotations

from dataclasses import dataclass

from .contracts import (KnowledgeError, TableSource, canonical_bytes, fields, nonblank,
                        require, sha256, strict_json)
from .retrieval import binding_from_tables, get_triage_knowledge
from .source_store import SourceKnowledgeStore


@dataclass(frozen=True)
class SourceContext:
    encoded: bytes
    evidence_bytes: bytes

    def to_dict(self) -> dict:
        return strict_json(self.encoded)

    def evidence(self) -> dict:
        return strict_json(self.evidence_bytes)


def build_source_context(
    store: SourceKnowledgeStore, findings: TableSource, registry: TableSource, *,
    knowledge_version: str, assessment_time: str, expected_strategy: dict,
    assessment_policy: dict, max_bytes: int,
) -> SourceContext:
    """Assemble native bundle 2 once; the workflow retains it for all retries."""
    require(isinstance(assessment_policy, dict) and nonblank(assessment_policy.get("version"))
            and len(assessment_policy) > 1, "assessment_policy",
            "Workflow must supply its separate versioned assessment policy.")
    require(type(max_bytes) is int and max_bytes > 0, "context_limit",
            "A positive full-context byte limit is required.")
    binding = binding_from_tables(findings, registry)
    query = {"findings": {row["finding_id"]: row for row in findings.rows},
             "registry": {row["equipment_id"]: row for row in registry.rows}}
    knowledge = get_triage_knowledge(
        store, query, knowledge_version=knowledge_version, assessment_time=assessment_time,
        expected_strategy=expected_strategy, allowed_input_binding=binding, max_bytes=max_bytes)
    result = knowledge.to_dict()
    if result["status"] != "ok":
        raise KnowledgeError(result["error_code"], "Required knowledge is unavailable; stop assessment.")
    selected = knowledge.provider_payload()
    require(isinstance(selected, dict) and selected
            and all(nonblank(key) and isinstance(value, str) and bool(value)
                    for key, value in selected.items()),
            "context_contract", "Retrieval returned an invalid provider projection.")
    index = dict(selected)
    for kind, table in (("finding", query["findings"]), ("equipment", query["registry"])):
        for identifier, row in table.items():
            index.update({f"{kind}:{identifier}:{field}": value for field, value in row.items()})
    payload = {**query, "knowledge": selected}
    body = {"contract_version": 2, "payload": payload, "source_index": index,
            "finding_ids": sorted(query["findings"]), "knowledge_version": knowledge_version,
            "assessment_time": assessment_time, "assessment_policy": assessment_policy,
            "knowledge_result_hash": result["content_sha256"]}
    context_hash = sha256(canonical_bytes(body))
    encoded = canonical_bytes({**body, "context_hash": context_hash})
    require(len(encoded) <= max_bytes, "context_limit",
            "The complete provider context exceeds the configured byte limit.")
    evidence = {"context_hash": context_hash, "retrieval": result,
                "source_manifest": [
                    {"source_id": findings.source_id, "kind": findings.kind,
                     "sha256": findings.raw_sha256},
                    {"source_id": registry.source_id, "kind": registry.kind,
                     "sha256": registry.raw_sha256}],
                "approval": "local_release_declaration_not_operational_approval"}
    return SourceContext(encoded, canonical_bytes(evidence))


def validate_source_context(
    bundle: SourceContext | bytes, findings: TableSource, registry: TableSource,
    store: SourceKnowledgeStore, *,
    knowledge_version: str, assessment_time: str, expected_strategy: dict,
    expected_assessment_policy: dict, max_bytes: int,
) -> SourceContext:
    """Validate native bundle 2 against independent tables, store and trusted pins.

    Rebuild local evidence from the supplied tables, never from bundle evidence.
    Equivalent CSV row ordering and JSON formatting do not change semantic identity.
    This verifies a context, not provider delivery or operational approval.
    """
    require(type(max_bytes) is int and max_bytes > 0, "context_limit",
            "A positive full-context byte limit is required.")
    raw = bundle.encoded if isinstance(bundle, SourceContext) else bundle
    require(type(raw) is bytes, "context_contract",
            "A SourceContext or serialized UTF-8 JSON bytes are required.")
    require(len(raw) <= max_bytes, "context_limit",
            "The supplied provider context exceeds the configured byte limit.")
    packet = fields(strict_json(raw), {
        "contract_version", "payload", "source_index", "finding_ids", "knowledge_version",
        "assessment_time", "assessment_policy", "knowledge_result_hash", "context_hash",
    }, "source_context")
    require(type(packet["contract_version"]) is int and packet["contract_version"] == 2,
            "unsupported_contract", "Only native source context version 2 is supported.")
    body = {key: value for key, value in packet.items() if key != "context_hash"}
    require(packet["context_hash"] == sha256(canonical_bytes(body)), "context_hash",
            "The supplied context hash does not match its contents.")
    require(isinstance(store, SourceKnowledgeStore), "unknown_or_invalid_release",
            "An independently supplied source knowledge store is required.")
    expected = build_source_context(
        store, findings, registry, knowledge_version=knowledge_version,
        assessment_time=assessment_time, expected_strategy=expected_strategy,
        assessment_policy=expected_assessment_policy, max_bytes=max_bytes)
    require(canonical_bytes(packet["assessment_policy"])
            == canonical_bytes(expected_assessment_policy), "assessment_policy",
            "The supplied context differs from the trusted workflow assessment policy.")
    require(canonical_bytes(packet) == expected.encoded, "context_contract",
            "The supplied context differs from independently regenerated source context.")
    return expected
