from __future__ import annotations

from dataclasses import dataclass
import json

from .contracts import (
    ContextBundle, EvaluationOverlay, KnowledgeSnapshot, TableSource,
    canonical_bytes, require, sha256, strict_json,
)
from .context import verify_context
from .knowledge import domain_sections


def _wire(value: object) -> str:
    # This provisional consumer predates the version-1 UTF-8 compact serializer.
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class WorkflowExport:
    encoded: bytes

    def read_export(self) -> dict:
        return strict_json(self.encoded)

    @classmethod
    def from_bundle(
        cls, snapshot: KnowledgeSnapshot, bundle: ContextBundle, selected_findings: TableSource,
        registry: TableSource, assessment_time: str, *, purpose: str = "normal",
        overlay_ref: EvaluationOverlay | None = None,
    ) -> WorkflowExport:
        verify_context(bundle, snapshot, selected_findings, registry, assessment_time,
                       purpose=purpose, overlay_ref=overlay_ref)
        original = bundle.to_dict()
        expected_managed = original["payload"]["managed_knowledge"]
        knowledge = {
            "domain:source": snapshot.domain_bytes.decode("utf-8"),
            **{f"domain:{name}": text for name, text in domain_sections(snapshot.domain_bytes).items()},
            "knowledge:managed": _wire(expected_managed),
        }
        for address, item in original["source_index"].items():
            if address.startswith("knowledge:"):
                location = item["location"]
                value = original
                for part in location:
                    value = value[part]
                require(value == item["text"] and item["source_id"] == "managed",
                        "context_index", "Managed source address does not match the payload.")
                knowledge[address] = value
        knowledge_manifest = [
            {"source_id": key, "kind": "supplied_domain" if key.startswith("domain:") else "managed_knowledge",
             "sha256": sha256(value.encode("utf-8"))} for key, value in sorted(knowledge.items())
        ]
        pinned = {
            "knowledge_version": snapshot.knowledge_version, "content": knowledge,
            "content_hash": sha256(_wire(knowledge).encode()),
            "source_manifest": knowledge_manifest, "approved": True,
        }
        finding_sources = [item for item in original["source_manifest"]
                           if item["kind"] in {"finding_input", "evaluation_input"}]
        registry_sources = [item for item in original["source_manifest"] if item["kind"] == "registry_input"]
        require(len(finding_sources) == len(registry_sources) == 1, "context_manifest",
                "The provisional workflow accepts one selected CSV and one registry.")
        manifest = [
            {"source_id": "findings", "kind": finding_sources[0]["kind"],
             "sha256": finding_sources[0]["sha256"]},
            {"source_id": "registry", "kind": "registry_input", "sha256": registry_sources[0]["sha256"]},
            *knowledge_manifest,
        ]
        overlay = original["payload"]["evaluation_overlay"]
        if original["purpose"] == "normal":
            require(overlay is None and finding_sources[0]["kind"] == "finding_input",
                    "context_purpose", "Normal exports cannot contain evaluation sources.")
        else:
            require(original["purpose"] == "evaluation_probe" and isinstance(overlay, dict),
                    "context_purpose", "An isolated export requires its explicit overlay.")
            # Keep the complete scoped instruction; the driver must independently pin this projection.
            overlay_text = _wire(overlay)
            knowledge = {**knowledge, overlay["source_id"]: overlay_text}
            manifest.append({"source_id": overlay["source_id"], "kind": "evaluation_overlay",
                             "sha256": sha256(overlay_text.encode())})
        payload = {"findings": original["payload"]["findings"],
                   "registry": original["payload"]["registry"], "knowledge": knowledge}
        index = {
            address: item["text"] for address, item in original["source_index"].items()
            if address.startswith(("finding:", "equipment:"))
        }
        index.update(knowledge)
        projected = {
            "contract_version": "triage-export-v0", "payload": payload, "source_index": index,
            "finding_ids": original["finding_ids"], "knowledge_version": snapshot.knowledge_version,
            "assessment_time": original["assessment_time"], "source_manifest": manifest,
            "purpose": "normal" if original["purpose"] == "normal" else "isolated_probe",
            "gaps": original["gaps"],
        }
        projected["context_hash"] = sha256(_wire({
            key: value for key, value in projected.items() if key != "source_manifest"
        }).encode())
        return cls(canonical_bytes({"snapshot": pinned, "bundle": projected}))

    @property
    def overlay_ref(self) -> dict | None:
        data = self.read_export()
        bundle = data["bundle"]
        if bundle["purpose"] == "normal":
            return None
        entry = next(item for item in bundle["source_manifest"] if item["kind"] == "evaluation_overlay")
        kind = next(item["kind"] for item in bundle["source_manifest"] if item["source_id"] == "findings")
        return {**{key: entry[key] for key in ("source_id", "sha256")},
                "text": bundle["payload"]["knowledge"][entry["source_id"]], "input_kind": kind}
