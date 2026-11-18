"""Observe source-first C0/C1 through public APIs without supplying evaluator gold.

Offline: python -B -m eval.knowledge.run --output <new-results-child>
Plan only: python -B -m eval.knowledge.run --copilot-experiment --plan-only
Authorized experiment additionally requires --allow-inference (13 slots/26 sends).

Default offline runs create UNREVIEWED partition-separated drafts. All 24 query
inputs are retained, but retrieval remains pending rather than manufacturing review.
--synthetic-review-diagnostic explicitly exercises publication/retrieval in isolated
software-fixture stores using UNCHANGED raw C0 output. Its declarations are NOT
human approval, and neither numerical passes nor publication qualify the system.
Optional --reviewed-inputs JSON supplies existing releases:
{"contract":"knowledge-eval-reviewed-input-v1","partitions":{
 "development":{"store":"<repository-relative-path>","release_id":"sha256-...",
 "expected_strategy":{...},"review_kind":"human"|"synthetic_software_fixture",
 "review_disclosure":"<actual provenance and limitations>"},
 "evaluation":{...}}}.
Synthetic reviews are diagnostic software fixtures, never human effort, genuine
publication approval, selective qualification or system B01/B02 acceptance.
The adapter never changes supplied releases or repairs extraction metadata.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
import importlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any, Callable
from uuid import uuid4

from .evaluate import (
    ROOT, Suite, assess_extraction, assess_observations, assess_retrieval,
    canonical_hash, load_suite, read_json,
)
from .query_inputs import load_registry_fixture


RESULTS = Path("eval") / "results" / "knowledge" / "extraction"
LEDGER = RESULTS / "source-first-copilot.experimental-ledger.json"
ASSESSMENT_TIME = "2026-07-01T00:00:00+00:00"
MODEL = "gpt-6-luna"
SOFTWARE_REVIEWER = "Softwarefixture NOT humanapproval"
SOFTWARE_REASON = (
    "Isolated software selector diagnostic over unchanged raw C0 output. "
    "NOT human content approval, NOT engineering approval, NOT qualification. "
    "No evaluator expectations were used to correct metadata."
)


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


class EvidenceWriter:
    """Write-once run directory. Existing observations are never overwritten."""

    def __init__(self, path: Path):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=False)

    def write(self, name: str, value: Any) -> None:
        path = self.root / name
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise ValueError("evidence path escapes run directory")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(value if isinstance(value, bytes) else _encoded(value))


def _runtime_source():
    return importlib.import_module("triage_knowledge.source")


def document_for(suite: Suite, source_id: str):
    """Send only exact submitted source bytes/name/identity to production intake."""
    record = next(s for s in suite.manifest["sources"] if s["source_id"] == source_id)
    return _runtime_source().SourceDocument.from_bytes(
        suite.sources[source_id], name=Path(record["path"]).name, source_id=source_id,
    )


def adapt_extraction(extraction) -> dict[str, Any]:
    """Translate validated runtime groups to source spans, never reference atom IDs."""
    document = extraction.document
    groups = extraction.groups
    units = {u["unit_id"]: u for u in document.units}
    by_id = {group["group_id"]: group for group in groups}

    def spans(group):
        return [dict(span, source_id=document.source_id) for span in group["spans"]]

    def evidence(group):
        return [
            {"source_id": document.source_id, "start": units[ev["unit_id"]]["start"], "end": units[ev["unit_id"]]["end"]}
            for ev in group["evidence"]
        ]

    metadata: dict[str, list] = {"scopes": [], "aliases": [], "links": []}
    for group in groups:
        affected, cited = spans(group), evidence(group)
        metadata["scopes"].extend({"value": value, "spans": affected, "evidence": cited} for value in group["scopes"])
        if group["aliases"] and len(group["scopes"]) != 1:
            raise ValueError("Cannot infer an alias target for an empty/multiple-scope runtime group")
        metadata["aliases"].extend(
            {"value": value, "target": group["scopes"][0], "evidence": cited}
            for value in group["aliases"]
        )
        metadata["links"].extend(
            {"from": affected, "to": spans(by_id[target]), "evidence": cited}
            for target in group["required_with"]
        )
    return {
        "source_id": document.source_id, "source_sha256": document.source_sha256,
        "status": "accepted",
        "groups": [{"spans": spans(group), "text": group["text"]} for group in groups],
        "metadata": metadata,
    }


def adapt_result(result) -> dict[str, Any]:
    """Retain the actual tool's spans/text and translate only contract field names."""
    raw = result.to_dict()
    entries = raw["entries"]
    values = list(entries.values()) if isinstance(entries, dict) else entries
    if raw["status"] != "ok":
        if values:
            raise ValueError("Unavailable runtime result contains partial usable entries")
        return {"status": "unavailable", "error_code": raw["error_code"], "entries": []}
    mode = raw["selection_mode"]
    if mode not in {"scoped", "conservative_expansion"}:
        raise ValueError("Unsupported runtime selection mode")
    return {
        "status": "ok", "selection_mode": mode,
        "entries": [
            {"spans": [dict(span, source_id=entry["source_id"]) for span in entry["spans"]],
             "text": entry["text"], "source_sha256": entry["source_sha256"]}
            for entry in values
        ],
    }


def query_rows(
    subject_types: list[str], *,
    shared_registry_rows: dict[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, dict[str, str]]]:
    """Map authorized synthetic subject labels to original CSV column contracts.

    Missing/ambiguous type uses an explicitly unrecognized synthetic type. Scores
    are inert query-fixture priors, not rule answers or real finding assessments.
    No expected atoms, aliases, metadata or rule text is added to these rows.
    A shared fixture supplies the same full registry to every case; findings
    still contain only the requested subjects and join its fixed equipment IDs.
    """
    findings, registry = {}, deepcopy(shared_registry_rows) if shared_registry_rows is not None else {}
    for index, subject in enumerate(subject_types or ["Unrecognized synthetic subject"], 1):
        fid, eid = f"F-{9000 + index}", f"SYN-{9000 + index}"
        if shared_registry_rows is not None:
            matches = [key for key, row in registry.items() if row["equipment_type"] == subject]
            if len(matches) != 1:
                raise ValueError("Target must join exactly one fixed registry fixture row")
            eid = matches[0]
        findings[fid] = {
            "finding_id": fid, "reported_date": "2026-07-01", "equipment_id": eid,
            "equipment_type": subject, "inspection_type": "Routine Operator Round",
            "inspection_method": "Synthetic selector fixture",
            "finding_description": "Artificial selector query; no actual fault is asserted.",
            "reported_by": "Synthetic Fixture", "reporter_role": "Software test",
        }
        if shared_registry_rows is None:
            registry[eid] = {
                "equipment_id": eid, "equipment_type": subject,
                "service_description": "Artificial selection subject", "criticality_score": "5",
                "reliability_score": "5", "safety_critical_element": "No", "redundancy": "None",
                "engineer_comment": "Authorized synthetic query, not field evidence.",
            }
    return {"findings": findings, "registry": registry}


def query_binding(query: dict[str, Any]):
    """Independently serialize authorized synthetic snapshots for runtime binding."""
    contracts = importlib.import_module("triage_knowledge.contracts")
    retrieval = importlib.import_module("triage_knowledge.retrieval")
    tables = []
    for key, identity, kind in (("findings", "synthetic-findings", "finding_input"), ("registry", "synthetic-registry", "registry_input")):
        rows = list(query[key].values())
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        tables.append(contracts.TableSource.from_bytes(stream.getvalue().encode("utf-8"), source_id=identity, kind=kind))
    return retrieval.binding_from_tables(*tables)


def code_identity(root: Path = ROOT) -> dict[str, Any]:
    """Bind current executable bytes, revision and dirty state without reading secrets."""
    def git(*args):
        result = subprocess.run(["git", "--no-pager", *args], cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    inventory = {}
    for directory in ("eval", "triage_knowledge", "llm_inference"):
        paths = list((root / directory).glob("*.py"))
        if directory == "eval":
            paths.extend((root / directory / "knowledge").glob("*.py"))
            paths.extend((root / directory / "tests").glob("*.py"))
            paths.extend((root / directory / "tests" / "knowledge").glob("*.py"))
        for path in sorted(paths):
            inventory[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "revision": git("rev-parse", "HEAD"), "dirty_status": git("status", "--porcelain"),
        "files_sha256": inventory, "code_sha256": canonical_hash(inventory),
    }


def _source_records(suite: Suite) -> list[dict[str, Any]]:
    return [{key: source[key] for key in ("source_id", "path", "partition", "sha256")} for source in suite.manifest["sources"]]


def collect_c0(suite: Suite, capture: Callable[[str, Any], None] | None = None):
    """Run actual C0 once per source. Return raw observations and validated objects."""
    runtime = _runtime_source()
    observations, extractions = [], {}
    for record in suite.manifest["sources"]:
        sid = record["source_id"]
        row: dict[str, Any] = {"source_id": sid}
        try:
            document = document_for(suite, sid)
            extraction = runtime.extract_code(document)
            extractions[sid] = extraction
            row.update(raw_proposal=extraction.proposal, materialized_groups=extraction.groups)
            observed = adapt_extraction(extraction)
            row.update(observation=observed, assessment=assess_extraction(suite, observed))
        except (ValueError, KeyError, TypeError) as error:
            row.update(adapter_or_intake_error=str(error), assessment={"status": "fail"})
        observations.append(row)
        if capture:
            capture(f"C0\\{sid}.json", row)
    return observations, extractions


def _partition_members(suite: Suite, partition: str) -> set[str]:
    members = suite.members(partition)
    if "original_domain" not in members or len(members) != 5:
        raise ValueError("A partition must contain four synthetic sources plus original_domain")
    return members


def _reviewed_partition(suite: Suite, partition: str, record: dict[str, Any]):
    if record.get("review_kind") not in {"human", "synthetic_software_fixture"} or not record.get("review_disclosure"):
        raise ValueError("Explicit reviewed-input provenance is required")
    path = (ROOT / record["store"]).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Reviewed stores must be repository-local")
    store = importlib.import_module("triage_knowledge.source_store").SourceKnowledgeStore(path)
    release = store.resolve_release(record["release_id"])
    sources = release["candidate"]["sources"]
    if set(sources) != _partition_members(suite, partition):
        raise ValueError("Reviewed release mixes partitions or has unexpected sources")
    if any(sources[sid]["source_sha256"] != hashlib.sha256(suite.sources[sid]).hexdigest() for sid in sources):
        raise ValueError("Reviewed release does not bind frozen submitted sources")
    return store


def _candidate_content(candidate: dict[str, Any]) -> str:
    """Bind all source/revision/edge content while allowing review declarations."""
    return canonical_hash({
        "schema_version": candidate["schema_version"],
        "sources": candidate["sources"],
        "items": {
            key: {name: item[name] for name in ("revision_id", "revision")}
            for key, item in candidate["items"].items()
        },
        "context_links": candidate["context_links"],
        "replacements": candidate["replacements"],
    })


def run_offline(
    suite: Suite, writer: EvidenceWriter, *, identity: dict[str, Any],
    assessment_time: str = ASSESSMENT_TIME, reviewed_inputs: dict[str, Any] | None = None,
    synthetic_review_diagnostic: bool = False,
) -> dict[str, Any]:
    """Observe raw C0, original smoke, unreviewed drafts and every frozen query.

    Existing reviewed releases may be supplied explicitly. Only the explicit
    synthetic diagnostic invokes review/publish, in a new run-local store. It
    neither edits raw revisions/metadata nor constitutes human review.
    """
    if synthetic_review_diagnostic and reviewed_inputs is not None:
        raise ValueError("Synthetic review diagnostic and reviewed inputs are mutually exclusive")
    if reviewed_inputs is not None and reviewed_inputs.get("contract") != "knowledge-eval-reviewed-input-v1":
        raise ValueError("Unsupported reviewed-input contract")
    registry_fixture = load_registry_fixture(suite)
    registry_rows = registry_fixture["fixture"]["registry"] if registry_fixture else None
    registry_pin = ({key: registry_fixture[key] for key in ("path", "sha256", "registry_sha256")}
                    if registry_fixture else None)
    if registry_fixture:
        writer.write("query-registry-fixture.json", registry_fixture)

    def capture_source(name, row):
        writer.write(name, dict(row, synthetic_review_diagnostic=synthetic_review_diagnostic,
                                human_approval_established=False))

    source_observations, extractions = collect_c0(suite, capture_source)
    for row in source_observations:
        row["synthetic_review_diagnostic"] = synthetic_review_diagnostic
    normalized = [row["observation"] for row in source_observations if "observation" in row]
    query_observations, retrievals, partitions = {}, {}, {}
    store_type = importlib.import_module("triage_knowledge.source_store").SourceKnowledgeStore
    for partition in ("development", "evaluation"):
        members = _partition_members(suite, partition)
        record = (reviewed_inputs or {}).get("partitions", {}).get(partition)
        store = None
        partitions[partition] = {
            "source_ids": sorted(members), "review_status": "unexecuted",
            "synthetic_review_diagnostic": synthetic_review_diagnostic,
            "human_approval_established": False, "qualification_eligible": False,
        }
        if record:
            store = _reviewed_partition(suite, partition, record)
            partitions[partition].update(
                review_status=record["review_kind"], review_disclosure=record["review_disclosure"],
                release_id=record["release_id"],
                qualification_eligible=False,
                limitation="Declared review provenance is not authenticated human effort or publication certification.",
            )
        elif members <= extractions.keys():
            directory = "synthetic-review-diagnostic" if synthetic_review_diagnostic else "unreviewed-drafts"
            draft_store = store_type(writer.root / directory / partition)
            digest = draft_store.create_draft([extractions[sid] for sid in sorted(members)])
            candidate, loaded_digest = draft_store.load_draft()
            if digest != loaded_digest or any(item["review_state"] != "pending" for item in candidate["items"].values()):
                raise ValueError("New raw intake unexpectedly carries review")
            partitions[partition].update(candidate_digest=digest, item_count=len(candidate["items"]))
            if synthetic_review_diagnostic:
                before = _candidate_content(candidate)
                for item_id in sorted(candidate["items"]):
                    digest = draft_store.review_item(
                        item_id, reviewer=SOFTWARE_REVIEWER, reason=SOFTWARE_REASON,
                        expected_digest=digest,
                    )
                declared, declared_digest = draft_store.load_draft()
                if declared_digest != digest or _candidate_content(declared) != before:
                    raise ValueError("Software review unexpectedly changed raw source/revision/context content")
                if any(item["review_state"] != "reviewed" for item in declared["items"].values()):
                    raise ValueError("Software fixture declarations did not bind every raw item")
                release_id = draft_store.publish(
                    expected_digest=digest, author=SOFTWARE_REVIEWER, reviewer=SOFTWARE_REVIEWER,
                    reason=SOFTWARE_REASON,
                    reviewed_at=identity.get("started_at") or datetime.now(timezone.utc).isoformat(),
                )
                runtime = importlib.import_module("triage_knowledge.retrieval")
                record = {
                    "release_id": release_id, "expected_strategy": runtime.strategy_binding(),
                    "review_kind": "synthetic_software_fixture", "review_disclosure": SOFTWARE_REASON,
                }
                store = draft_store
                partitions[partition].update(
                    review_status="synthetic_software_fixture", review_disclosure=SOFTWARE_REASON,
                    reviewer=SOFTWARE_REVIEWER, release_id=release_id,
                    raw_content_sha256=before, reviewed_candidate_digest=digest,
                )
        for case_id, query_spec in suite.queries.items():
            if query_spec["source_id"] not in members:
                continue
            query = query_rows(query_spec["subject_types"], shared_registry_rows=registry_rows)
            binding = query_binding(query)
            observed: dict[str, Any] = {
                "case_id": case_id, "query_context": query,
                "authorized_input_binding": binding.to_dict(),
                "query_registry_fixture": registry_pin,
                "partition": partition, "result": None,
                "assessment": {"status": "needs_review", "reason": "No genuinely reviewed release was supplied; unreviewed drafts are not published."},
                "execution": "not_run_pending_review",
                "synthetic_review_diagnostic": synthetic_review_diagnostic,
                "synthetic_review_only": synthetic_review_diagnostic,
                "human_approval_established": False, "selective_qualification": False,
            }
            if store is not None:
                runtime = importlib.import_module("triage_knowledge.retrieval")
                result = runtime.get_triage_knowledge(
                    store, query, knowledge_version=record["release_id"],
                    assessment_time=assessment_time, expected_strategy=record["expected_strategy"],
                    allowed_input_binding=binding, max_bytes=64000,
                )
                adapted = adapt_result(result)
                retrievals[case_id] = adapted
                observed.update(
                    result=result.to_dict(), provider_payload=result.provider_payload(),
                    local_evidence=result.evidence, execution="observed",
                    assessment=assess_retrieval(suite, case_id, adapted),
                    synthetic_review_only=record["review_kind"] == "synthetic_software_fixture",
                    selective_qualification=False,
                )
            query_observations[case_id] = observed
            writer.write(f"queries\\{case_id}.json", observed)
    graded = assess_observations(suite, {"profiles": {"C0": {"extractions": normalized, "retrievals": retrievals}}})
    graded["synthetic_review_diagnostic"] = synthetic_review_diagnostic
    graded["qualification_established"] = False
    failed = any(row["assessment"]["status"] == "fail" for row in source_observations) or any(row["assessment"]["status"] == "fail" for row in query_observations.values())
    report = {
        "contract": "knowledge-source-first-run-v1", "identity": identity,
        "reference_version": suite.manifest["version"], "grader_version": suite.manifest.get("grader_version"),
        "sources": _source_records(suite), "partitions": partitions,
        "query_registry_fixture": registry_pin,
        "source_assessments": source_observations, "query_count": len(query_observations),
        "query_assessments": {key: value["assessment"] for key, value in query_observations.items()},
        "original_smoke": next(row for row in source_observations if row["source_id"] == "original_domain"),
        "component_report": graded, "status": "failed_component_checks" if failed else "pending_review",
        "human_effort": "unexecuted", "strict_qualification": "unexecuted",
        "synthetic_review_diagnostic": synthetic_review_diagnostic,
        "human_approval_established": False, "system_qualified": False,
        "review_disclosure": SOFTWARE_REASON if synthetic_review_diagnostic else None,
        "selective_retrieval_qualified": False, "C1_qualified": False,
        "system_B01_B02": "not_established", "overall": "pending",
    }
    writer.write("observation.json", report)
    return report


def build_experiment(suite: Suite, identity: dict[str, Any]):
    """Freeze 13 same-profile source-only requests, with development/original first."""
    runtime = _runtime_source()
    ordered = [
        source["source_id"] + ".primary"
        for partition in ("development", "shared_smoke", "evaluation")
        for source in suite.manifest["sources"] if source["partition"] == partition
    ] + [slot for slot in suite.manifest["slot_ids"] if ".repeat" in slot]
    if len(ordered) != 13 or set(ordered) != set(suite.manifest["slot_ids"]):
        raise ValueError("Unexpected frozen experiment denominator")
    documents = {sid: document_for(suite, sid) for sid in suite.sources}
    requests = {
        slot: runtime.extraction_request(documents[slot.rsplit(".", 1)[0]],
                                         model=MODEL, reasoning_effort="low", timeout_seconds=90)
        for slot in ordered
    }
    prefix = frozenset(ordered[:5])
    from .copilot import request_record
    registry_fixture = load_registry_fixture(suite)
    freeze = {
        "contract": "knowledge-source-first-experiment-freeze-v1",
        "identity": identity, "reference_version": suite.manifest["version"],
        "manifest_sha256": hashlib.sha256((ROOT / "eval" / "spec" / "knowledge_extraction.json").read_bytes()).hexdigest(),
        "source_hashes": {sid: hashlib.sha256(data).hexdigest() for sid, data in suite.sources.items()},
        "schedule": ordered, "development_slots": sorted(prefix),
        "model": MODEL, "reasoning_effort": "low", "timeout_seconds": 90,
        "maximum_application_attempts": 26, "maximum_attempts_per_slot": 2,
        "request_hashes": {slot: canonical_hash(request_record(request)) for slot, request in requests.items()},
        "query_registry_fixture": (
            {key: registry_fixture[key] for key in ("path", "sha256", "registry_sha256")}
            if registry_fixture else None
        ),
        "strict_http_token_usd_accounting": "unknown_not_qualified",
        "human_effort": "unexecuted", "C1_qualified": False,
    }
    return requests, documents, prefix, freeze


def make_validator(suite: Suite, documents: dict[str, Any], capture: Callable[[str, Any], None] | None = None):
    """Accept only after real source validation and independent critical-error check.

    Evaluation findings never enter a new/retried provider request. Missing safe
    metadata is a disclosed diagnostic under grader v1.1, not semantic feedback.
    """
    def validate(slot: str, raw: Any) -> dict[str, Any]:
        sid = slot.rsplit(".", 1)[0]
        record: dict[str, Any] = {"slot_id": slot, "raw_proposal": raw}
        try:
            extraction = _runtime_source().validate_proposal(documents[sid], raw)
            normalized = adapt_extraction(extraction)
            grade = assess_extraction(suite, normalized)
            record.update(observation=normalized, assessment=grade)
            if grade["status"] != "pass":
                raise ValueError("Independent source-span assessment did not pass critical/unresolved gates")
        except ValueError as error:
            record.update(accepted=False, error=str(error))
            if capture:
                capture(f"C1\\{slot}.json", record)
            raise
        record["accepted"] = True
        if capture:
            capture(f"C1\\{slot}.json", record)
        return {"accepted": True, "source_id": sid, "observation": normalized, "assessment": grade}
    return validate


async def run_experiment(suite: Suite, writer: EvidenceWriter, *, identity: dict[str, Any], allow_inference: bool = False):
    """Explicit experimental Copilot dispatch. Never invoked by offline evaluation."""
    if not allow_inference:
        raise ValueError("Explicit --allow-inference is required")
    requests, documents, development, freeze = build_experiment(suite, identity)
    writer.write("freeze.json", freeze)
    from .copilot import run_requests
    from llm_inference import CopilotProvider
    async with CopilotProvider() as provider:
        result = await run_requests(
            provider, requests, output=writer.root / "calls", ledger_path=ROOT / LEDGER,
            phase="source-first-copilot-" + canonical_hash(freeze),
            validate_response=make_validator(suite, documents, writer.write),
            development_slots=development, allow_inference=True,
        )
    writer.write("experiment-observation.json", {
        "freeze_sha256": canonical_hash(freeze), "driver": result,
        "strict_accounting_pass": False, "human_effort": "unexecuted",
        "C1_qualified": False, "overall": "pending",
    })
    return result


def main(argv: list[str] | None = None) -> int:
    """Return 1 for observed failure/invalid input; 2 for honest pending component work."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    review_mode = parser.add_mutually_exclusive_group()
    review_mode.add_argument("--reviewed-inputs", type=Path)
    review_mode.add_argument("--synthetic-review-diagnostic", action="store_true")
    parser.add_argument("--assessment-time", default=ASSESSMENT_TIME)
    parser.add_argument("--copilot-experiment", action="store_true")
    parser.add_argument("--allow-inference", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.synthetic_review_diagnostic and args.copilot_experiment:
            raise ValueError("Synthetic review diagnostic is offline-only, not a Copilot experiment")
        if args.allow_inference and not args.copilot_experiment:
            raise ValueError("--allow-inference requires --copilot-experiment")
        if args.copilot_experiment and not (args.allow_inference or args.plan_only):
            raise ValueError("Copilot needs explicit --allow-inference or --plan-only")
        if args.plan_only and not args.copilot_experiment:
            raise ValueError("--plan-only is for the Copilot experiment")
        suite = load_suite()
        identity = {
            "run_id": str(uuid4()), "started_at": datetime.now(timezone.utc).isoformat(),
            "code": code_identity(), "assessment_time": args.assessment_time,
            "exposure": suite.manifest["exposure"],
        }
        if args.plan_only:
            _, _, _, freeze = build_experiment(suite, identity)
            print(json.dumps(freeze, indent=2, allow_nan=False))
            return 0
        default_run = "source-first-copilot-1" if args.copilot_experiment else "source-first-software-review-1" if args.synthetic_review_diagnostic else "source-first-c0-1"
        output = (ROOT / (args.output or RESULTS / default_run)).resolve()
        if not output.is_relative_to((ROOT / RESULTS).resolve()) or output == (ROOT / RESULTS).resolve():
            raise ValueError("Output must be a new child under eval\\results\\knowledge\\extraction")
        writer = EvidenceWriter(output)
        writer.write("run-identity.json", identity)
        for sid, data in suite.sources.items():
            writer.write(f"sources\\{sid}.bin", data)
        if args.copilot_experiment:
            result = asyncio.run(run_experiment(suite, writer, identity=identity, allow_inference=args.allow_inference))
            print(json.dumps({"status": result["status"], "output": str(output), "C1_qualified": False}))
            return 1 if any(row["status"] == "failed" for row in result["results"].values()) else 2
        reviewed = read_json(args.reviewed_inputs) if args.reviewed_inputs else None
        result = run_offline(
            suite, writer, identity=identity, assessment_time=args.assessment_time,
            reviewed_inputs=reviewed, synthetic_review_diagnostic=args.synthetic_review_diagnostic,
        )
        print(json.dumps({"status": result["status"], "output": str(output), "overall": "pending"}))
        return 1 if result["status"] == "failed_component_checks" else 2
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(json.dumps({"status": "failed", "error": str(error), "C1_qualified": False, "overall": "pending"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
