from __future__ import annotations

from datetime import date
import re

from .contracts import (
    ContextBundle, ContextError, EvaluationOverlay, KnowledgeError, KnowledgeSnapshot,
    TableSource, canonical_bytes, fields, nonblank, require, sha256, timestamp,
)
from .knowledge import active_guidance, domain_sections, effective_guidance, validate_snapshot

CONTEXT_FIELDS = {
    "contract_version", "payload", "source_index", "finding_ids", "knowledge_version",
    "assessment_time", "source_manifest", "context_hash", "gaps", "purpose",
}
FINDING_FIELDS = {
    "finding_id", "reported_date", "equipment_id", "equipment_type", "inspection_type",
    "inspection_method", "finding_description", "reported_by", "reporter_role",
}
REGISTRY_FIELDS = {
    "equipment_id", "equipment_type", "service_description", "criticality_score",
    "reliability_score", "safety_critical_element", "redundancy", "engineer_comment",
}


def _managed_payload(snapshot: KnowledgeSnapshot, assessment_time: str) -> dict:
    candidate = snapshot.candidate
    if candidate["schema_version"] == 2:
        active, _ = effective_guidance(candidate, assessment_time)
        assessment_fields = {
            "title", "scope", "dimension", "guidance", "evidence_requirements",
            "uncertainty_guidance", "source_refs",
        }
        return {
            "rubric": candidate["rubric"],
            "guidance": {name: {key: value for key, value in candidate["guidance"][name].items()
                                if key in assessment_fields} for name in active},
            "active_guidance_ids": list(active),
            "authority": "Supplied domain notes remain authoritative. Managed guidance is reviewed, "
                         "not retired, effective at the explicit assessment time and not superseded. "
                         "Maintenance history is excluded; structural eligibility is not semantic certification.",
        }
    active = list(active_guidance(candidate))
    return {
        "rubric": candidate["rubric"],
        "guidance": {name: candidate["guidance"][name] for name in active},
        "active_guidance_ids": active,
        "superseded_guidance_ids": sorted(set(candidate["guidance"]) - set(active)),
        "authority": "Supplied domain notes remain authoritative. Only active managed guidance "
                     "is included. Superseded text is excluded from assessment context.",
    }


def _overlay_payload(overlay: EvaluationOverlay | None) -> dict | None:
    if overlay is None:
        return None
    checked = EvaluationOverlay(overlay.source_id, overlay.raw, overlay.expected_sha256)
    return {
        "source_id": checked.source_id, "sha256": checked.expected_sha256, **checked.data,
        "precedence": "ISOLATED EXPERIMENT ONLY: within the declared equipment/mechanism scope "
                      "and L/I dimension, this artificial guidance takes precedence over base "
                      "scoring guidance. Outside that scope use base guidance. Never override "
                      "source evidence, urgency/review rules, attempt limits or source selection.",
    }


def _source_manifest(selected: TableSource, registry: TableSource, snapshot: KnowledgeSnapshot,
                     overlay: EvaluationOverlay | None) -> list:
    result = [
        {"source_id": selected.source_id, "kind": selected.kind,
         "sha256": selected.raw_sha256, "version": None, "locator": selected.source_id},
        {"source_id": registry.source_id, "kind": registry.kind, "sha256": registry.raw_sha256,
         "version": None, "locator": registry.source_id},
        {"source_id": "domain", "kind": "supplied_domain", "sha256": sha256(snapshot.domain_bytes),
         "version": None, "locator": snapshot.candidate["domain_source"]["path"]},
        {"source_id": "managed", "kind": "managed_knowledge", "sha256": sha256(snapshot.release_bytes),
         "version": snapshot.knowledge_version, "locator": f"releases\\{snapshot.knowledge_version}.json"},
    ]
    if overlay is not None:
        result.append({"source_id": overlay.source_id, "kind": "evaluation_overlay",
                       "sha256": overlay.expected_sha256, "version": None, "locator": overlay.source_id})
    require(len({item["source_id"] for item in result}) == len(result), "context_manifest",
            "Logical source IDs must be unique, including reserved domain/managed sources.")
    return sorted(result, key=lambda x: x["source_id"])


def _source_index(payload: dict, findings_id: str, registry_id: str) -> dict:
    index = {}

    def add(address: str, source_id: str, text: str, location: list) -> None:
        require(address not in index, "context_index", "Duplicate source address.", address)
        index[address] = {"source_id": source_id, "text": text, "location": ["payload", *location]}

    for kind, table, source_id in (("finding", "findings", findings_id),
                                   ("equipment", "registry", registry_id)):
        for name, row in payload[table].items():
            for field, value in sorted(row.items()):
                add(f"{kind}:{name}:{field}", source_id, value, [table, name, field])
    for heading, text in payload["domain"]["sections"].items():
        add(f"domain:{heading}", "domain", text, ["domain", "sections", heading])
    for dimension in ("likelihood", "impact"):
        for number, band in enumerate(payload["managed_knowledge"]["rubric"][dimension]):
            add(f"knowledge:{band['band_id']}:description", "managed", band["description"],
                ["managed_knowledge", "rubric", dimension, number, "description"])
    for name, entry in sorted(payload["managed_knowledge"]["guidance"].items()):
        for field in ("title", "guidance", "uncertainty_guidance", "change_reason", "dimension"):
            if field not in entry:
                continue
            add(f"knowledge:{name}:{field}", "managed", entry[field],
                ["managed_knowledge", "guidance", name, field])
        for number, text in enumerate(entry["evidence_requirements"]):
            add(f"knowledge:{name}:evidence_requirements/{number}", "managed", text,
                ["managed_knowledge", "guidance", name, "evidence_requirements", number])
    overlay = payload["evaluation_overlay"]
    if overlay is not None:
        for field in ("scope", "dimension", "guidance"):
            add(f"overlay:{overlay['source_id']}:{field}", overlay["source_id"], overlay[field],
                ["evaluation_overlay", field])
    return dict(sorted(index.items()))


def _value(bundle: ContextBundle | dict) -> dict:
    data = bundle.to_dict() if isinstance(bundle, ContextBundle) else bundle
    require(isinstance(data, dict) and set(data) in
            (CONTEXT_FIELDS, CONTEXT_FIELDS - {"context_hash"}),
            "context_contract", "Unexpected ContextBundle fields.")
    require(type(data["contract_version"]) is int and data["contract_version"] == 1,
            "context_contract", "Unsupported context contract.")
    return data


def _checked_manifest(value: object) -> list:
    require(isinstance(value, list), "context_manifest", "Source manifest required.")
    for entry in value:
        fields(entry, {"source_id", "kind", "sha256", "version", "locator"}, "source_manifest")
        require(nonblank(entry["source_id"]) and nonblank(entry["kind"])
                and nonblank(entry["locator"]) and isinstance(entry["sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", entry["sha256"])
                and (entry["version"] is None or type(entry["version"]) in (str, int)),
                "context_manifest", "Invalid source manifest field values.")
    return value


def canonical_context_bytes(bundle: ContextBundle | dict) -> bytes:
    data = _value(bundle)
    projection = {key: value for key, value in data.items() if key != "context_hash"}
    manifest = []
    for entry in _checked_manifest(data["source_manifest"]):
        manifest.append({key: entry[key] for key in ("source_id", "kind", "version")})
    projection["source_manifest"] = sorted(manifest, key=lambda x: x["source_id"])
    return canonical_bytes(projection)


def serialize_context(bundle: ContextBundle | dict) -> bytes:
    data = _value(bundle)
    validate_bundle(data)
    require("context_hash" in data and data["context_hash"] == sha256(canonical_context_bytes(data)),
            "context_hash", "Context digest differs from its semantic content.")
    return canonical_bytes(data)


def _partner_gaps(findings: dict, registry: dict) -> list[dict]:
    result = []
    for name, row in sorted(registry.items()):
        match = re.fullmatch(r"(?:N\+1|Duplicated) \(([A-Z]+-\d{4})\)", row["redundancy"])
        affected = sorted(key for key, finding in findings.items() if finding["equipment_id"] == name)
        if match and match[1] not in registry and affected:
            result.append({"kind": "tagged_partner_not_in_registry", "subject_equipment_id": name,
                           "partner_equipment_id": match[1], "finding_ids": affected,
                           "source_refs": [f"equipment:{name}:redundancy"]})
    return result


def validate_bundle(bundle: ContextBundle | dict) -> None:
    data = _value(bundle)
    payload = fields(data["payload"], {
        "findings", "registry", "primary_equipment_by_finding", "domain",
        "managed_knowledge", "evaluation_overlay",
    }, "payload")
    findings, registry = payload["findings"], payload["registry"]
    require(isinstance(findings, dict) and findings and isinstance(registry, dict) and registry,
            "context_payload", "Finding and registry maps must be nonempty.")
    require(all(isinstance(row, dict) and row.get("finding_id") == name
                and set(row) == FINDING_FIELDS and all(nonblank(x) for x in row.values())
                for name, row in findings.items())
            and all(isinstance(row, dict) and row.get("equipment_id") == name
                    and set(row) == REGISTRY_FIELDS and all(nonblank(x) for x in row.values())
                    for name, row in registry.items()),
            "context_payload", "Invalid finding or registry source rows.")
    require(data["finding_ids"] == sorted(findings), "context_membership",
            "Finding membership is not canonical or differs from the payload.")
    require(payload["primary_equipment_by_finding"] ==
            {name: row.get("equipment_id") for name, row in findings.items() if isinstance(row, dict)}
            and len(payload["primary_equipment_by_finding"]) == len(findings)
            and all(value in registry for value in payload["primary_equipment_by_finding"].values()),
            "context_primary_mapping", "Primary equipment index differs from the selected rows.")
    manifest = _checked_manifest(data["source_manifest"])
    kinds = {item["kind"] for item in manifest}
    source_ids = {item["source_id"] for item in manifest}
    require(len(source_ids) == len(manifest), "context_manifest", "Source IDs must be unique.")
    require(kinds <= {"finding_input", "registry_input", "supplied_domain",
                      "managed_knowledge", "evaluation_input", "evaluation_overlay"},
            "context_manifest", "Unknown source kind.")
    by_kind = {}
    for item in manifest:
        by_kind.setdefault(item["kind"], []).append(item)
    finding_sources = by_kind.get("finding_input", []) + by_kind.get("evaluation_input", [])
    require(len(finding_sources) == len(by_kind.get("registry_input", [])) == 1
            and len(by_kind.get("supplied_domain", [])) == len(by_kind.get("managed_knowledge", [])) == 1,
            "context_manifest", "Exactly one finding, registry, domain and managed source is required.")
    domain = fields(payload["domain"], {"text", "sections"}, "payload.domain")
    require(isinstance(domain["text"], str) and domain["sections"] == domain_sections(domain["text"].encode("utf-8")),
            "context_domain", "Domain section view differs from its full source text.")
    require(by_kind["supplied_domain"][0]["sha256"] == sha256(domain["text"].encode("utf-8")),
            "context_domain", "Domain source hash differs from its text.")
    purpose = data["purpose"]
    require(isinstance(purpose, str) and purpose in {"normal", "evaluation_probe"},
            "context_purpose", "Unsupported context purpose.")
    if purpose == "normal":
        require(not kinds & {"evaluation_input", "evaluation_overlay"}
                and payload["evaluation_overlay"] is None,
                "context_purpose", "Evaluation content is forbidden in normal context.")
    else:
        require("evaluation_overlay" in kinds and isinstance(payload["evaluation_overlay"], dict),
                "context_purpose", "Isolated context must retain its declared overlay.")
    require(isinstance(data["source_index"], dict), "context_index", "Source index is required.")
    for address, item in data["source_index"].items():
        fields(item, {"source_id", "text", "location"}, f"source_index.{address}")
        require(isinstance(item["source_id"], str) and item["source_id"] in source_ids
                and isinstance(item["text"], str)
                and isinstance(item["location"], list) and item["location"]
                and item["location"][0] == "payload"
                and all(type(part) in (str, int) for part in item["location"]),
                "context_index", "Invalid source address metadata.", address)
        value = data
        try:
            for key in item["location"]:
                value = value[key]
        except (KeyError, IndexError, TypeError) as error:
            raise KnowledgeError("context_index", "Source address does not resolve.", address) from error
        require(value == item["text"], "context_index", "Source text differs from its address.", address)
    try:
        expected_index = _source_index(payload, finding_sources[0]["source_id"],
                                       by_kind["registry_input"][0]["source_id"])
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise KnowledgeError("context_payload", "Malformed knowledge or overlay payload.") from error
    require(data["source_index"] == expected_index, "context_index",
            "Source index is incomplete, foreign or differs from its payload.")
    require(isinstance(data["gaps"], list), "context_gap", "An explicit factual gap array is required.")
    require(data["gaps"] == _partner_gaps(findings, registry), "context_gap",
            "Factual gaps are missing, duplicated, unknown or inconsistent with the source.")
    timestamp(data["assessment_time"], "assessment_time")


def _rows(source: TableSource, key: str, required: set[str]) -> dict:
    rows = {}
    for row in source.rows:
        require(set(row) == required and all(nonblank(value) for value in row.values()), "context_input",
                "Missing, blank or extra source fields are not permitted.", key)
        require(row[key] not in rows, "context_duplicate", "Duplicate source identity.", row[key])
        rows[row[key]] = row
    return dict(sorted(rows.items()))


def verify_context(
    bundle: ContextBundle, snapshot: KnowledgeSnapshot, selected_findings: TableSource,
    registry: TableSource, assessment_time: str, *, purpose: str = "normal",
    overlay_ref: EvaluationOverlay | None = None,
) -> None:
    """Verify provenance against independently retained inputs, never a self-reported digest."""
    validate_snapshot(snapshot)
    serialize_context(bundle)
    data = bundle.to_dict()
    require(data["knowledge_version"] == snapshot.knowledge_version
            and data["assessment_time"] == assessment_time and data["purpose"] == purpose,
            "context_version", "Context release, cutoff or purpose differs from the requested run.")
    require(selected_findings.kind in {"finding_input", "evaluation_input"}
            and registry.kind == "registry_input", "context_input", "Incorrect source roles.")
    require((purpose == "normal" and overlay_ref is None and selected_findings.kind == "finding_input")
            or (purpose == "evaluation_probe" and isinstance(overlay_ref, EvaluationOverlay)),
            "context_purpose", "Context purpose is incompatible with its declared inputs.")
    require(data["payload"]["findings"] == _rows(selected_findings, "finding_id", FINDING_FIELDS)
            and data["payload"]["registry"] == _rows(registry, "equipment_id", REGISTRY_FIELDS),
            "context_input", "Context changed the independently selected source rows.")
    require(data["payload"]["domain"] == {
        "text": snapshot.domain_bytes.decode("utf-8"), "sections": domain_sections(snapshot.domain_bytes),
    } and data["payload"]["managed_knowledge"] == _managed_payload(snapshot, assessment_time)
            and data["payload"]["evaluation_overlay"] == _overlay_payload(overlay_ref),
            "context_knowledge", "Context knowledge differs from the pinned snapshot or overlay.")
    require(data["source_manifest"] == _source_manifest(selected_findings, registry, snapshot, overlay_ref),
            "context_manifest", "Context source provenance differs from the retained original bytes.")

def build_context(
    selected_findings: TableSource, registry: TableSource, snapshot: KnowledgeSnapshot,
    assessment_time: str, *, purpose: str = "normal", overlay_ref: EvaluationOverlay | None = None,
) -> ContextBundle:
    try:
        return _build_context(selected_findings, registry, snapshot, assessment_time,
                              purpose=purpose, overlay_ref=overlay_ref)
    except KnowledgeError as error:
        raise ContextError(error.code, str(error), error.field) from error


def _build_context(
    selected_findings: TableSource, registry: TableSource, snapshot: KnowledgeSnapshot,
    assessment_time: str, *, purpose: str, overlay_ref: EvaluationOverlay | None,
) -> ContextBundle:
    validate_snapshot(snapshot)
    cutoff = timestamp(assessment_time, "assessment_time")
    require(isinstance(selected_findings, TableSource) and isinstance(registry, TableSource),
            "context_input", "Original selected TableSource values are required.")
    require(selected_findings.kind in {"finding_input", "evaluation_input"}
            and registry.kind == "registry_input", "context_input", "Incorrect table source roles.")
    require(isinstance(purpose, str) and purpose in {"normal", "evaluation_probe"},
            "context_purpose", "Unsupported context purpose.")
    if purpose == "normal":
        require(overlay_ref is None and selected_findings.kind == "finding_input",
                "context_purpose", "Normal context cannot contain evaluation inputs or overlays.")
    else:
        require(isinstance(overlay_ref, EvaluationOverlay), "context_overlay",
                "Isolated probes require an explicit hash-bound overlay.")
        # Revalidate constructor invariants even if a caller bypassed the ordinary factory.
        overlay_ref = EvaluationOverlay(overlay_ref.source_id, overlay_ref.raw, overlay_ref.expected_sha256)
    findings = _rows(selected_findings, "finding_id", FINDING_FIELDS)
    equipment = _rows(registry, "equipment_id", REGISTRY_FIELDS)
    primary = {}
    for name, row in findings.items():
        require(re.fullmatch(r"F-\d{4}", name), "context_input", "Invalid finding identity.", name)
        partner = row["equipment_id"]
        require(partner in equipment and row["equipment_type"] == equipment[partner]["equipment_type"],
                "context_primary_mapping", "Primary equipment is absent or has a different type.", name)
        try:
            observed = date.fromisoformat(row["reported_date"])
        except ValueError as error:
            raise KnowledgeError("context_date", "Invalid finding observation date.", name) from error
        require(observed <= cutoff.date(), "context_date",
                "A selected finding is later than the assessment cutoff.", name)
        primary[name] = partner
    sections = domain_sections(snapshot.domain_bytes)
    payload = {
        "findings": findings, "registry": equipment,
        "primary_equipment_by_finding": primary,
        "domain": {"text": snapshot.domain_bytes.decode("utf-8"), "sections": sections},
        "managed_knowledge": _managed_payload(snapshot, assessment_time),
        "evaluation_overlay": _overlay_payload(overlay_ref),
    }
    data = {
        "contract_version": 1, "payload": payload,
        "source_index": _source_index(payload, selected_findings.source_id, registry.source_id),
        "finding_ids": sorted(findings), "knowledge_version": snapshot.knowledge_version,
        "assessment_time": assessment_time,
        "source_manifest": _source_manifest(selected_findings, registry, snapshot, overlay_ref),
        "gaps": _partner_gaps(findings, equipment), "purpose": purpose,
    }
    data["context_hash"] = sha256(canonical_context_bytes(data))
    return ContextBundle(serialize_context(data))
