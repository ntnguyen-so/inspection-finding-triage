"""Deterministic active-only retrieval over independently bound CSV snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType

from .contracts import (KnowledgeError, TableSource, canonical_bytes, fields, identifier, nonblank,
                        require, sha256, strict_json, timestamp)


FINDING_FIELDS = {
    "finding_id", "reported_date", "equipment_id", "equipment_type", "inspection_type",
    "inspection_method", "finding_description", "reported_by", "reporter_role",
}
REGISTRY_FIELDS = {
    "equipment_id", "equipment_type", "service_description", "criticality_score",
    "reliability_score", "safety_critical_element", "redundancy", "engineer_comment",
}
ERROR_CODES = frozenset({
    "invalid_query", "input_binding_mismatch", "unsupported_contract",
    "unknown_or_invalid_release", "strategy_binding_mismatch", "knowledge_gap",
    "invalid_dependency", "result_too_large",
})
PARAMETERS = {
    "version": "source-selector-v1",
    "scope": "casefold-exact", "lexical": "disabled", "general": "always",
    "closure": "bidirectional", "unknown": "all-active", "overflow": "failure-only",
    "ordering": "address-ascending", "type_scope": "registry-type-vocabulary",
    "source_context": "c0-heading-source-context-v2",
}


def _copy(value):
    return strict_json(canonical_bytes(value))


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def strategy_binding():
    # Actual executable bytes, not a manually maintained label alone.
    implementation = {name: sha256(Path(__file__).with_name(name).read_bytes())
                      for name in ("retrieval.py", "source_store.py", "source.py", "contracts.py")}
    return {"strategy": "source-selector-v1",
            "implementation_sha256": sha256(canonical_bytes(implementation)),
            "implementation_files": implementation,
            "parameters": _copy(PARAMETERS),
            "parameters_sha256": sha256(canonical_bytes(PARAMETERS))}


def _row_map(rows, key, required):
    result = {}
    require(isinstance(rows, list) and rows, "invalid_query", "Nonempty input rows required.")
    for row in rows:
        fields(row, required, key)
        require(all(isinstance(v, str) for v in row.values()) and nonblank(row[key]),
                "invalid_query", "CSV values must be strings with nonempty IDs.")
        require(row[key] not in result, "invalid_query", "Duplicate CSV primary key.")
        result[row[key]] = row
    return result


def _validate_query(query):
    fields(query, {"findings", "registry"}, "query_context")
    require(isinstance(query["findings"], dict) and isinstance(query["registry"], dict),
            "invalid_query", "Findings and registry must be ID-keyed maps.")
    findings = _row_map(list(query["findings"].values()), "finding_id", FINDING_FIELDS)
    registry = _row_map(list(query["registry"].values()), "equipment_id", REGISTRY_FIELDS)
    require(findings == query["findings"] and registry == query["registry"],
            "invalid_query", "Map keys must equal row IDs.")
    for row in registry.values():
        require(all(row[k].isdigit() and 1 <= int(row[k]) <= 10
                    for k in ("criticality_score", "reliability_score"))
                and row["safety_critical_element"] in ("Yes", "No"),
                "invalid_query", "Registry scores or safety-critical marker are invalid.")
    for row in findings.values():
        try:
            require(date.fromisoformat(row["reported_date"]).isoformat() == row["reported_date"],
                    "invalid_query", "Canonical ISO reported_date required.")
        except ValueError as error:
            raise KnowledgeError("invalid_query", "Invalid reported_date.") from error
        require(nonblank(row["finding_description"]), "invalid_query", "Finding description is required.")
        equipment = registry.get(row["equipment_id"])
        require(equipment is not None and row["equipment_type"] == equipment["equipment_type"],
                "invalid_query", "Finding-to-registry equipment join/type mismatch.")
    return findings, registry


@dataclass(frozen=True)
class InputBinding:
    _encoded: bytes

    @property
    def findings(self):
        return _freeze(strict_json(self._encoded)["findings"])

    @property
    def registry(self):
        return _freeze(strict_json(self._encoded)["registry"])

    @property
    def manifest(self):
        return _freeze(strict_json(self._encoded)["manifest"])

    def to_dict(self):
        return strict_json(self._encoded)


def binding_from_tables(findings: TableSource, registry: TableSource, *,
                        input_purpose: str = "normal"):
    """Bind independent CSV bytes; evaluation inputs require explicit probe purpose."""
    require(input_purpose in ("normal", "isolated_probe"), "input_binding_mismatch",
            "An explicit supported input purpose is required.")
    finding_kinds = (("finding_input", "evaluation_input")
                     if input_purpose == "isolated_probe" else ("finding_input",))
    require(isinstance(findings, TableSource) and isinstance(registry, TableSource)
            and findings.kind in finding_kinds and registry.kind == "registry_input"
            and findings.source_id != registry.source_id,
            "input_binding_mismatch", "Distinct authorized findings and registry tables required.")
    frows = _row_map(findings.rows, "finding_id", FINDING_FIELDS)
    rrows = _row_map(registry.rows, "equipment_id", REGISTRY_FIELDS)
    _validate_query({"findings": frows, "registry": rrows})
    manifest = [{"source_id": table.source_id, "kind": table.kind,
                 "raw_sha256": table.raw_sha256, "bytes": len(table.raw)}
                for table in (findings, registry)]
    body = {"findings": frows, "registry": rrows, "manifest": manifest}
    if input_purpose == "isolated_probe":
        body["input_purpose"] = input_purpose
    return InputBinding(canonical_bytes(body))


def _checked_binding(binding, input_purpose):
    require(input_purpose in ("normal", "isolated_probe"), "input_binding_mismatch",
            "An explicit supported input purpose is required.")
    require(isinstance(binding, InputBinding), "input_binding_mismatch",
            "Use an independently constructed InputBinding.")
    names = {"findings", "registry", "manifest"}
    if input_purpose == "isolated_probe":
        names.add("input_purpose")
    allowed = fields(binding.to_dict(), names, "input_binding")
    if input_purpose == "isolated_probe":
        require(allowed["input_purpose"] == input_purpose, "input_binding_mismatch",
                "Input binding differs from the trusted purpose.")
    _validate_query({"findings": allowed["findings"], "registry": allowed["registry"]})
    manifest = allowed["manifest"]
    require(isinstance(manifest, list) and len(manifest) == 2, "input_binding_mismatch",
            "Distinct findings and registry manifests are required.")
    finding_kinds = (("finding_input", "evaluation_input")
                     if input_purpose == "isolated_probe" else ("finding_input",))
    for entry, kinds in zip(manifest, (finding_kinds, ("registry_input",))):
        fields(entry, {"source_id", "kind", "raw_sha256", "bytes"}, "input_manifest")
        require(identifier(entry["source_id"]) and entry["kind"] in kinds
                and isinstance(entry["raw_sha256"], str) and len(entry["raw_sha256"]) == 64
                and all(char in "0123456789abcdef" for char in entry["raw_sha256"])
                and type(entry["bytes"]) is int and entry["bytes"] > 0,
                "input_binding_mismatch", "Invalid authorized input manifest.")
    require(manifest[0]["source_id"] != manifest[1]["source_id"],
            "input_binding_mismatch", "Input source IDs must be distinct.")
    return allowed


@dataclass(frozen=True)
class KnowledgeResult:
    _encoded: bytes
    _evidence: bytes

    def to_dict(self):
        return strict_json(self._encoded)

    def provider_payload(self):
        result = self.to_dict()
        return {address: entry["text"] for address, entry in result["entries"].items()}

    @property
    def evidence(self):
        return strict_json(self._evidence)

    @property
    def status(self):
        return self.to_dict()["status"]

    @property
    def error_code(self):
        return self.to_dict()["error_code"]

    @property
    def error(self):
        return self.error_code


def _result(base, *, status, error_code=None, entries=None, mode=None, index=None, evidence=None):
    record = {**base, "contract": "triage-knowledge-result-v1", "status": status,
              "error_code": error_code, "selection_mode": mode, "entries": entries or {},
              "source_index": index or {}}
    record["content_sha256"] = sha256(canonical_bytes(record))
    return KnowledgeResult(canonical_bytes(record), canonical_bytes(evidence or {}))


def get_triage_knowledge(store, query_context, *, knowledge_version, assessment_time,
                        expected_strategy, allowed_input_binding, max_bytes,
                        input_purpose: str = "normal"):
    """Retrieve source-faithful knowledge with purpose supplied by the trusted caller."""
    base = {"knowledge_version": knowledge_version if isinstance(knowledge_version, str) else None,
            "assessment_time": None, "query_sha256": None, "strategy": strategy_binding(),
            "retrieval_index_sha256": None}
    evidence = {}
    def fail(code, detail):
        return _result(base, status="unavailable", error_code=code,
                       evidence={**evidence, "diagnostic": detail})
    try:
        cutoff = timestamp(assessment_time, "assessment_time")
        base["assessment_time"] = cutoff.isoformat()
        require(type(max_bytes) is int and max_bytes > 0, "invalid_query",
                "max_bytes must be a positive integer.")
        query = _copy(query_context)
        findings, registry = _validate_query(query)
        base["query_sha256"] = sha256(canonical_bytes(query))
    except (KnowledgeError, ValueError, TypeError, UnicodeError, OverflowError) as error:
        return fail("invalid_query", str(error))
    try:
        allowed = _checked_binding(allowed_input_binding, input_purpose)
    except (KnowledgeError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as error:
        return fail("input_binding_mismatch", str(error))
    if (registry != allowed["registry"]
            or any(name not in allowed["findings"] or row != allowed["findings"][name]
                   for name, row in findings.items())):
        return fail("input_binding_mismatch", "Actual query rows differ from authorized snapshots.")
    if input_purpose == "isolated_probe":
        base["input_purpose"] = input_purpose
        evidence["input_purpose"] = input_purpose
    evidence["authorized_input_manifest"] = allowed["manifest"]
    evidence["authorized_input_manifest_sha256"] = sha256(canonical_bytes(allowed["manifest"]))
    if expected_strategy != base["strategy"]:
        return fail("strategy_binding_mismatch", "Executable selector or parameters differ from pin.")
    try:
        release = store.resolve_release(knowledge_version)
        candidate = release["candidate"]
    except KnowledgeError as error:
        if error.code == "unsupported_contract":
            return fail("unsupported_contract", "Unsupported source contract.")
        if error.code == "invalid_dependency":
            return fail("invalid_dependency", "Invalid release context dependency.")
        return fail("unknown_or_invalid_release", "Release validation failed.")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return fail("unknown_or_invalid_release", "Release not available or invalid.")
    try:
        store.validate_dependencies(candidate, assessment_time=base["assessment_time"])
    except (KnowledgeError, OSError, ValueError, TypeError, KeyError):
        return fail("invalid_dependency", "Known context dependency is inactive or invalid.")
    items = candidate["items"]
    index = {item_id: {
        "revision_id": item["revision_id"], "review_state": item["review_state"],
        **{key: item["revision"][key] for key in
           ("source_id", "source_sha256", "spans", "scopes", "aliases",
            "status", "effective_from", "effective_until")},
    } for item_id, item in items.items()}
    base["retrieval_index_sha256"] = sha256(canonical_bytes({
        "items": index, "context_links": candidate["context_links"],
        "replacements": candidate["replacements"],
    }))
    active = {i: item for i, item in items.items()
              if store.eligible(candidate, i, base["assessment_time"])}
    if not active:
        return fail("knowledge_gap", "Pinned release has no eligible knowledge at the cutoff.")
    subject_types = {row["equipment_type"].casefold() for row in findings.values()}
    known_types = {row["equipment_type"].casefold() for row in registry.values()
                   if row["equipment_type"].strip()}
    scoped = {i: v for i, v in active.items() if v["revision"]["scopes"]}
    labels = {i: {x.casefold() for x in item["revision"]["scopes"] + item["revision"]["aliases"]}
              for i, item in scoped.items()}
    matched = {i for i, values in labels.items() if values.intersection(subject_types)}
    recognized = set().union(*labels.values()) if labels else set()
    safe_narrow = (bool(scoped) and all(t and t in recognized for t in subject_types)
                   and bool(matched)
                   and all(values.intersection(known_types) for values in labels.values())
                   and all(item["review_state"] == "reviewed" for item in active.values()))
    if safe_narrow:
        mode = "scoped"
        selected = {i for i in active if i not in scoped} | matched
    else:
        mode, selected = "conservative_expansion", set(active)
    before_closure = set(selected)
    edges = [tuple(edge[k].split("@")[0] for k in ("from", "to"))
             for edge in candidate["context_links"]]
    changed = True
    while changed:
        before = len(selected)
        for left, right in edges:
            if left in selected or right in selected:
                selected.update((left, right))
        changed = len(selected) != before
    conservative_edges = [edge for edge in candidate["context_links"]
                          if edge.get("kind") == "conservative_source_context"
                          and any(edge[key].split("@")[0] in selected for key in ("from", "to"))]
    if safe_narrow and conservative_edges:
        mode = "conservative_expansion"
    entries, source_index = {}, {}
    for item_id in sorted(selected):
        item = active[item_id]
        rev = item["revision"]
        address = f"knowledge:{item_id}@{item['revision_id']}:text"
        entry = {key: rev[key] for key in
                 ("source_id", "source_sha256", "spans", "text", "scopes", "aliases")}
        entries[address] = entry
        source_index[address] = {key: entry[key] for key in
                                 ("source_id", "source_sha256", "spans")}
    evidence.update(selected_item_ids=sorted(selected), excluded_item_ids=sorted(set(items) - selected),
                    conservative_expansion=mode == "conservative_expansion",
                    expansion_reason=("conservative_source_context" if safe_narrow and conservative_edges
                                      else "unrecognized_or_incomplete_type_scope" if not safe_narrow
                                      else None),
                    conservative_source_context_edges=len(conservative_edges),
                    context_added_item_ids=sorted(selected - before_closure))
    result = _result(base, status="ok", entries=entries, mode=mode,
                     index=source_index, evidence=evidence)
    if len(canonical_bytes(result.provider_payload())) > max_bytes:
        return fail("result_too_large", "Complete provider projection exceeds max_bytes.")
    return result
