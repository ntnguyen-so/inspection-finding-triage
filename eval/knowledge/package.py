"""Write-once, offline mechanical package integration; never triage or certify content."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import subprocess
import sys

from triage_knowledge.contracts import (
    KnowledgeError, TableSource, canonical_bytes, require, sha256, strict_json, timestamp,
)
from triage_knowledge.retrieval import binding_from_tables, get_triage_knowledge, strategy_binding
from triage_knowledge.source import SourceDocument, extract_code
from triage_knowledge.source_context import build_source_context, validate_source_context
from triage_knowledge.source_store import SourceKnowledgeStore


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "eval" / "results" / "knowledge"
PACK = ROOT / "docs" / "candidate-pack" / "candidate-pack"
SOURCE_PATHS = {
    "domain": PACK / "reference" / "domain_knowledge.md",
    "findings": PACK / "data" / "inspection_findings.csv",
    "registry": PACK / "data" / "equipment_registry.csv",
    "split": ROOT / "eval" / "spec" / "split.json",
}
# Reference bytes verified against commit 237ff52, never derived from run inputs.
EXPECTED_SPLIT_SHA256 = "bf708a150f0ac08a1f65f1d585f2cdde6fb6984578ea379465a066cf9a622e43"
SOURCE_KEYS = {"domain": r"reference\domain_knowledge.md",
               "findings": r"data\inspection_findings.csv",
               "registry": r"data\equipment_registry.csv"}
DISCLOSURE = (
    "SOFTWARE-ONLY isolated review declarations, not human content review, engineering "
    "approval, workflow activation, C1 qualification, provider handoff or system acceptance. "
    "No LLM, triage scores, expected answers or evaluation cards are used."
)
LIFECYCLE_DISCLOSURE = (
    "Explicit SOFTWARE fixture removes C0 conservative source-context edges before changes. "
    "This intentionally contrived isolation is not an engineering-approved dependency change. "
    "Whitespace-only editing and replacement between two existing items test storage/retrieval "
    "mechanics, not semantic equivalence, correct withdrawal or real replacement approval."
)
POLICY = {"version": "package-mechanical-fixture-v1", "instructions": DISCLOSURE}
MAX_BYTES = 1_000_000
GOALS = {
    "source_coverage": "Exact original domain byte coverage, once per source span.",
    "pending_blocked": "Initial pending intake cannot publish or provide usable knowledge.",
    "batch_and_single_contexts": "All/single/development/test batches preserve every input field and join.",
    "row_order_and_repeat": "Row reversal changes raw manifests, not semantic context; repeats are identical.",
    "tamper_rejection": "Modified and rehashed knowledge/comment/policy/index packets are rejected.",
    "fail_closed": "Bad release/strategy/version/overflow have no usable partial result.",
    "lifecycle": "Whitespace edit, retirement, future, expiry and contrived replacement exclude inactive text.",
    "freeze_unchanged": "Frozen executable and input bytes remain unchanged throughout the run.",
}


def _write(root: Path, name: str, value) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value if type(value) is bytes else canonical_bytes(value))


def _hashes(paths: dict[str, Path]) -> dict:
    return {name: sha256(path.read_bytes()) for name, path in sorted(paths.items())}


def code_paths() -> dict[str, Path]:
    paths = list((ROOT / "triage_knowledge").glob("*.py"))
    paths += [Path(__file__), ROOT / "eval" / "tests" / "knowledge" / "test_package.py"]
    return {str(path.relative_to(ROOT)): path for path in paths}


def make_plan(paths: dict[str, Path], assessment_time: str, counts: dict) -> dict:
    timestamp(assessment_time, "assessment_time")
    input_hashes = _hashes(paths)
    split_raw = paths["split"].read_bytes()
    require(input_hashes["split"] == sha256(split_raw) == EXPECTED_SPLIT_SHA256, "split_integrity",
            "The supplied split differs from the trusted committed reference.")
    declared = strict_json(split_raw)["sources_sha256"]
    require(all(input_hashes[name] == declared[key] for name, key in SOURCE_KEYS.items()),
            "original_integrity", "Package source bytes differ from the trusted split fingerprints.")
    return {
        "contract": "knowledge-package-mechanical-v1", "assessment_time": assessment_time,
        "goals": GOALS, "disclosure": DISCLOSURE, "lifecycle_disclosure": LIFECYCLE_DISCLOSURE,
        "scenario_mapping": ["B01", "B02", "B03", "D04", "X02"],
        "input_sha256": input_hashes, "code_sha256": _hashes(code_paths()),
        "expected_counts": counts, "strategy": strategy_binding(),
        "assessment_policy": POLICY, "max_bytes": MAX_BYTES,
        "calls": 0, "cost": 0,
        "cache": "none", "provider_handoff": "not executed",
    }


def _table(rows: list[dict], original: TableSource) -> TableSource:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return TableSource.from_bytes(stream.getvalue().encode("utf-8"),
                                  source_id=original.source_id, kind=original.kind)


def _review_publish(store, assessment_time):
    candidate, digest = store.load_draft()
    for item_id, item in candidate["items"].items():
        if item["review_state"] == "pending":
            digest = store.review_item(item_id, reviewer="SOFTWARE fixture, NOT human review",
                                       reason=DISCLOSURE, expected_digest=digest)
    return store.publish(expected_digest=digest, author="SOFTWARE integration harness",
                         reviewer="SOFTWARE fixture, NOT human review", reason=DISCLOSURE,
                         reviewed_at=assessment_time)


def _reject(call, expected_code: str) -> str:
    try:
        call()
    except KnowledgeError as error:
        require(error.code == expected_code, "unexpected_diagnostic",
                "A rejection used a different diagnostic.", error.code)
        return error.code
    raise KnowledgeError("missing_rejection", "A required fail-closed check unexpectedly succeeded.")


def _rehashed(packet):
    body = {key: value for key, value in packet.items() if key != "context_hash"}
    return canonical_bytes({**body, "context_hash": sha256(canonical_bytes(body))})


def _git_identity() -> dict:
    try:
        def read(*args):
            return subprocess.run(["git", "--no-optional-locks", "--no-pager", *args],
                                  cwd=ROOT, capture_output=True, encoding="utf-8",
                                  errors="replace", check=True, timeout=10).stdout.strip()
        return {"revision": read("rev-parse", "HEAD"),
                "dirty": bool(read("status", "--porcelain")), "read_only": True}
    except (OSError, subprocess.SubprocessError) as error:
        return {"revision": None, "dirty": None, "error_class": type(error).__name__}


def _assert_revision_projection(packet, candidate, required, store, cutoff, excluded=()):
    def address(item_id):
        return f"knowledge:{item_id}@{candidate['items'][item_id]['revision_id']}:text"
    expected = {address(item_id): item["revision"]["text"]
                for item_id, item in candidate["items"].items()
                if store.eligible(candidate, item_id, cutoff)}
    actual, index = packet["payload"]["knowledge"], packet["source_index"]
    require(all(key in expected and text == expected[key] and index.get(key) == text
                for key, text in actual.items()), "revision_projection",
            "Selected knowledge must match exact eligible current revision addresses and text.")
    require(all(actual.get(address(item_id)) == text
                and index.get(address(item_id)) == text for item_id, text in required.items()),
            "missing_lifecycle_target", "A required lifecycle target is missing or has changed text.")
    require(not any(key.startswith(f"knowledge:{item_id}@")
                    for item_id in excluded for key in (*actual, *index)),
            "inactive_leak", "An excluded logical item retained a provider address.")


def run_package(output: Path, paths: dict[str, Path], plan: dict) -> dict:
    """Execute only after a separately recorded plan has been reviewed and frozen."""
    output = Path(output).resolve()
    require(output.is_relative_to(RESULTS.resolve()) and output != RESULTS.resolve(),
            "output_path", "Output must be a new child of eval/results/knowledge.")
    output.mkdir(parents=True, exist_ok=False)
    _write(output, "plan.json", plan)
    report = {"contract": plan["contract"], "status": "failed", "disclosure": DISCLOSURE,
              "declared_goals": GOALS,
              "lifecycle_disclosure": LIFECYCLE_DISCLOSURE, "cases": [], "diagnostics": [],
              "goals": {key: "not_run" for key in GOALS}, "provider_calls": 0,
              "git": _git_identity(),
              "human_review": "not established", "system_acceptance": "not established"}
    started = datetime.now(timezone.utc)
    stage = "freeze"
    try:
        require(plan == make_plan(paths, plan["assessment_time"], plan["expected_counts"]),
                "freeze_mismatch", "Code, inputs or run settings differ from the frozen plan.")
        core = {name: Path(sys.modules[f"triage_knowledge.{name}"].__file__).resolve()
                for name in ("contracts", "retrieval", "source", "source_context", "source_store")}
        report["runtime"] = {"python_version": sys.version, "python_executable": sys.executable,
                             "core_module_files": {name: str(path) for name, path in core.items()}}
        require(all(path == (ROOT / "triage_knowledge" / (name + ".py")).resolve()
                    for name, path in core.items()), "runtime_import",
                "Imported core modules must be the frozen checkout files, not archived or installed copies.")
        stage = "intake"
        document = SourceDocument.from_bytes(paths["domain"].read_bytes(),
                                              source_id="domain", name="Unchanged package domain")
        findings = TableSource.from_bytes(paths["findings"].read_bytes(),
                                          source_id="findings", kind="finding_input")
        registry = TableSource.from_bytes(paths["registry"].read_bytes(),
                                          source_id="registry", kind="registry_input")
        split = strict_json(paths["split"].read_bytes())
        frows = findings.rows
        memberships = {key: set(split["partitions"][key])
                       for key in ("development", "test")}
        all_ids = {row["finding_id"] for row in frows}
        require(not memberships["development"] & memberships["test"]
                and set.union(*memberships.values()) == all_ids, "split_membership",
                "Development/test membership must partition the supplied findings exactly.")
        require({"all": len(frows), **{key: len(value) for key, value in memberships.items()}}
                == plan["expected_counts"], "input_count", "Unexpected package row counts.")
        binding = binding_from_tables(findings, registry)
        extraction = extract_code(document)
        spans = sorted((span["start"], span["end"])
                       for group in extraction.groups for span in group["spans"])
        cursor = 0
        for start, end in spans:
            require(start == cursor and end > start, "source_coverage",
                    "Source extraction omitted or duplicated bytes.")
            cursor = end
        require(cursor == len(document.raw), "source_coverage", "Source byte coverage is incomplete.")
        report["source_coverage"] = {"covered_bytes": cursor, "original_bytes": len(document.raw)}
        report["goals"]["source_coverage"] = "pass"
        store = SourceKnowledgeStore(output / "software-store")
        digest = store.create_draft([extraction])
        cutoff = plan["assessment_time"]
        report["diagnostics"].append({"case": "pending_publish", "error_code": _reject(
            lambda: store.publish(expected_digest=digest, author="SOFTWARE",
                                  reviewer="SOFTWARE", reason=DISCLOSURE, reviewed_at=cutoff),
            "pending_review")})
        unavailable = get_triage_knowledge(
            store, {"findings": {row["finding_id"]: row for row in frows},
                    "registry": {row["equipment_id"]: row for row in registry.rows}},
            knowledge_version="sha256-" + digest, assessment_time=cutoff,
            expected_strategy=plan["strategy"], allowed_input_binding=binding, max_bytes=MAX_BYTES)
        require(unavailable.status == "unavailable"
                and unavailable.error_code == "unknown_or_invalid_release"
                and not unavailable.provider_payload()
                and not unavailable.to_dict()["source_index"], "pending_usable",
                "Pending intake produced usable knowledge.")
        report["diagnostics"].append({"case": "pending_retrieval", "error_code": unavailable.error_code})
        report["goals"]["pending_blocked"] = "pass"
        release = _review_publish(store, cutoff)
        report["baseline_release"] = release
        pins = {"knowledge_version": release, "assessment_time": cutoff,
                "expected_strategy": plan["strategy"], "max_bytes": MAX_BYTES}

        def build(table=findings, **overrides):
            return build_source_context(store, table, registry, assessment_policy=POLICY,
                                        **{**pins, **overrides})

        def validate(bundle, table=findings, registry_table=registry, **overrides):
            return validate_source_context(
                bundle, table, registry_table, store, expected_assessment_policy=POLICY,
                **{**pins, **overrides})

        stage = "contexts"
        baseline = build()
        batches = [("all", findings)]
        batches += [(f"single-{number:02d}", _table([row], findings))
                    for number, row in enumerate(frows, 1)]
        batches += [(key, _table([row for row in frows if row["finding_id"] in selected], findings))
                    for key, selected in memberships.items()]
        for name, selected in batches:
            stage = "context:" + name
            bundle = build(selected)
            checked = validate(bundle, selected)
            packet = checked.to_dict()
            require(packet["payload"]["findings"]
                    == {row["finding_id"]: row for row in selected.rows}
                    and packet["payload"]["registry"]
                    == {row["equipment_id"]: row for row in registry.rows},
                    "input_delivery", "Context changed an input field or comment.")
            for kind, rows, key in (("finding", selected.rows, "finding_id"),
                                    ("equipment", registry.rows, "equipment_id")):
                require(all(packet["source_index"][f"{kind}:{row[key]}:{field}"] == value
                            for row in rows for field, value in row.items()),
                        "input_delivery", "Source index changed an input field.")
            report["cases"].append({
                "case": name, "status": "pass", "context_hash": packet["context_hash"],
                "encoded_sha256": sha256(checked.encoded), "finding_ids": packet["finding_ids"],
                "knowledge_result_hash": packet["knowledge_result_hash"],
                "selected_addresses": sorted(packet["payload"]["knowledge"]),
            })
            if name in ("all", "development"):
                _write(output, name + "-context.json", checked.encoded)
                _write(output, name + "-evidence.json", checked.evidence_bytes)
        report["goals"]["batch_and_single_contexts"] = "pass"
        stage = "row_order"
        reversed_f = _table(list(reversed(frows)), findings)
        reversed_r = _table(list(reversed(registry.rows)), registry)
        reversed_bundle = build_source_context(
            store, reversed_f, reversed_r, assessment_policy=POLICY, **pins)
        repeated = build()
        require(reversed_bundle.encoded == baseline.encoded == repeated.encoded
                and repeated.evidence_bytes == baseline.evidence_bytes,
                "semantic_instability", "Row ordering or repetition changed semantic context.")
        require(all(left["sha256"] != right["sha256"] for left, right in zip(
                    reversed_bundle.evidence()["source_manifest"],
                    baseline.evidence()["source_manifest"], strict=True)),
                "manifest_identity", "Row reversal did not change raw evidence manifests.")
        require(validate(baseline, reversed_f, reversed_r).evidence_bytes
                == reversed_bundle.evidence_bytes, "manifest_identity",
                "Consumer did not independently rebuild local evidence from the reversed inputs.")
        report["row_order"] = {"baseline": baseline.evidence()["source_manifest"],
                               "reversed": reversed_bundle.evidence()["source_manifest"]}
        report["goals"]["row_order_and_repeat"] = "pass"
        stage = "faults"
        for name in ("knowledge", "comment", "policy", "index"):
            packet = baseline.to_dict()
            address = next(iter(packet["payload"]["knowledge"]))
            if name == "knowledge":
                packet["payload"]["knowledge"][address] += "\n"
                packet["source_index"][address] += "\n"
            elif name == "comment":
                identifier = next(iter(packet["payload"]["registry"]))
                packet["payload"]["registry"][identifier]["engineer_comment"] += "\n"
                packet["source_index"][f"equipment:{identifier}:engineer_comment"] += "\n"
            elif name == "policy":
                packet["assessment_policy"]["instructions"] += "\n"
            else:
                packet["source_index"][address] += "\n"
            report["diagnostics"].append({"case": "rehashed_" + name,
                                          "error_code": _reject(
                                              lambda: validate(_rehashed(packet)),
                                              "assessment_policy" if name == "policy" else "context_contract")})
        report["goals"]["tamper_rejection"] = "pass"
        for name, options, code in (
            ("release", {"knowledge_version": "sha256-" + "0" * 64}, "unknown_or_invalid_release"),
            ("strategy", {"expected_strategy": {}}, "strategy_binding_mismatch"),
            ("overflow", {"max_bytes": 1}, "result_too_large"),
        ):
            report["diagnostics"].append({"case": name, "error_code": _reject(
                lambda: build(**options), code)})
        packet = baseline.to_dict()
        packet["contract_version"] = 0
        report["diagnostics"].append({"case": "version", "error_code": _reject(
            lambda: validate(_rehashed(packet)), "unsupported_contract")})
        for name, version, strategy, limit, code in (
            ("unavailable_release", "sha256-" + "0" * 64, pins["expected_strategy"], MAX_BYTES,
             "unknown_or_invalid_release"),
            ("unavailable_strategy", release, {}, MAX_BYTES, "strategy_binding_mismatch"),
            ("unavailable_overflow", release, pins["expected_strategy"], 1, "result_too_large"),
        ):
            result = get_triage_knowledge(
                store, {"findings": {row["finding_id"]: row for row in frows},
                        "registry": {row["equipment_id"]: row for row in registry.rows}},
                knowledge_version=version, assessment_time=cutoff, expected_strategy=strategy,
                allowed_input_binding=binding, max_bytes=limit)
            require(result.status == "unavailable" and result.error_code == code
                    and not result.provider_payload()
                    and not result.to_dict()["source_index"], "partial_failure",
                    "Unavailable retrieval exposed usable partial knowledge.")
            report["diagnostics"].append({"case": name, "error_code": result.error_code})
        report["goals"]["fail_closed"] = "pass"
        stage = "lifecycle"
        candidate, digest = store.load_draft()
        require(all(edge["kind"] == "conservative_source_context"
                    for edge in candidate["context_links"]), "fixture_dependency",
                "Only C0 conservative edges may be cleared by this software fixture.")
        digest = store.set_context_links([], expected_digest=digest)
        identifiers = sorted(candidate["items"])
        require(len(identifiers) >= 6, "fixture_size",
                "Six source items are required for independent lifecycle mechanics.")
        edited, retired, future, expired, predecessor, successor = identifiers[:6]
        _assert_revision_projection(
            baseline.to_dict(), candidate,
            {item_id: candidate["items"][item_id]["revision"]["text"] for item_id in identifiers[:6]},
            store, cutoff)
        edited_text = candidate["items"][edited]["revision"]["text"] + "\n"
        digest = store.edit_item(edited, edited_text,
                                 reason=LIFECYCLE_DISCLOSURE, expected_digest=digest)
        edited_release = _review_publish(store, cutoff)
        changed = build(knowledge_version=edited_release)
        require(changed.encoded != baseline.encoded, "edit_identity", "A fresh edit did not change context.")
        validate(changed, knowledge_version=edited_release)
        _assert_revision_projection(
            changed.to_dict(), store.resolve_release(edited_release)["candidate"],
            {edited: edited_text}, store, cutoff)
        old_edited_address = f"knowledge:{edited}@{candidate['items'][edited]['revision_id']}:text"
        require(old_edited_address not in changed.to_dict()["source_index"]
                and old_edited_address not in changed.to_dict()["payload"]["knowledge"],
                "old_revision_leak", "The edited release retained its predecessor revision address.")
        _, digest = store.load_draft()
        later = (timestamp(cutoff, "assessment_time") + timedelta(days=1)).isoformat()
        for item_id, kwargs in ((retired, {"status": "retired"}),
                                (future, {"effective_from": later}),
                                (expired, {"effective_until": cutoff})):
            digest = store.set_lifecycle(item_id, reason=LIFECYCLE_DISCLOSURE,
                                         expected_digest=digest, **kwargs)
        digest = store.replace_item(predecessor, successor, effective_from=cutoff,
                                     reason=LIFECYCLE_DISCLOSURE, expected_digest=digest)
        lifecycle_release = _review_publish(store, cutoff)
        lifecycle = build(knowledge_version=lifecycle_release)
        validate(lifecycle, knowledge_version=lifecycle_release)
        payload = lifecycle.to_dict()
        current_candidate = store.resolve_release(lifecycle_release)["candidate"]
        excluded = {retired, future, expired, predecessor}
        _assert_revision_projection(
            payload, current_candidate,
            {edited: edited_text, successor: candidate["items"][successor]["revision"]["text"]},
            store, cutoff, excluded)
        require(old_edited_address not in payload["source_index"]
                and old_edited_address not in payload["payload"]["knowledge"],
                "old_revision_leak", "The lifecycle release retained the old edited revision address.")
        projected_texts = [*payload["payload"]["knowledge"].values(), *payload["source_index"].values()]
        active_texts = [item["revision"]["text"] for item_id, item in current_candidate["items"].items()
                        if store.eligible(current_candidate, item_id, cutoff)]
        for item_id in excluded:
            old_text = candidate["items"][item_id]["revision"]["text"]
            if old_text.strip() and not any(old_text in text for text in active_texts):
                require(all(old_text not in text for text in projected_texts), "inactive_leak",
                        "Unambiguous inactive source text leaked into the provider projection.")
        require(all(document.raw.decode("utf-8") not in text for text in projected_texts),
                "historical_reappend", "The full historical source was re-appended.")
        require(build().encoded == baseline.encoded, "old_pin_changed",
                "New lifecycle releases changed the old pinned context.")
        packet = lifecycle.to_dict()
        for address, text in baseline.to_dict()["payload"]["knowledge"].items():
            if any(address.startswith(f"knowledge:{item_id}@") for item_id in excluded):
                packet["payload"]["knowledge"][address] = text
                packet["source_index"][address] = text
        report["diagnostics"].append({"case": "inactive_reinsert", "error_code": _reject(
            lambda: validate(_rehashed(packet), knowledge_version=lifecycle_release), "context_contract")})
        report["lifecycle"] = {"edited_release": edited_release, "release": lifecycle_release,
                               "old_edited_address": old_edited_address,
                               "baseline_target_items": identifiers[:6],
                               "required_present_items": [edited, successor],
                               "edited_item": edited, "excluded_items": sorted(excluded),
                               "successor": successor,
                               "selected_addresses": sorted(payload["payload"]["knowledge"])}
        _write(output, "lifecycle-context.json", lifecycle.encoded)
        report["goals"]["lifecycle"] = "pass"
    except Exception as error:
        report["failure"] = {"stage": stage, **(
            error.diagnostic() if isinstance(error, KnowledgeError) else
            {"error_class": type(error).__name__, "message": str(error)})}
    finally:
        try:
            report["final_input_sha256"] = _hashes(paths)
            report["final_code_sha256"] = _hashes(code_paths())
            require(report["final_input_sha256"] == plan["input_sha256"]
                    and report["final_code_sha256"] == plan["code_sha256"],
                    "freeze_changed", "Source or executable bytes changed during the run.")
            report["goals"]["freeze_unchanged"] = "pass"
        except Exception as error:
            report["goals"]["freeze_unchanged"] = "failed"
            report["freeze_failure"] = str(error)
        report["status"] = ("pass" if all(value == "pass" for value in report["goals"].values())
                            and "failure" not in report else "failed")
        report["started_at"] = started.isoformat()
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        _write(output, "report.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assessment-time", required=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--freeze", type=Path, help="Reviewed plan.json from a separate plan-only run.")
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        require(output.is_relative_to(RESULTS.resolve()) and output != RESULTS.resolve(),
                "output_path", "Output must be a new child of eval/results/knowledge.")
        plan = make_plan(SOURCE_PATHS, args.assessment_time, {"all": 21, "development": 13, "test": 8})
        if args.plan_only:
            output.mkdir(parents=True, exist_ok=False)
            _write(output, "plan.json", plan)
            print('{"status":"planned","execution":"not_run"}')
            return 0
        require(args.freeze is not None, "freeze_required",
                "Execution requires a reviewed --freeze plan.json; create it with --plan-only first.")
        require(strict_json(args.freeze.read_bytes()) == plan, "freeze_mismatch",
                "Frozen plan differs from current code, sources or settings.")
        report = run_package(output, SOURCE_PATHS, plan)
        print(canonical_bytes({"status": report["status"],
                               "report": str(output / "report.json")}).decode())
        return 0 if report["status"] == "pass" else 1
    except (KnowledgeError, OSError, ValueError) as error:
        diagnostic = (error.diagnostic() if isinstance(error, KnowledgeError) else
                      {"status": "failed", "error_class": type(error).__name__, "message": str(error)})
        print(canonical_bytes(diagnostic).decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
