from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from llm_inference.contracts import canonical, strict_json

from .contracts import TriageError, digest, json_copy, nonblank, require, sha256_value, timestamp

FINDING_FIELDS = (
    "finding_id", "reported_date", "equipment_id", "equipment_type", "inspection_type",
    "inspection_method", "finding_description", "reported_by", "reporter_role",
)
EQUIPMENT_FIELDS = (
    "equipment_id", "equipment_type", "service_description", "criticality_score",
    "reliability_score", "safety_critical_element", "redundancy", "engineer_comment",
)
CONTEXT_FIELDS = {
    "contract_version", "payload", "source_index", "finding_ids", "knowledge_version",
    "assessment_time", "source_manifest", "context_hash", "gaps", "purpose",
}
SEMANTIC_FIELDS = CONTEXT_FIELDS - {"source_manifest", "context_hash"}
KINDS = {
    "finding_input", "registry_input", "supplied_domain", "managed_knowledge",
    "evaluation_input", "evaluation_overlay",
}


@dataclass(frozen=True)
class Inputs:
    encoded: str
    findings_hash: str
    registry_hash: str
    findings_raw: bytes
    registry_raw: bytes

    @property
    def data(self) -> dict:
        return strict_json(self.encoded)


class ContextExport(Protocol):
    """Provisional export seam, not the knowledge module's proposed headless API."""

    def read_export(self) -> dict: ...


def read_inputs(findings_path: Path, registry_path: Path) -> Inputs:
    def load(path: Path, fields: tuple[str, ...]) -> tuple[dict, bytes]:
        raw = path.read_bytes()
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        require(reader.fieldnames == list(fields), "input_header", "Unexpected CSV header")
        rows = {}
        for row in reader:
            require(set(row) == set(fields) and all(nonblank(x) for x in row.values()),
                    "input_cell", "Missing, extra or blank CSV cell")
            identifier = row[fields[0]]
            require(identifier not in rows, "input_duplicate", "Duplicate CSV primary key")
            rows[identifier] = row
        require(rows, "input_empty", "Input CSV is empty")
        return rows, raw

    findings, findings_raw = load(findings_path, FINDING_FIELDS)
    registry, registry_raw = load(registry_path, EQUIPMENT_FIELDS)
    validate_rows(findings, registry)
    return Inputs(canonical({"findings": findings, "registry": registry}),
                  digest(findings_raw), digest(registry_raw), findings_raw, registry_raw)


def missing_partner_gaps(data: dict) -> list[dict]:
    gaps = []
    for identifier, row in sorted(data["registry"].items()):
        affected = sorted(k for k, v in data["findings"].items() if v["equipment_id"] == identifier)
        for partner in re.findall(r"^(?:N\+1|Duplicated) \(([A-Z]+-\d{4})\)$", row["redundancy"]):
            if partner not in data["registry"] and affected:
                gaps.append({
                    "kind": "tagged_partner_not_in_registry", "subject_equipment_id": identifier,
                    "partner_equipment_id": partner, "finding_ids": affected,
                    "source_refs": [f"equipment:{identifier}:redundancy"],
                })
    return gaps


def validate_rows(findings: dict, registry: dict) -> None:
    require(isinstance(findings, dict) and findings and isinstance(registry, dict) and registry,
            "input_shape", "Nonempty finding and registry maps required")
    for identifier, row in registry.items():
        require(isinstance(row, dict) and set(row) == set(EQUIPMENT_FIELDS)
                and all(nonblank(x) for x in row.values())
                and identifier == row["equipment_id"]
                and re.fullmatch(r"[A-Z]+-\d{4}", identifier),
                "input_equipment", "Invalid equipment identity or fields")
        require(row["safety_critical_element"] in {"Yes", "No"}, "input_sce", "Invalid SCE flag")
        for name in ("criticality_score", "reliability_score"):
            require(re.fullmatch(r"(?:[1-9]|10)", row[name]),
                    "input_prior", "Registry prior must be 1-10")
    for identifier, row in findings.items():
        require(isinstance(row, dict) and set(row) == set(FINDING_FIELDS)
                and all(nonblank(x) for x in row.values())
                and identifier == row["finding_id"] and re.fullmatch(r"F-\d{4}", identifier),
                "input_finding", "Invalid finding identity or fields")
        require(row["equipment_id"] in registry, "input_mapping", "Primary equipment missing")
        require(row["equipment_type"] == registry[row["equipment_id"]]["equipment_type"],
                "input_mapping", "Equipment type mismatch")
        try:
            require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["reported_date"]),
                    "input_date", "Invalid report date")
            date.fromisoformat(row["reported_date"])
        except ValueError as error:
            raise TriageError("input_date", "Invalid report date") from error


def context_body(bundle: dict) -> str:
    """Consumer wire contract; this validates/serializes, never constructs context."""
    return canonical({name: bundle[name] for name in sorted(SEMANTIC_FIELDS)})


def validate_context(
    source: ContextExport, inputs: Inputs, version: str, assessment_time: str,
    max_bytes: int, *, purpose: str = "normal", overlay_ref: dict | None = None,
) -> tuple[dict, str, dict]:
    try:
        return _validate_context(source, inputs, version, assessment_time, max_bytes,
                                 purpose=purpose, overlay_ref=overlay_ref)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise TriageError("context_contract", "Malformed context dependency result") from error


def _validate_context(
    source: ContextExport, inputs: Inputs, version: str, assessment_time: str,
    max_bytes: int, *, purpose: str, overlay_ref: dict | None,
) -> tuple[dict, str, dict]:
    data = inputs.data
    cutoff = timestamp(assessment_time)
    require(all(date.fromisoformat(row["reported_date"]) <= cutoff.date()
                for row in data["findings"].values()),
            "assessment_time", "A finding is later than the assessment cutoff")
    export = json_copy(source.read_export())
    require(isinstance(export, dict) and set(export) == {"snapshot", "bundle"},
            "context_export", "Expected provisional snapshot/bundle export")
    snapshot = export["snapshot"]
    require(isinstance(snapshot, dict) and set(snapshot) ==
            {"knowledge_version", "content", "content_hash", "source_manifest", "approved"},
            "knowledge_contract", "Invalid knowledge snapshot")
    require(snapshot["approved"] is True and snapshot["knowledge_version"] == version
            and isinstance(snapshot["content"], dict) and snapshot["content"],
            "knowledge_version", "Approved exact knowledge release required")
    require(digest(canonical(snapshot["content"]).encode()) == snapshot["content_hash"],
            "knowledge_hash", "Knowledge snapshot content hash mismatch")
    bundle = export["bundle"]
    require(isinstance(bundle, dict) and set(bundle) == CONTEXT_FIELDS
            and bundle["contract_version"] == "triage-export-v0",
            "context_contract", "Unsupported context contract")
    require(bundle["knowledge_version"] == version
            and bundle["assessment_time"] == assessment_time,
            "context_version", "Context release or cutoff changed")
    require(isinstance(bundle["finding_ids"], list)
            and all(isinstance(x, str) for x in bundle["finding_ids"])
            and len(bundle["finding_ids"]) == len(data["findings"])
            and set(bundle["finding_ids"]) == set(data["findings"]),
            "context_membership", "Context finding membership differs")
    require(isinstance(bundle["payload"], dict)
            and set(bundle["payload"]) == {"findings", "registry", "knowledge"}
            and bundle["payload"]["findings"] == data["findings"]
            and bundle["payload"]["registry"] == data["registry"],
            "context_payload", "Context changed selected source rows")
    knowledge = bundle["payload"]["knowledge"]
    require(isinstance(knowledge, dict)
            and all(nonblank(k) and nonblank(v) for k, v in knowledge.items()),
            "context_payload", "Knowledge sources must be nonempty text")
    require(purpose in {"normal", "isolated_probe"} and bundle["purpose"] == purpose,
            "context_purpose", "Context purpose mismatch")
    expected_manifest = [
        {"source_id": "findings", "kind": "finding_input", "sha256": inputs.findings_hash},
        {"source_id": "registry", "kind": "registry_input", "sha256": inputs.registry_hash},
    ]
    require(isinstance(snapshot["source_manifest"], list)
            and isinstance(bundle["source_manifest"], list),
            "context_manifest", "Source manifest required")
    expected_manifest.extend(snapshot["source_manifest"])
    expected_knowledge = dict(snapshot["content"])
    if purpose == "isolated_probe":
        require(isinstance(overlay_ref, dict) and set(overlay_ref) ==
                {"source_id", "sha256", "text", "input_kind"}
                and nonblank(overlay_ref["source_id"]) and nonblank(overlay_ref["text"])
                and digest(overlay_ref["text"].encode()) == overlay_ref["sha256"]
                and overlay_ref["input_kind"] in {"finding_input", "evaluation_input"},
                "context_overlay", "Declared experiment overlay/hash required")
        expected_manifest[0]["kind"] = overlay_ref["input_kind"]
        expected_manifest.append({"source_id": overlay_ref["source_id"],
                                  "sha256": overlay_ref["sha256"],
                                  "kind": "evaluation_overlay"})
        expected_knowledge[overlay_ref["source_id"]] = overlay_ref["text"]
    else:
        require(overlay_ref is None, "context_overlay", "Normal runs cannot load overlays")
    require(knowledge == expected_knowledge, "context_payload", "Undeclared knowledge content")
    manifest = bundle["source_manifest"]
    for item in manifest:
        require(isinstance(item, dict) and set(item) == {"source_id", "kind", "sha256"}
                and nonblank(item["source_id"]) and item["kind"] in KINDS
                and sha256_value(item["sha256"]),
                "context_manifest", "Invalid source manifest entry")
        if purpose == "normal":
            require(not item["kind"].startswith("evaluation_"),
                    "context_overlay", "Evaluation sources in normal context")
    require(len({x["source_id"] for x in manifest}) == len(manifest)
            and sorted(manifest, key=canonical) == sorted(expected_manifest, key=canonical),
            "context_manifest", "Context sources do not match pinned manifests")
    for entry in snapshot["source_manifest"]:
        require(entry["source_id"] in snapshot["content"]
                and entry["kind"] in {"supplied_domain", "managed_knowledge"}
                and digest(snapshot["content"][entry["source_id"]].encode()) == entry["sha256"],
                "knowledge_manifest", "Knowledge source content differs from manifest")
    require({x["source_id"] for x in snapshot["source_manifest"]} == set(snapshot["content"]),
            "knowledge_manifest", "Incomplete knowledge manifest")
    index = bundle["source_index"]
    require(isinstance(index, dict), "context_index", "Source index required")
    expected_refs = set(knowledge)
    for kind, rows in (("finding", data["findings"]), ("equipment", data["registry"])):
        for identifier, row in rows.items():
            for name, value in row.items():
                address = f"{kind}:{identifier}:{name}"
                expected_refs.add(address)
                require(index.get(address) == value, "context_index", "Source field differs")
    require(set(index) == expected_refs and all(index.get(k) == v for k, v in knowledge.items()),
            "context_index", "Incomplete or foreign source index")
    require(isinstance(bundle["gaps"], list), "context_gap", "Gap array required")
    expected_gaps = {(gap["subject_equipment_id"], gap["partner_equipment_id"])
                     for gap in missing_partner_gaps(data)}
    seen_gaps = set()
    for gap in bundle["gaps"]:
        require(isinstance(gap, dict) and set(gap) ==
                {"kind", "subject_equipment_id", "partner_equipment_id", "finding_ids", "source_refs"}
                and gap["kind"] == "tagged_partner_not_in_registry",
                "context_gap", "Unknown or invalid gap")
        pair = (gap["subject_equipment_id"], gap["partner_equipment_id"])
        require(pair in expected_gaps and pair not in seen_gaps, "context_gap", "Invalid gap subject")
        affected = sorted(k for k, v in data["findings"].items() if v["equipment_id"] == pair[0])
        require(gap["finding_ids"] == affected
                and gap["source_refs"] == [f"equipment:{pair[0]}:redundancy"],
                "context_gap", "Gap membership or source differs")
        seen_gaps.add(pair)
    require(seen_gaps == expected_gaps, "context_gap", "Required missing-partner gap omitted")
    serialized = context_body(bundle)
    require(digest(serialized.encode()) == bundle["context_hash"],
            "context_hash", "Context hash mismatch")
    require(type(max_bytes) is int and max_bytes > 0 and len(serialized.encode()) <= max_bytes,
            "context_limit", "Context exceeds byte budget")
    return bundle, serialized, snapshot


class ExportedContext:
    """Unauthenticated provisional export, NOT document 06's knowledge API."""

    def __init__(self, path: Path):
        raw = path.read_bytes()
        self.raw_sha256 = digest(raw)
        export = strict_json(raw.decode("utf-8"))
        require(isinstance(export, dict) and set(export) == {"snapshot", "bundle"},
                "context_export", "Expected snapshot/bundle export")
        self._encoded = canonical(export)

    def read_export(self) -> dict:
        return strict_json(self._encoded)
