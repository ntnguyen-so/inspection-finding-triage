"""Build and independently validate source-first provider context bundles."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .contracts import (KnowledgeError, TableSource, canonical_bytes, fields, nonblank,
                        require, sha256, strict_json)
from .retrieval import binding_from_tables, get_triage_knowledge
from .source_store import SourceKnowledgeStore


@dataclass(frozen=True)
class SourceContext:
    """Canonical provider context bytes with separate construction evidence."""
    encoded: bytes
    evidence_bytes: bytes

    def to_dict(self) -> dict:
        return strict_json(self.encoded)

    def evidence(self) -> dict:
        return strict_json(self.evidence_bytes)


def build_input_history(findings: dict, registry: dict) -> dict:
    """Derive chronology and explicit case relationships from trusted input rows."""
    by_equipment = {equipment_id: [] for equipment_id in registry}
    for finding_id, row in findings.items():
        by_equipment[row["equipment_id"]].append({
            "finding_id": finding_id,
            "reported_date": row["reported_date"],
            "source_refs": [
                f"finding:{finding_id}:reported_date",
                f"finding:{finding_id}:equipment_id",
                f"finding:{finding_id}:finding_description",
            ],
        })
    timelines = {
        equipment_id: sorted(entries, key=lambda item: (item["reported_date"], item["finding_id"]))
        for equipment_id, entries in sorted(by_equipment.items()) if entries
    }

    links: dict[tuple, dict] = {}

    def finding_ids(equipment_ids: list[str]) -> list[str]:
        return sorted(
            item["finding_id"]
            for equipment_id in equipment_ids
            for item in timelines.get(equipment_id, [])
        )

    def add_link(kind: str, equipment_ids: list[str], source_refs: list[str],
                 direction: list[str] | None = None) -> None:
        equipment_ids = sorted(set(equipment_ids))
        if sum(bool(timelines.get(equipment_id)) for equipment_id in equipment_ids) < 2:
            return
        related = finding_ids(equipment_ids)
        key = (kind, tuple(equipment_ids), tuple(direction or ()))
        existing = links.get(key)
        if existing is None:
            existing = {
                "kind": kind,
                "equipment_ids": equipment_ids,
                "finding_ids": related,
                "source_refs": [],
                "interpretation": "context_only_not_causation",
            }
            if direction is not None:
                existing["direction"] = direction
            links[key] = existing
        existing["source_refs"] = sorted(set(existing["source_refs"]) | set(source_refs))

    for equipment_id, row in sorted(registry.items()):
        partner = re.fullmatch(r"(?:N\+1|Duplicated) \(([A-Z]+-\d{4})\)", row["redundancy"])
        if partner and partner.group(1) in registry:
            add_link(
                "explicit_redundancy",
                [equipment_id, partner.group(1)],
                [f"equipment:{equipment_id}:redundancy"],
            )

    equipment_ids = set(registry)
    for equipment_id, row in sorted(registry.items()):
        for field in ("service_description", "engineer_comment"):
            text = row[field]
            for referenced in sorted(equipment_ids - {equipment_id}):
                if re.search(rf"(?<![A-Z0-9-]){re.escape(referenced)}(?![A-Z0-9-])", text):
                    add_link(
                        "explicit_registry_reference",
                        [equipment_id, referenced],
                        [f"equipment:{equipment_id}:{field}"],
                        [equipment_id, referenced],
                    )

    return {
        "contract": "triage-input-history-v1",
        "equipment_timelines": timelines,
        "case_links": sorted(
            links.values(),
            key=lambda item: (
                item["kind"], item["equipment_ids"], item.get("direction", []), item["finding_ids"],
            ),
        ),
        "limitations": [
            "Input history records observations, not repair completion or current equipment state.",
            "A registry reference supplies context only and does not establish causation.",
        ],
    }


def build_source_context(
    store: SourceKnowledgeStore, findings: TableSource, registry: TableSource, *,
    knowledge_version: str, assessment_time: str, expected_strategy: dict,
    assessment_policy: dict, max_bytes: int, input_purpose: str = "normal",
) -> SourceContext:
    """Assemble native bundle 3 once; the workflow retains it for all retries.

    Explicit isolated probes add a hash-covered input_purpose discriminator.
    Normal and probe contexts share the history-aware shape; probes add only
    the hash-covered input-purpose discriminator.
    """
    require(isinstance(assessment_policy, dict) and nonblank(assessment_policy.get("version"))
            and len(assessment_policy) > 1, "assessment_policy",
            "Workflow must supply its separate versioned assessment policy.")
    require(type(max_bytes) is int and max_bytes > 0, "context_limit",
            "A positive full-context byte limit is required.")
    binding = binding_from_tables(findings, registry, input_purpose=input_purpose)
    query = {"findings": {row["finding_id"]: row for row in findings.rows},
             "registry": {row["equipment_id"]: row for row in registry.rows}}
    knowledge = get_triage_knowledge(
        store, query, knowledge_version=knowledge_version, assessment_time=assessment_time,
        expected_strategy=expected_strategy, allowed_input_binding=binding, max_bytes=max_bytes,
        input_purpose=input_purpose)
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
    payload = {**query, "knowledge": selected,
               "history": build_input_history(query["findings"], query["registry"])}
    body = {"contract_version": 3, "payload": payload, "source_index": index,
            "finding_ids": sorted(query["findings"]), "knowledge_version": knowledge_version,
            "assessment_time": assessment_time, "assessment_policy": assessment_policy,
            "knowledge_result_hash": result["content_sha256"]}
    if input_purpose == "isolated_probe":
        body["input_purpose"] = input_purpose
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
    if input_purpose == "isolated_probe":
        evidence["input_purpose"] = input_purpose
    return SourceContext(encoded, canonical_bytes(evidence))


def validate_source_context(
    bundle: SourceContext | bytes, findings: TableSource, registry: TableSource,
    store: SourceKnowledgeStore, *,
    knowledge_version: str, assessment_time: str, expected_strategy: dict,
    expected_assessment_policy: dict, max_bytes: int, expected_input_purpose: str = "normal",
) -> SourceContext:
    """Validate native bundle 3 against independent tables, store and trusted pins.

    Rebuild local evidence from the supplied tables, never from bundle evidence.
    Expected input purpose is a trusted caller pin, never inferred from the bundle.
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
    require(expected_input_purpose in ("normal", "isolated_probe"), "input_binding_mismatch",
            "An explicit supported input purpose is required.")
    names = {
        "contract_version", "payload", "source_index", "finding_ids", "knowledge_version",
        "assessment_time", "assessment_policy", "knowledge_result_hash", "context_hash",
    }
    if expected_input_purpose == "isolated_probe":
        names.add("input_purpose")
    packet = fields(strict_json(raw), names, "source_context")
    if expected_input_purpose == "isolated_probe":
        require(packet["input_purpose"] == expected_input_purpose, "input_binding_mismatch",
                "The supplied context differs from the trusted input purpose.")
    require(type(packet["contract_version"]) is int and packet["contract_version"] == 3,
            "unsupported_contract", "Only native source context version 3 is supported.")
    body = {key: value for key, value in packet.items() if key != "context_hash"}
    require(packet["context_hash"] == sha256(canonical_bytes(body)), "context_hash",
            "The supplied context hash does not match its contents.")
    require(isinstance(store, SourceKnowledgeStore), "unknown_or_invalid_release",
            "An independently supplied source knowledge store is required.")
    expected = build_source_context(
        store, findings, registry, knowledge_version=knowledge_version,
        assessment_time=assessment_time, expected_strategy=expected_strategy,
        assessment_policy=expected_assessment_policy, max_bytes=max_bytes,
        input_purpose=expected_input_purpose)
    require(canonical_bytes(packet["assessment_policy"])
            == canonical_bytes(expected_assessment_policy), "assessment_policy",
            "The supplied context differs from the trusted workflow assessment policy.")
    require(canonical_bytes(packet) == expected.encoded, "context_contract",
            "The supplied context differs from independently regenerated source context.")
    return expected
