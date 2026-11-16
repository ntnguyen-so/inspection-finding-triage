"""Author and verify a frozen synthetic registry fixture, never production metadata.

python -B -m eval.knowledge_query_inputs --write

The explicit authoring step uses only the eight synthetic source documents'
literal Scope:/Equipment: fields and declared query inputs. Loading verifies the
fixed artifact; it never learns vocabulary from candidate outputs or grading.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from triage_knowledge.source import SourceDocument

from .knowledge_eval import ROOT, canonical_hash, read_json


FIXTURE_PATH = Path("eval") / "data" / "knowledge_extraction" / "registry.json"
MISSING_SUBJECT = "Unrecognized synthetic subject"
CONSTRUCTION = (
    "Fixture authoring only: literal whole-line Scope:/Equipment: declarations "
    "outside fences in the eight unchanged synthetic sources, plus declared "
    "query input types. Source-authored scope labels ARE used; this inventory is "
    "NOT independent of source authorship. Reference access supplies only query "
    "IDs and subject_types, never rule-to-scope, atom or expected-answer assignments. "
    "No original domain or model output. Empty query type lists retain the existing "
    "missing-type sentinel. Shared all-family vocabulary exposure is NOT blind. "
    "Vocabulary coverage does NOT qualify semantic quality, field/domain knowledge "
    "or type safety: raw critical extraction grades and per-case recall must still pass."
)


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def author_registry(sources: Mapping[str, bytes], query_inputs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Pure authoring transform with source-byte or query-field provenance."""
    inventory: dict[str, list[dict[str, Any]]] = {}
    source_hashes, queries = {}, {}

    def add(label, evidence):
        inventory.setdefault(label, []).append(evidence)

    for sid, raw in sorted(sources.items()):
        if sid == "original_domain":
            raise ValueError("The original domain is not a synthetic registry authoring input")
        document = SourceDocument.from_bytes(raw, name=sid, source_id=sid)
        source_hashes[sid] = document.source_sha256
        fence = None
        for unit in document.units:
            line = unit["text"].lstrip("\ufeff")
            # Same literal-field/fence grammar as C0, without a heading requirement.
            marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)", line)
            if marker:
                run, tail = marker.groups()
                if fence is None:
                    fence = (run[0], len(run))
                elif run[0] == fence[0] and len(run) >= fence[1] and not tail.strip():
                    fence = None
                continue
            if fence is not None:
                continue
            match = re.fullmatch(r"[ \t]*(Scope|Equipment):[ \t]*([^\r\n]+?)[ \t]*(?:\r?\n)?", line)
            if match and match.group(2).strip():
                field, label = match.groups()
                add(label, {
                    "kind": "source_declaration", "source_id": sid,
                    "source_sha256": document.source_sha256, "field": field,
                    "start": unit["start"], "end": unit["end"], "quote": unit["text"],
                })
    for query in query_inputs:
        qid, subjects = query["case_id"], query["subject_types"]
        if (not isinstance(qid, str) or not qid or qid in queries
                or not isinstance(subjects, list)
                or any(not isinstance(value, str) or not value for value in subjects)):
            raise ValueError("Unique query IDs and declared string-list subject inputs are required")
        queries[qid] = {"subject_types": list(subjects)}
        for index, label in enumerate(subjects):
            add(label, {"kind": "query_input", "query_id": qid, "field": "subject_types", "index": index})
        if not subjects:
            add(MISSING_SUBJECT, {
                "kind": "query_input", "query_id": qid, "field": "subject_types",
                "index": None, "encoding": "existing_empty_type_list_sentinel",
            })
    rows = {}
    for index, label in enumerate(sorted(inventory), 1):
        eid = f"SYN-{9000 + index}"
        rows[eid] = {
            "equipment_id": eid, "equipment_type": label,
            "service_description": "Artificial selection subject", "criticality_score": "5",
            "reliability_score": "5", "safety_critical_element": "No", "redundancy": "None",
            "engineer_comment": "Authorized synthetic query, not field evidence.",
        }
    return {
        "contract": "knowledge-query-registry-fixture-v1", "construction": CONSTRUCTION,
        "source_hashes": source_hashes, "query_inputs": dict(sorted(queries.items())),
        "inventory": [
            {"equipment_type": label, "provenance": sorted(inventory[label], key=canonical_hash)}
            for label in sorted(inventory)
        ],
        "registry": rows, "registry_sha256": canonical_hash(rows),
        "candidate_outputs_used": False, "expected_answer_sheet_used": False,
        "source_scope_labels_used": True, "inventory_independent_of_sources": False,
        "production_scope_review": False,
    }


def _synthetic_sources(manifest, sources):
    records = [row for row in manifest["sources"] if row["partition"] in {"development", "evaluation"}]
    if len(records) != 8 or len({row["source_id"] for row in records}) != 8:
        raise ValueError("Registry authoring requires the frozen eight-source synthetic cohort")
    selected = {}
    for row in records:
        sid = row["source_id"]
        raw = sources[sid]
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Registry authoring source hash mismatch")
        selected[sid] = raw
    return selected


def load_registry_fixture(suite, root: Path = ROOT) -> dict[str, Any] | None:
    """Verify a pinned fixture by replay, returning ONLY its fixed stored rows."""
    manifest = suite.manifest
    path, pin = manifest.get("query_registry"), manifest.get("query_registry_sha256")
    if path is None and pin is None:
        if manifest.get("version") == "knowledge-extraction-reference-v1.4":
            raise ValueError("Reference v1.4 requires a frozen query_registry path and SHA-256")
        return None
    if not isinstance(path, str) or not isinstance(pin, str):
        raise ValueError("A query registry path and SHA-256 must be frozen together")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Query registry must be repository-local")
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin:
        raise ValueError("Query registry fixture hash mismatch")
    fixture = read_json(resolved)
    if len(suite.queries) != 24:
        raise ValueError("Query registry requires all twenty-four declared inputs")
    expected = author_registry(
        _synthetic_sources(manifest, suite.sources),
        ({"case_id": key, "subject_types": value["subject_types"]} for key, value in suite.queries.items()),
    )
    if fixture != expected:
        raise ValueError("Frozen registry differs from its declared authoring inputs/provenance")
    return {"path": path, "sha256": pin, "registry_sha256": fixture["registry_sha256"],
            "construction": CONSTRUCTION, "fixture": deepcopy(fixture)}


def author_repository_fixture(root: Path = ROOT) -> dict[str, Any]:
    """Explicit fixture creation, independent of Suite atoms and candidate assessment."""
    manifest = read_json(root / "eval" / "spec" / "knowledge_extraction.json")
    sources = {
        row["source_id"]: (root / row["path"]).read_bytes()
        for row in manifest["sources"] if row["partition"] in {"development", "evaluation"}
    }
    reference_path = root / manifest["reference"]
    if hashlib.sha256(reference_path.read_bytes()).hexdigest() != manifest["reference_sha256"]:
        raise ValueError("Query-input reference hash mismatch")
    reference = read_json(reference_path)
    inputs = [
        {"case_id": query["id"], "subject_types": query["subject_types"]}
        for source in reference["sources"] for query in source["queries"]
    ]
    if len(inputs) != 24:
        raise ValueError("Registry authoring requires all twenty-four declared query inputs")
    return author_registry(_synthetic_sources(manifest, sources), inputs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the new fixed fixture once")
    args = parser.parse_args(argv)
    fixture = author_repository_fixture()
    raw = _encoded(fixture)
    if args.write:
        with (ROOT / FIXTURE_PATH).open("xb") as stream:
            stream.write(raw)
    print(json.dumps({
        "path": str(FIXTURE_PATH), "sha256": hashlib.sha256(raw).hexdigest(),
        "registry_sha256": fixture["registry_sha256"],
        "source_count": len(fixture["source_hashes"]), "query_count": len(fixture["query_inputs"]),
        "inventory_type_count": len(fixture["registry"]), "written": args.write,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
