"""Independent, offline source-span grader; never import this module in production.

Adapter JSON contract (all intervals are half-open UTF-8 byte offsets):

* Span: {source_id, start, end}; IDs belong to sources, NEVER extractor items.
* Proposal: {source_id, source_sha256, status: "accepted", groups, metadata}.
  A group is {spans: [Span], text: str}. Groups partition the source exactly once.
  metadata contains scopes [{value, spans, evidence: [Span]}], aliases
  [{value, target, evidence: [Span]}], links [{from: [Span], to: [Span],
  evidence: [Span]}]. "spans" describes applicability, "evidence" cites support.
  status="rejected" with a reason retains a failed attempt, not accepted knowledge.
* Retrieval: {status: "ok", selection_mode: "scoped"|"conservative_expansion",
  entries: [{spans: [Span], text: str, source_sha256: str}]}.
  Each entry belongs to one source. Explicit inability is status="unavailable",
  error_code="knowledge_gap", entries=[]; it is allowed only on unknown cases.
* Experiment: {profiles: {"C0": {extractions: [Proposal], retrievals:
  {case_id: Retrieval}}, "C1": ...}, reviews: [Review], attempts: [Attempt]}.
  Extraction observations are primary raw automatic outputs; reviewed-index
  retrieval is a separate observation, not evidence of human publication.

JSON readers reject duplicate keys and nonfinite numbers. All APIs return plain
JSON-compatible reports. Invalid observations fail; invalid references raise
ValueError. Self-tests establish grader behavior, never runtime acceptance.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from statistics import median
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("eval") / "spec" / "knowledge_extraction.json"
Span = tuple[str, int, int]


def canonical_hash(value: Any) -> str:
    """Hash canonical JSON, independent of mapping insertion order (not list order)."""
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def canonical_query_hash(findings: list[dict[str, str]], registry: list[dict[str, str]]) -> str:
    """Hash independently supplied authorized rows, ignoring row ordering only.

    The adapter validates full CSV column/authorization contracts separately;
    this function rejects duplicate/blank identities and non-string cells.
    """
    def keyed(rows: list[dict[str, str]], identity: str) -> dict[str, dict[str, str]]:
        result = {}
        for row in rows:
            if not isinstance(row, dict) or not row.get(identity) or any(not isinstance(value, str) for value in row.values()):
                raise ValueError("invalid input row")
            key = row[identity]
            if key in result:
                raise ValueError("duplicate input identity")
            result[key] = row
        return result
    return canonical_hash({"findings": keyed(findings, "finding_id"), "registry": keyed(registry, "equipment_id")})


def read_json(path: Path) -> Any:
    """Read strict UTF-8 JSON with duplicate/nonfinite-value rejection."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise ValueError(f"nonfinite JSON value: {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)


def union_intervals(intervals: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Sorted interval union; duplicate copies and adjacent fragments count once."""
    result: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            raise ValueError("invalid interval")
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def interval_bytes(intervals: Iterable[tuple[int, int]]) -> int:
    """Number of distinct bytes, not sum of raw passage lengths."""
    return sum(end - start for start, end in union_intervals(intervals))


def overlap_bytes(left: Iterable[tuple[int, int]], right: Iterable[tuple[int, int]]) -> int:
    """Intersection size of two independently unioned sets."""
    a, b = union_intervals(left), union_intervals(right)
    return sum(max(0, min(y, v) - max(x, u)) for x, y in a for u, v in b)


@dataclass(frozen=True)
class Suite:
    """Frozen reference plus exact source bytes. Construct with load_suite()."""

    manifest: dict[str, Any]
    reference: dict[str, Any]
    sources: dict[str, bytes]

    @property
    def atoms(self) -> dict[str, dict[str, Any]]:
        return {
            f"{source['source_id']}:{atom['id']}": dict(atom, source_id=source["source_id"])
            for source in self.reference["sources"] for atom in source["atoms"]
        }

    @property
    def queries(self) -> dict[str, dict[str, Any]]:
        return {
            query["id"]: dict(query, source_id=source["source_id"])
            for source in self.reference["sources"] for query in source["queries"]
        }

    def members(self, partition: str) -> set[str]:
        """Only one synthetic partition and the exposed original smoke may coexist."""
        if partition not in {"development", "evaluation"}:
            raise ValueError("unknown partition")
        return {
            source["source_id"] for source in self.manifest["sources"]
            if source["partition"] in {partition, "shared_smoke"}
        }

    def partition(self, source_id: str) -> str:
        return next(s["partition"] for s in self.manifest["sources"] if s["source_id"] == source_id)


def load_suite(root: Path = ROOT) -> Suite:
    """Validate frozen inventory, source hashes, byte atoms and fixed denominators."""
    manifest = read_json(root / MANIFEST)
    reference_path = root / Path(manifest["reference"])
    reference = read_json(reference_path)
    if hashlib.sha256(reference_path.read_bytes()).hexdigest() != manifest.get("reference_sha256"):
        raise ValueError("reference hash mismatch")
    sources: dict[str, bytes] = {}
    families: set[str] = set()
    for record in manifest["sources"]:
        sid = record["source_id"]
        if sid in sources or record["family"] in families:
            raise ValueError("duplicate source or cross-partition family")
        families.add(record["family"])
        data = (root / Path(record["path"])).read_bytes()
        data.decode("utf-8")
        if not data or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"source hash mismatch: {sid}")
        sources[sid] = data
    suite = Suite(manifest, reference, sources)
    if {s["source_id"] for s in reference["sources"]} != set(sources):
        raise ValueError("reference source membership")
    for source in reference["sources"]:
        sid = source["source_id"]
        ids = [a["id"] for a in source["atoms"]]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate atom")
        for atom in source["atoms"]:
            _spans(suite, [atom_span(sid, atom)], {sid})
            if not set(atom["requires"]) <= set(ids):
                raise ValueError("dangling reference context")
        for alias in source["aliases"]:
            text = sources[sid][alias["start"]:alias["end"]].decode("utf-8")
            if alias["value"] not in text or alias["target"] not in sources[sid].decode("utf-8"):
                raise ValueError("unsupported reference alias")
    for partition in ("development", "evaluation"):
        members = suite.members(partition) - {"original_domain"}
        cases = [q for q in suite.queries.values() if q["source_id"] in members]
        if len(members) != 4 or len(cases) != 12:
            raise ValueError("partition denominator")
        if any(sorted(q["kind"] for q in cases if q["source_id"] == sid) != ["qualifier", "scoped", "unknown"] for sid in members):
            raise ValueError("three query kinds required per source")
    evaluation = suite.members("evaluation") - {"original_domain"}
    expected_scoped = {q["id"] for q in suite.queries.values() if q["source_id"] in evaluation and q["kind"] != "unknown"}
    expected_unknown = {q["id"] for q in suite.queries.values() if q["source_id"] in evaluation and q["kind"] == "unknown"}
    if set(manifest["efficiency_case_ids"]) != expected_scoped or len(expected_scoped) != 8:
        raise ValueError("efficiency denominator")
    if set(manifest["unknown_case_ids"]) != expected_unknown or len(expected_unknown) != 4:
        raise ValueError("unknown denominator")
    ordered = sorted((s["sha256"], s["source_id"]) for s in manifest["sources"] if s["partition"] == "evaluation")
    if manifest["repeat_source_ids"] != [sid for _, sid in ordered[:2]]:
        raise ValueError("repeat sources not selected by frozen hash ordering")
    return suite


def atom_span(source_id: str, atom: dict[str, Any]) -> dict[str, Any]:
    """Translate a reference atom to the adapter's source-only Span representation."""
    return {"source_id": source_id, "start": atom["start"], "end": atom["end"]}


def _spans(suite: Suite, values: Any, allowed: set[str]) -> list[Span]:
    if not isinstance(values, list) or not values:
        raise ValueError("nonempty span list required")
    result = []
    for value in values:
        if not isinstance(value, dict) or set(value) != {"source_id", "start", "end"}:
            raise ValueError("invalid source reference")
        sid, start, end = value["source_id"], value["start"], value["end"]
        if not isinstance(sid, str) or sid not in allowed or sid not in suite.sources:
            raise ValueError("unauthorized source")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(suite.sources[sid]):
            raise ValueError("out-of-range source reference")
        suite.sources[sid][start:end].decode("utf-8")
        result.append((sid, start, end))
    return result


def _covered(spans: list[Span], sid: str, start: int, end: int) -> bool:
    return overlap_bytes([(a, b) for s, a, b in spans if s == sid], [(start, end)]) == end - start


def _materialize(suite: Suite, group: Any, allowed: set[str], entry: bool = False) -> list[Span]:
    expected = {"spans", "text", "source_sha256"} if entry else {"spans", "text"}
    if not isinstance(group, dict) or set(group) != expected:
        raise ValueError("invalid materialized entry fields")
    spans = _spans(suite, group["spans"], allowed)
    if len({s for s, _, _ in spans}) != 1:
        raise ValueError("entry mixes sources")
    text = b"".join(suite.sources[s][a:b] for s, a, b in spans).decode("utf-8")
    if not isinstance(group["text"], str) or text != group["text"]:
        raise ValueError("altered or invented materialized text")
    if entry and group["source_sha256"] != hashlib.sha256(suite.sources[spans[0][0]]).hexdigest():
        raise ValueError("entry source hash mismatch")
    return spans


def _diagnostic(expected: set[Any], actual: set[Any]) -> dict[str, Any]:
    return {
        "expected": len(expected), "observed": len(actual),
        "true_positive": len(expected & actual),
        "precision": len(expected & actual) / len(actual) if actual else None,
        "recall": len(expected & actual) / len(expected) if expected else None,
        "missing": sorted(expected - actual), "unsupported": sorted(actual - expected),
    }


def _closure_pairs(edges: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    graph: dict[str, set[str]] = {}
    for a, b in edges:
        if a != b:
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    result: set[tuple[str, str]] = set()
    for origin in graph:
        seen, todo = {origin}, [origin]
        while todo:
            node = todo.pop()
            for neighbour in graph[node] - seen:
                seen.add(neighbour)
                todo.append(neighbour)
        result.update(tuple(sorted((origin, other))) for other in seen - {origin})
    return result


def assess_extraction(suite: Suite, proposal: dict[str, Any]) -> dict[str, Any]:
    """Grade exact partition/text and atom-normalized metadata, independent of groups.

    Empty scope is the declared conservative general fallback, not an accepted
    wrong restrictive claim. Missing metadata stays visible as repair diagnostics;
    it is never filled into the proposal. Nonempty partial/unsupported scope,
    unsupported aliases and missing context with a scoped endpoint are critical.
    Retrieval completeness/usefulness and actual human work remain separate gates.
    Context closure is computed on actual groups before projecting fully covered
    atoms. Reference atoms never create graph edges. Correct partial scope may
    need repair when its whole atom co-returns; unsupported partial scope and
    restrictive scope on an atom split across components remain critical.
    """
    report: dict[str, Any] = {"status": "fail", "fidelity": "fail", "semantic": "not_run", "accepted_wrong_critical": False}
    try:
        if not isinstance(proposal, dict):
            raise ValueError("proposal object required")
        if proposal.get("status") == "rejected":
            report["error"] = "raw_rejected_proposal"
            return report
        if set(proposal) != {"source_id", "source_sha256", "status", "groups", "metadata"} or proposal["status"] != "accepted":
            raise ValueError("invalid proposal fields/status")
        sid = proposal["source_id"]
        if sid not in suite.sources or proposal["source_sha256"] != hashlib.sha256(suite.sources[sid]).hexdigest():
            raise ValueError("source binding mismatch")
        if not isinstance(proposal["groups"], list) or not proposal["groups"]:
            raise ValueError("groups required")
        groups = [_materialize(suite, group, {sid}) for group in proposal["groups"]]
        intervals = sorted((a, b) for group in groups for _, a, b in group)
        cursor = 0
        for start, end in intervals:
            if start != cursor:
                raise ValueError("source bytes omitted or duplicated")
            cursor = end
        if cursor != len(suite.sources[sid]):
            raise ValueError("incomplete source partition")
        report["fidelity"] = "pass"
        source = next(s for s in suite.reference["sources"] if s["source_id"] == sid)
        atoms = {a["id"]: a for a in source["atoms"]}
        metadata = proposal["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {"scopes", "aliases", "links"}:
            raise ValueError("closed metadata object required")
        if any(not isinstance(metadata[key], list) for key in metadata):
            raise ValueError("metadata lists required")

        def evidence(record: dict[str, Any], literals: Iterable[str] = ()) -> None:
            spans = _spans(suite, record["evidence"], {sid})
            texts = [suite.sources[s][a:b].decode("utf-8") for s, a, b in spans]
            for literal in literals:
                if not isinstance(literal, str) or not literal or not any(literal in text for text in texts):
                    raise ValueError("metadata literal missing from source evidence")

        expected_scopes = {(key, scope.casefold()) for key, atom in atoms.items() for scope in atom["scopes"]}
        scope_spans: dict[str, list[Span]] = {}
        for record in metadata["scopes"]:
            if set(record) != {"value", "spans", "evidence"}:
                raise ValueError("invalid scope fields")
            evidence(record, [record["value"]])
            affected = _spans(suite, record["spans"], {sid})
            if not any(overlap_bytes([(a, b) for s, a, b in affected if s == sid],
                                     [(atom["start"], atom["end"])]) for atom in atoms.values()):
                raise ValueError("scope does not intersect a labelled atom")
            scope_spans.setdefault(record["value"].casefold(), []).extend(affected)
        expected_aliases = {(alias["value"].casefold(), alias["target"].casefold()) for alias in source["aliases"]}
        actual_aliases = set()
        for record in metadata["aliases"]:
            if set(record) != {"value", "target", "evidence"}:
                raise ValueError("invalid alias fields")
            evidence(record, [record["value"], record["target"]])
            actual_aliases.add((record["value"].casefold(), record["target"].casefold()))
        expected_links = _closure_pairs((key, other) for key, atom in atoms.items() for other in atom["requires"])
        parents = list(range(len(groups)))

        def root(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        def endpoint_groups(spans: list[Span]) -> set[int]:
            matched = {
                index for index, group in enumerate(groups)
                if any(s == t and max(a, c) < min(b, d)
                       for s, a, b in spans for t, c, d in group)
            }
            if not matched:
                raise ValueError("context endpoint does not map to a materialized group")
            return matched

        for record in metadata["links"]:
            if set(record) != {"from", "to", "evidence"}:
                raise ValueError("invalid context fields")
            evidence(record)
            left = endpoint_groups(_spans(suite, record["from"], {sid}))
            right = endpoint_groups(_spans(suite, record["to"], {sid}))
            joined = sorted(left | right)
            for other in joined[1:]:
                parents[root(other)] = root(joined[0])

        grouped: dict[int, list[int]] = {}
        for index in range(len(groups)):
            grouped.setdefault(root(index), []).append(index)
        components = sorted(grouped.values(), key=lambda indices: min(span for i in indices for span in groups[i]))
        component_spans = [[span for index in indices for span in groups[index]] for indices in components]
        component_atoms = [
            {key for key, atom in atoms.items() if _covered(spans, sid, atom["start"], atom["end"])}
            for spans in component_spans
        ]
        actual_links = {
            tuple(sorted((a, b))) for members in component_atoms for a in members for b in members if a != b
        }
        whole_in_component = set().union(*component_atoms)
        claimed_scopes: set[tuple[str, str]] = set()
        actual_scopes: set[tuple[str, str]] = set()
        incomplete_scope_bytes = []
        for value, spans in sorted(scope_spans.items()):
            for key, atom in atoms.items():
                claimed_bytes = overlap_bytes(
                    [(a, b) for s, a, b in spans if s == sid],
                    [(atom["start"], atom["end"])],
                )
                if not claimed_bytes:
                    continue
                fact = (key, value)
                claimed_scopes.add(fact)
                complete = claimed_bytes == atom["end"] - atom["start"]
                if complete and key in whole_in_component:
                    actual_scopes.add(fact)
                if not complete:
                    incomplete_scope_bytes.append({
                        "atom": key, "value": value, "claimed_bytes": claimed_bytes,
                        "atom_bytes": atom["end"] - atom["start"],
                    })
        report["metrics"] = {
            "scope": _diagnostic(expected_scopes, actual_scopes),
            "alias": _diagnostic(expected_aliases, actual_aliases),
            "context": _diagnostic(expected_links, actual_links),
        }
        scoped_atoms = {key for key, _ in claimed_scopes}
        disconnected_scoped_atoms = scoped_atoms - whole_in_component
        partial_scope_atoms = {
            key for key in scoped_atoms
            if {value for atom, value in claimed_scopes if atom == key}
            != {value for atom, value in expected_scopes if atom == key}
        }
        detached_scoped_context = {
            pair for pair in expected_links - actual_links if set(pair) & scoped_atoms
        }
        semantic_fail = bool(
            claimed_scopes - expected_scopes or partial_scope_atoms or disconnected_scoped_atoms
            or actual_aliases - expected_aliases or detached_scoped_context
        )
        repairs = {
            "scope_add": len(expected_scopes - actual_scopes),
            "alias_add": len(expected_aliases - actual_aliases),
            "context_add": len(expected_links - actual_links),
        }
        report["repair_required"] = semantic_fail or any(repairs.values())
        report["repair_counts"] = repairs
        report["repair_count_basis"] = "Missing complete atom-level scope/alias facts and context-closure pairs; NOT observed human corrections or review benefit."
        report["incomplete_scope_byte_facts"] = incomplete_scope_bytes
        report["group_graph"] = {
            "component_count": len(components),
            "components": [
                {"group_count": len(indices),
                 "source_bytes": {sid: interval_bytes([(a, b) for s, a, b in spans if s == sid])},
                 "whole_atom_ids": sorted(members)}
                for indices, spans, members in zip(components, component_spans, component_atoms)
            ],
            "atoms_not_whole_in_one_component": sorted(set(atoms) - whole_in_component),
            "overclosure_pair_count": len(actual_links - expected_links),
        }
        report["critical_errors"] = {
            "unsupported_scope_facts": sorted(claimed_scopes - expected_scopes),
            "nonempty_incomplete_scope_atoms": sorted(partial_scope_atoms),
            "disconnected_scoped_atoms": sorted(disconnected_scoped_atoms),
            "unsupported_alias_facts": sorted(actual_aliases - expected_aliases),
            "detached_scoped_context_pairs": sorted(detached_scoped_context),
        }
        unresolved_aliases = sum(a.get("judgment") == "needs_review" for a in source["aliases"])
        pending = any(a.get("judgment") == "needs_review" for a in atoms.values()) or bool(unresolved_aliases)
        report["semantic"] = "fail" if semantic_fail else "needs_review" if pending else "pass"
        report["status"] = report["semantic"]
        report["accepted_wrong_critical"] = semantic_fail
        report["atom_count"] = len(atoms)
        report["unresolved_atom_count"] = sum(a.get("judgment") == "needs_review" for a in atoms.values())
        report["unresolved_alias_count"] = unresolved_aliases
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        report["error"] = str(error)
        report["status"] = "fail"
    return report


def case_expectation(suite: Suite, case_id: str) -> dict[str, Any]:
    """Resolve independent atom labels/closure and active source membership.

    General atoms are required context, never irrelevant bytes. Unknown cases
    require the entire active corpus or explicit inability, not an empty success.
    """
    query = suite.queries[case_id]
    members = suite.members(suite.partition(query["source_id"]))
    atoms = {key: atom for key, atom in suite.atoms.items() if atom["source_id"] in members}
    subjects = {s.casefold() for s in query["subject_types"]}
    targets = set(subjects)
    for source in suite.reference["sources"]:
        if source["source_id"] in members:
            targets.update(a["target"].casefold() for a in source["aliases"] if a["value"].casefold() in subjects)
    required = {
        key for key, atom in atoms.items()
        if query["kind"] == "unknown" or not atom["scopes"] or targets & {s.casefold() for s in atom["scopes"]}
    }
    todo = list(required)
    while todo:
        atom = atoms[todo.pop()]
        for other in atom["requires"]:
            key = f"{atom['source_id']}:{other}"
            if key not in required:
                required.add(key)
                todo.append(key)
    permitted = set(query.get("permitted_context", []))
    irrelevant = {
        key for key, atom in atoms.items()
        if atom["scopes"] and key not in required | permitted
    }
    return {"query": query, "sources": sorted(members), "required": sorted(required),
            "permitted_context": sorted(permitted), "irrelevant": sorted(irrelevant)}


def assess_retrieval(suite: Suite, case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Grade atom-union recall and manually interpretable scoped-byte reduction."""
    expected = case_expectation(suite, case_id)
    required, irrelevant = expected["required"], expected["irrelevant"]
    unresolved_aliases = [
        f"{source['source_id']}:{alias['value']}"
        for source in suite.reference["sources"] if source["source_id"] in expected["sources"]
        for alias in source["aliases"] if alias.get("judgment") == "needs_review"
    ]
    report: dict[str, Any] = {
        "case_id": case_id, "status": "fail", "required_atom_count": len(required),
        "unresolved_alias_labels": unresolved_aliases,
    }
    try:
        if result.get("status") == "unavailable":
            if set(result) != {"status", "error_code", "entries"} or result["entries"] != []:
                raise ValueError("unavailable result must contain no partial usable entries")
            allowed = expected["query"]["kind"] == "unknown" and result["error_code"] == "knowledge_gap"
            unresolved = [key for key in required if suite.atoms[key].get("judgment") == "needs_review"]
            report.update(status="fail" if not allowed else "needs_review" if unresolved or unresolved_aliases else "pass",
                          handling="explicit_inability", recall=None, unresolved_required_atoms=unresolved)
            return report
        if set(result) != {"status", "selection_mode", "entries"} or result["status"] != "ok":
            raise ValueError("invalid retrieval result")
        if result["selection_mode"] not in {"scoped", "conservative_expansion"} or not isinstance(result["entries"], list):
            raise ValueError("invalid selection mode/entries")
        selected = [span for entry in result["entries"] for span in _materialize(suite, entry, set(expected["sources"]), entry=True)]
        atoms = suite.atoms
        covered = {
            key for key, atom in atoms.items()
            if _covered(selected, atom["source_id"], atom["start"], atom["end"])
        }
        # A rule is credited only with its complete qualifier closure.
        covered_with_context = set(covered)
        changed = True
        while changed:
            bad = {
                key for key in covered_with_context
                if any(f"{atoms[key]['source_id']}:{other}" not in covered_with_context for other in atoms[key]["requires"])
            }
            changed = bool(bad)
            covered_with_context -= bad
        hits = len(set(required) & covered_with_context)
        b_bytes = r_bytes = selected_bytes = 0
        for sid in expected["sources"]:
            baseline = [(atoms[key]["start"], atoms[key]["end"]) for key in irrelevant if atoms[key]["source_id"] == sid]
            returned = [(a, b) for s, a, b in selected if s == sid]
            b_bytes += interval_bytes(baseline)
            r_bytes += overlap_bytes(baseline, returned)
            selected_bytes += interval_bytes(returned)
        recall = hits / len(required) if required else None
        reduction = 1 - r_bytes / b_bytes if b_bytes else None
        unknown = expected["query"]["kind"] == "unknown"
        broadening_ok = not unknown or (
            result["selection_mode"] == "conservative_expansion"
            and all(_covered(selected, sid, 0, len(suite.sources[sid])) for sid in expected["sources"])
        )
        efficiency = case_id in suite.manifest["efficiency_case_ids"]
        useful = not efficiency or (b_bytes > 0 and reduction >= suite.manifest["thresholds"]["each_scoped_irrelevant_byte_reduction"])
        pending = any(atoms[key].get("judgment") == "needs_review" for key in required) or bool(unresolved_aliases)
        passed = recall == 1.0 and broadening_ok and useful
        report.update(
            status="fail" if not passed else "needs_review" if pending else "pass",
            recall=recall, covered_required_atoms=hits,
            missing_required_atoms=sorted(set(required) - covered_with_context),
            unresolved_required_atoms=[key for key in required if atoms[key].get("judgment") == "needs_review"],
            irrelevant_baseline_bytes=b_bytes, irrelevant_returned_bytes=r_bytes,
            irrelevant_byte_reduction=reduction, selected_source_union_bytes=selected_bytes,
            provider_text_bytes=sum(len(e["text"].encode("utf-8")) for e in result["entries"]),
            full_active_corpus_bytes=sum(len(suite.sources[sid]) for sid in expected["sources"]),
            conservative_expansion=result["selection_mode"] == "conservative_expansion",
            broadening_ok=broadening_ok, usefulness_pass=useful,
        )
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        report["error"] = str(error)
    return report


def assess_boundary_case(suite: Suite, case_id: str, observation: dict[str, Any]) -> dict[str, Any]:
    """Grade a separate lifecycle/fail-closed probe, never one of the 24 queries.

    Probe observations bind a unique marker string to captured result/index/
    provider payloads. Failure probes additionally supply before/after artifact
    hashes. These are adapter captures, not independent human attestation.
    """
    case = next(c for c in suite.reference["boundary_cases"] if c["id"] == case_id)
    try:
        captures = [observation[name] for name in ("result_text", "index_text", "provider_text")]
        if not all(isinstance(text, str) for text in captures):
            raise ValueError("text captures required")
        marker = observation["marker"]
        if not isinstance(marker, str) or not marker:
            raise ValueError("nonempty marker required")
        if case["kind"] == "failure":
            before, after = observation["before_sha256"], observation["after_sha256"]
            valid_hash = lambda x: isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x)
            passed = (
                observation["status"] == "unavailable" and observation["error_code"] == case["code"]
                and observation["entries"] == [] and observation["exit_code"] != 0
                and type(observation["exit_code"]) is int
                and valid_hash(before) and before == after and not any(captures)
            )
        else:
            present = [marker in text for text in captures]
            passed = all(present) if case["expected"] == "included" else not any(present)
        return {"case_id": case_id, "denominator": "boundary_only", "status": "pass" if passed else "fail"}
    except (ValueError, KeyError, TypeError) as error:
        return {"case_id": case_id, "denominator": "boundary_only", "status": "fail", "error": str(error)}


def calibrate_semantic_review(suite: Suite, judgments: list[dict[str, Any]]) -> dict[str, Any]:
    """Check all six known controls; does not certify the reviewer or source truth.

    Judgment = {id, verdict, reason}. Unresolved MUST remain needs_review.
    Bind the returned report to the actual reviewer/config hash externally.
    """
    expected = {c["id"]: c["expected"] for c in suite.reference["semantic_controls"]}
    actual = {j.get("id"): j for j in judgments}
    valid = len(actual) == len(judgments) and set(actual) == set(expected)
    checks = [
        {"id": key, "expected": verdict, "observed": actual.get(key, {}).get("verdict"),
         "correct": actual.get(key, {}).get("verdict") == verdict and bool(actual.get(key, {}).get("reason"))}
        for key, verdict in expected.items()
    ]
    return {"scope": "known_fixture_conformance_not_reviewer_certification",
            "status": "pass" if valid and all(c["correct"] for c in checks) else "fail",
            "control_count": len(expected), "checks": checks}


def assess_effort(
    suite: Suite, reviews: list[dict[str, Any]], *,
    candidate_hashes: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Count unique atom-fact corrections under the frozen crossed human schedule.

    Review fields: source_id, strategy, reviewer_id, reviewer_slot, kind="human",
    blinded=true, answer_sheet_exposed=false, unblinded=false, recognizability
    (a disclosure string), candidate_sha256, order (the scheduled pair), operations.
    Operation fields: kind, atoms (local atom IDs), value (scope/alias/relation
    identity or group-change reason). Events with the same normalized fact count
    once. candidate_hashes is {source_id: {strategy: canonical_candidate_hash}},
    independently computed from retained raw outputs. Without it review remains
    pending, even when records claim a benefit.
    """
    schedules = suite.manifest["review_schedule"]
    expected = {(r["source_id"], strategy) for r in schedules for strategy in ("C0", "C1")}
    records = {(r.get("source_id"), r.get("strategy")): r for r in reviews}
    report: dict[str, Any] = {"status": "needs_review", "benefit_demonstrated": False, "counts": {"C0": 0, "C1": 0}, "per_source": {}}
    if len(records) != len(reviews) or set(records) != expected:
        report["reason"] = "missing_or_duplicate_paired_human_records"
        return report
    identities: dict[str, str] = {}
    try:
        for schedule in schedules:
            sid = schedule["source_id"]
            pair = [records[(sid, strategy)] for strategy in ("C0", "C1")]
            if pair[0]["reviewer_id"] == pair[1]["reviewer_id"]:
                raise ValueError("same reviewer saw both candidates for a source")
            for strategy, record in zip(("C0", "C1"), pair):
                slot = schedule[strategy]
                if not record["reviewer_id"] or record["reviewer_slot"] != slot or record["order"] != schedule["order"]:
                    raise ValueError("review schedule mismatch")
                if slot in identities and identities[slot] != record["reviewer_id"]:
                    raise ValueError("reviewer identity changed")
                identities[slot] = record["reviewer_id"]
                if record["kind"] != "human" or record["blinded"] is not True or record["answer_sheet_exposed"] is not False or record["unblinded"] is not False:
                    raise ValueError("independent blinded human review unavailable")
                if not isinstance(record["recognizability"], str) or not record["recognizability"]:
                    raise ValueError("recognizability disclosure missing")
                digest = record["candidate_sha256"]
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError("candidate hash missing")
                if candidate_hashes is None:
                    raise ValueError("retained candidate bindings unavailable")
                if candidate_hashes.get(sid, {}).get(strategy) != digest:
                    raise ValueError("review does not bind retained candidate")
                allowed_atoms = {a["id"] for a in suite.atoms.values() if a["source_id"] == sid}
                normalized = set()
                for operation in record["operations"]:
                    kind, atom_ids, value = operation["kind"], operation["atoms"], operation["value"]
                    if kind not in suite.manifest["effort_taxonomy"] or not isinstance(atom_ids, list) or not atom_ids or not set(atom_ids) <= allowed_atoms or not isinstance(value, str) or not value:
                        raise ValueError("invalid normalized correction")
                    # Atom-level assignments each cost one; a shared group edit costs one.
                    if kind == "group_change":
                        normalized.add((kind, tuple(sorted(set(atom_ids))), value))
                    else:
                        normalized.update((kind, (atom,), value) for atom in set(atom_ids))
                count = len(normalized)
                report["per_source"].setdefault(sid, {})[strategy] = count
                report["counts"][strategy] += count
        c0, c1 = report["counts"]["C0"], report["counts"]["C1"]
        thresholds = suite.manifest["thresholds"]
        benefit = (
            c0 >= thresholds["minimum_c0_corrections"]
            and c0 - c1 >= thresholds["c1_absolute_correction_reduction"]
            and (c0 - c1) / c0 >= thresholds["c1_relative_correction_reduction"]
        )
        report.update(status="pass" if benefit else "fail", benefit_demonstrated=benefit,
                      absolute_reduction=c0 - c1, relative_reduction=(c0 - c1) / c0 if c0 else None)
    except (ValueError, KeyError, TypeError) as error:
        report["reason"] = str(error)
    return report


def assess_attempts(suite: Suite, attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """Check application ledger slots/recovery; never infer hidden HTTP or USD.

    Attempt fields: slot_id, attempt (1 or 2), status, error_code (null on success),
    source_sha256, prompt_sha256, schema_sha256, settings_sha256, model, provider.
    Status is reserved/interrupted/transport_error/structural_error/accepted/
    semantic_error/refused. Retried sends require a preceding allowlisted failure.
    A reserved/interrupted send remains spent. Raw requests, costs and runtime
    freeze evidence are retained by the adapter, not invented by this checker.
    """
    slots: dict[str, list[dict[str, Any]]] = {slot: [] for slot in suite.manifest["slot_ids"]}
    report: dict[str, Any] = {
        "status": "needs_review", "planned_slots": len(slots), "application_attempts": len(attempts),
        "maximum_application_attempts": 26, "strict_accounting": "not_established",
        "hidden_http_attempts": None, "usd_cost": None,
    }
    try:
        if len(attempts) > suite.manifest["experiment"]["maximum_application_attempts"]:
            raise ValueError("total application attempt budget exceeded")
        for attempt in attempts:
            if attempt["slot_id"] not in slots or type(attempt["attempt"]) is not int:
                raise ValueError("unknown slot or invalid attempt number")
            slots[attempt["slot_id"]].append(attempt)
        statuses = {"reserved", "interrupted", "transport_error", "structural_error", "accepted", "semantic_error", "refused"}
        global_profile = set()
        for slot, records in slots.items():
            records.sort(key=lambda r: r["attempt"])
            if len(records) > 2 or [r["attempt"] for r in records] != list(range(1, len(records) + 1)):
                raise ValueError("duplicate, skipped or excess per-slot attempt")
            for record in records:
                if record["status"] not in statuses:
                    raise ValueError("unknown attempt status")
                sid = slot.rsplit(".", 1)[0]
                if record["source_sha256"] != hashlib.sha256(suite.sources[sid]).hexdigest():
                    raise ValueError("attempt source binding mismatch")
                pins = tuple(record[key] for key in ("prompt_sha256", "schema_sha256", "settings_sha256", "model", "provider"))
                if not all(isinstance(pin, str) and pin for pin in pins):
                    raise ValueError("missing experiment pins")
                for digest in pins[:3]:
                    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                        raise ValueError("invalid configuration hash")
                global_profile.add(pins)
            if len(records) == 2:
                first = records[0]
                if first["status"] not in {"transport_error", "structural_error"} or first["error_code"] not in suite.manifest["experiment"]["retry_allowed"]:
                    raise ValueError("ineligible retry, including semantic retry")
        if len(global_profile) > 1:
            raise ValueError("model/prompt/schema/settings/provider changed within fixed experiment")
        unexecuted = [slot for slot, records in slots.items() if not records]
        unfinished = [slot for slot, records in slots.items() if records and records[-1]["status"] != "accepted"]
        report.update(
            status="fail" if unfinished else "needs_review" if unexecuted else "pass",
            unexecuted_slots=unexecuted, unsuccessful_or_interrupted_slots=unfinished,
            first_attempt_failures=sum(bool(records) and records[0]["status"] != "accepted" for records in slots.values()),
            recovery_attempts=sum(len(records) == 2 for records in slots.values()),
            note="Application-ledger conformance only; Copilot hidden HTTP/token/USD controls remain unknown.",
        )
    except (ValueError, KeyError, TypeError) as error:
        report.update(status="fail", error=str(error))
    return report


def assess_repeats(suite: Suite, primaries: list[dict[str, Any]], repeats: list[dict[str, Any]]) -> dict[str, Any]:
    """Grade four additional outputs and report normalized metadata drift, not ID equality.

    Repeats = [{slot_id, proposal}]. Each chosen source has its primary and two
    extractions. Full source/critical-semantic correctness is mandatory each time.
    """
    expected = {slot for slot in suite.manifest["slot_ids"] if ".repeat" in slot}
    observed = [r.get("slot_id") for r in repeats]
    if set(observed) != expected or len(observed) != len(expected):
        return {"status": "needs_review", "expected_repeats": 4, "observed_repeats": len(repeats)}
    reports = {}
    for sid in suite.manifest["repeat_source_ids"]:
        originals = [p for p in primaries if p.get("source_id") == sid]
        proposals = originals + [r["proposal"] for r in sorted(repeats, key=lambda r: r["slot_id"]) if r["slot_id"].rsplit(".", 1)[0] == sid]
        if len(proposals) != 3 or any(p.get("source_id") != sid for p in proposals):
            return {"status": "fail", "error": "repeat source binding or primary count"}
        grades = [assess_extraction(suite, proposal) for proposal in proposals]
        signatures = [canonical_hash(grade.get("metrics", {})) for grade in grades]
        reports[sid] = {
            "status": "fail" if any(g["status"] == "fail" for g in grades) else "needs_review" if any(g["status"] != "pass" for g in grades) else "pass",
            "outputs": grades, "metadata_drift_observed": len(set(signatures)) > 1,
            "atom_coverage_all_exact": all(g["fidelity"] == "pass" for g in grades),
        }
    statuses = [report["status"] for report in reports.values()]
    return {"status": "fail" if "fail" in statuses else "needs_review" if "needs_review" in statuses else "pass",
            "sources": reports, "statistical_stability": "not_established_two_sources_only"}


def assess_observations(suite: Suite, observation: dict[str, Any]) -> dict[str, Any]:
    """Report component results separately from deliberately unexecuted system gates.

    This evaluator cannot qualify C1 or production: human publication, real
    provider handoff, retry/cost freeze and owner decision need separate evidence.
    A Copilot experiment never establishes hidden HTTP/USD accounting.
    """
    profiles = {}
    for name in ("C0", "C1"):
        profile = observation.get("profiles", {}).get(name, {})
        proposals = profile.get("extractions", [])
        reports = [dict(assess_extraction(suite, p), source_id=p.get("source_id")) for p in proposals]
        seen = [p.get("source_id") for p in proposals]
        retrievals = {key: assess_retrieval(suite, key, value) for key, value in profile.get("retrievals", {}).items()}
        complete = set(seen) == set(suite.sources) and len(seen) == len(suite.sources) and set(retrievals) == set(suite.queries)
        statuses = [r["status"] for r in reports] + [r["status"] for r in retrievals.values()]
        component = "fail" if "fail" in statuses else "pass" if complete and statuses and all(s == "pass" for s in statuses) else "needs_review"
        reductions = [retrievals[k]["irrelevant_byte_reduction"] for k in suite.manifest["efficiency_case_ids"] if k in retrievals and retrievals[k].get("irrelevant_byte_reduction") is not None]
        profiles[name] = {
            "component_status": component, "inventory_complete": complete,
            "extractions": reports, "retrievals": retrievals,
            "efficiency_median_reduction": median(reductions) if len(reductions) == 8 else None,
            "efficiency_case_count": len(reductions),
            "qualification": "unqualified" if name == "C1" else "component_only_not_production",
        }
    candidates: dict[str, dict[str, str]] = {}
    for strategy in ("C0", "C1"):
        for value in observation.get("profiles", {}).get(strategy, {}).get("extractions", []):
            candidates.setdefault(value.get("source_id"), {})[strategy] = canonical_hash(value)
    effort = assess_effort(suite, observation.get("reviews", []), candidate_hashes=candidates)
    primaries = observation.get("profiles", {}).get("C1", {}).get("extractions", [])
    repeats = assess_repeats(suite, primaries, observation.get("repeats", []))
    attempts = assess_attempts(suite, observation.get("attempts", []))
    return {
        "scope": "component_observations_not_system_acceptance",
        "profiles": profiles, "human_effort": effort,
        "attempt_accounting": attempts, "strict_accounting": "unexecuted_or_unknown_hidden_attempts",
        "repeat_reliability": repeats,
        "lifecycle_and_handoff": "unexecuted_separate_adapter_captures_required",
        "C1_qualification": "unqualified",
        "overall": "pending", "system_acceptance": "not_established",
    }


def main(argv: list[str] | None = None) -> int:
    """Read an observation JSON; emit JSON with fail/pending exit 1/2, never a fake pass."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args(argv)
    try:
        suite = load_suite()
        report = assess_observations(suite, read_json(args.observations)) if args.observations else {
            "scope": "reference_integrity_only", "status": "pass",
            "sources": len(suite.sources), "queries": len(suite.queries),
            "system_acceptance": "not_established",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        if args.observations:
            return 1 if any(p["component_status"] == "fail" for p in report["profiles"].values()) else 2
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
