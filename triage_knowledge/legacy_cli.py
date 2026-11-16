from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .context import build_context, serialize_context
from .contracts import KnowledgeError, Review, TableSource, require
from .knowledge import (
    DEFAULT_DOMAIN_LOCATOR, KnowledgeStore, _write, active_guidance, candidate_diff,
    effective_guidance, starter_candidate,
)
from .workflow_export import WorkflowExport

DOMAIN_PATH = DEFAULT_DOMAIN_LOCATOR


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Maintain reviewed triage knowledge and build offline context.")
    result.add_argument("--store", type=Path, default=Path("knowledge"))
    result.add_argument("--domain", type=Path, default=Path(DOMAIN_PATH))
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create an unapproved initial draft; never publishes.")
    for name, help_text in (("check", "Validate the saved draft."),
                            ("diff", "Show the draft diff against its base release.")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--assessment-time", help="Also show time-specific local eligibility audit.")
    upgrade = commands.add_parser("upgrade", help="Explicitly upgrade a saved schema-1 draft to schema 2.")
    upgrade.add_argument("--expected-digest", required=True)
    retire = commands.add_parser("retire", help="Withdraw guidance in the draft; does not publish or change old pins.")
    retire.add_argument("--guidance-id", required=True)
    retire.add_argument("--reason", required=True)
    retire.add_argument("--expected-digest", required=True)
    recovery = commands.add_parser("recover", help="Explicitly archive an invalid draft and reset to unapproved.")
    recovery.add_argument("--expected-raw-sha256", required=True)
    recovery.add_argument("--confirm-archive", action="store_true", required=True)
    fork = commands.add_parser("fork", help="Start a draft based on an exact release.")
    fork.add_argument("--release", required=True)
    fork.add_argument("--expected-digest")
    publish = commands.add_parser("publish", help="Explicitly declare review of the saved candidate.")
    publish.add_argument("--candidate-digest", required=True)
    publish.add_argument("--author", required=True)
    publish.add_argument("--reviewer", required=True)
    publish.add_argument("--reason", required=True)
    context = commands.add_parser("context", help="Build normal context without model calls.")
    context.add_argument("--release", required=True)
    context.add_argument("--findings", type=Path, required=True)
    context.add_argument("--registry", type=Path, required=True)
    context.add_argument("--assessment-time", required=True)
    context.add_argument("--output", type=Path, required=True)
    context.add_argument("--max-context-bytes", type=int, default=262_144)
    context.add_argument("--workflow-v0", action="store_true",
                         help="Write the explicitly provisional triage-export-v0 seam instead.")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = KnowledgeStore(args.store, args.domain)
    try:
        if args.command == "init":
            candidate = starter_candidate(args.domain.read_bytes(), store.domain_locator)
            digest = store.save_draft(candidate, expected_digest=None)
            result = {"status": "draft", "candidate_digest": digest, "approved": False}
        elif args.command == "recover":
            digest = store.recover_draft(
                starter_candidate(args.domain.read_bytes(), store.domain_locator),
                expected_raw_sha256=args.expected_raw_sha256)
            result = {"status": "draft_recovered", "candidate_digest": digest, "approved": False,
                      "archived_raw_sha256": args.expected_raw_sha256}
        elif args.command == "fork":
            result = {"status": "draft", "candidate_digest": store.fork_release(
                args.release, expected_digest=args.expected_digest), "approved": False}
        elif args.command == "upgrade":
            result = {"status": "draft", "candidate_digest": store.upgrade_draft(
                expected_digest=args.expected_digest), "approved": False}
        elif args.command == "retire":
            result = {"status": "draft", "candidate_digest": store.retire_guidance(
                args.guidance_id, args.reason, expected_digest=args.expected_digest), "approved": False}
        elif args.command in {"check", "diff"}:
            candidate, digest = store.load_draft()
            result = {"status": "valid_draft", "candidate_digest": digest, "approved": False,
                      "schema_version": candidate["schema_version"],
                      "eligibility": "structural_only_requires_assessment_time",
                      "structurally_active_ids": active_guidance(candidate),
                      "publish_requires_upgrade": candidate["schema_version"] == 1}
            if args.assessment_time is not None:
                active, excluded = effective_guidance(candidate, args.assessment_time)
                result.update(eligibility="at_explicit_assessment_time", assessment_time=args.assessment_time,
                              effective_guidance_ids=active, excluded_guidance=excluded)
            if args.command == "diff":
                base = candidate["base_release_id"]
                result["diff"] = candidate_diff(
                    store.resolve_knowledge(base).candidate if base is not None else None, candidate)
        elif args.command == "publish":
            now = datetime.now(timezone.utc).isoformat()
            version = store.publish(Review(args.candidate_digest, args.author, args.reviewer,
                                           args.reason, now), published_at=now)
            result = {"status": "published", "knowledge_version": version,
                      "approval": "local_declaration_not_authenticated"}
        else:
            snapshot = store.resolve_knowledge(args.release)
            findings = TableSource.from_bytes(args.findings.read_bytes(), source_id="findings",
                                               kind="finding_input")
            registry = TableSource.from_bytes(args.registry.read_bytes(), source_id="registry",
                                              kind="registry_input")
            bundle = build_context(findings, registry, snapshot, args.assessment_time)
            require(args.max_context_bytes > 0
                    and len(serialize_context(bundle)) <= args.max_context_bytes,
                    "context_limit", "Context exceeds the configured byte limit.")
            output = (WorkflowExport.from_bundle(snapshot, bundle, findings, registry,
                                                  args.assessment_time).encoded
                      if args.workflow_v0 else serialize_context(bundle))
            require(len(output) <= args.max_context_bytes, "context_limit",
                    "Export exceeds the configured byte limit.")
            _write(args.output, output, replace=False)
            result = {"status": "context_created", "output": str(args.output),
                      "knowledge_version": snapshot.knowledge_version,
                      "context_hash": bundle.context_hash, "finding_ids": bundle.finding_ids,
                      "provider_sends": 0}
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except KnowledgeError as error:
        print(json.dumps(error.diagnostic(), ensure_ascii=True), file=sys.stderr)
        return 1
    except OSError:
        print(json.dumps({"status": "failed", "error_class": "io",
                          "message": "Could not read or write the configured artifact."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
