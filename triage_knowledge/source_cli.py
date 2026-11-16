from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

from .contracts import KnowledgeError, strict_json

DEFAULT_DOMAIN = Path(r"docs\candidate-pack\candidate-pack\reference\domain_knowledge.md")
DEFAULT_STORE = Path("knowledge") / "source-first"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Maintain source-first knowledge; no L/I/U inference.")
    result.add_argument("--store", type=Path, default=DEFAULT_STORE)
    commands = result.add_subparsers(dest="command", required=True)
    intake = commands.add_parser("import-source", help="Import exact user-supplied bytes with code extraction.")
    intake.add_argument("--source", type=Path, required=True)
    intake.add_argument("--name", required=True)
    intake.add_argument("--source-id")
    for name in ("check", "strategy"):
        commands.add_parser(name)
    for name in ("review", "edit", "retire", "restore", "reject", "restore-intake"):
        command = commands.add_parser(name)
        command.add_argument("--item", required=True)
        command.add_argument("--expected-digest", required=True)
        command.add_argument("--reason", required=True)
        if name == "review":
            command.add_argument("--reviewer", required=True)
        if name == "edit":
            command.add_argument("--text-file", type=Path, required=True)
        if name in {"retire", "restore"}:
            command.add_argument("--effective-from")
            command.add_argument("--effective-until")
    links = commands.add_parser("set-links")
    links.add_argument("--links", type=Path, required=True)
    links.add_argument("--expected-digest", required=True)
    replacement = commands.add_parser("replace")
    replacement.add_argument("--predecessor", required=True)
    replacement.add_argument("--successor", required=True)
    replacement.add_argument("--effective-from", required=True)
    replacement.add_argument("--reason", required=True)
    replacement.add_argument("--expected-digest", required=True)
    cancel = commands.add_parser("cancel-replacement")
    cancel.add_argument("--predecessor", required=True)
    cancel.add_argument("--reason", required=True)
    cancel.add_argument("--expected-digest", required=True)
    fork = commands.add_parser("fork")
    fork.add_argument("--release", required=True)
    fork.add_argument("--expected-digest", required=True)
    publish = commands.add_parser("publish")
    for name in ("expected-digest", "author", "reviewer", "reason"):
        publish.add_argument("--" + name, required=True)
    publish.add_argument("--reviewed-at")
    query = commands.add_parser("query")
    query.add_argument("--release", required=True)
    query.add_argument("--findings", type=Path, required=True)
    query.add_argument("--registry", type=Path, required=True)
    query.add_argument("--assessment-time", required=True)
    query.add_argument("--expected-strategy", type=Path, required=True)
    query.add_argument("--max-bytes", type=int, default=64_000)
    query.add_argument("--output", type=Path, required=True)
    return result


def write_new_json(path: Path, value: dict) -> None:
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True,
                      allow_nan=False, indent=2) + "\n").encode()
    if path.exists():
        raise FileExistsError("Output already exists; choose a new observation path")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError("Output appeared while preparing publication")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    from .source import SourceDocument, extract_code
    from .source_store import SourceKnowledgeStore
    from .retrieval import binding_from_tables, get_triage_knowledge, strategy_binding
    from .contracts import TableSource

    try:
        store = SourceKnowledgeStore(args.store)
        if args.command == "import-source":
            document = SourceDocument.from_bytes(
                args.source.read_bytes(), name=args.name, source_id=args.source_id)
            extraction = extract_code(document)
            if store.draft_path.exists():
                _, digest = store.load_draft()
                digest = store.add_source(extraction, expected_digest=digest)
            else:
                digest = store.create_draft([extraction])
            result = {"status": "pending_review", "candidate_digest": digest,
                      "source_id": document.source_id, "approved": False}
        elif args.command == "check":
            candidate, digest = store.load_draft()
            result = {"status": "valid_draft", "candidate_digest": digest,
                      "candidate": candidate, "approved": False}
        elif args.command == "strategy":
            result = strategy_binding()
        elif args.command == "publish":
            version = store.publish(
                expected_digest=args.expected_digest, author=args.author,
                reviewer=args.reviewer, reason=args.reason,
                reviewed_at=args.reviewed_at or datetime.now(timezone.utc).isoformat())
            result = {"status": "published", "knowledge_version": version,
                      "approval": "local_declaration_not_authenticated"}
        elif args.command == "query":
            findings = TableSource.from_bytes(args.findings.read_bytes(),
                                              source_id="findings", kind="finding_input")
            registry = TableSource.from_bytes(args.registry.read_bytes(),
                                              source_id="registry", kind="registry_input")
            query = {"findings": {row["finding_id"]: row for row in findings.rows},
                     "registry": {row["equipment_id"]: row for row in registry.rows}}
            binding = binding_from_tables(findings, registry)
            knowledge = get_triage_knowledge(
                store, query, knowledge_version=args.release,
                assessment_time=args.assessment_time,
                expected_strategy=strict_json(args.expected_strategy.read_bytes()),
                allowed_input_binding=binding, max_bytes=args.max_bytes)
            result = knowledge.to_dict()
            if result["status"] != "ok":
                raise KnowledgeError(result["error_code"], "Knowledge retrieval is unavailable")
            write_new_json(args.output, result)
            result = {"status": "knowledge_created", "output": str(args.output),
                      "knowledge_version": args.release, "provider_sends": 0}
        else:
            expected = {"expected_digest": args.expected_digest}
            if args.command == "review":
                digest = store.review_item(args.item, reviewer=args.reviewer,
                                           reason=args.reason, **expected)
            elif args.command == "edit":
                digest = store.edit_item(args.item, args.text_file.read_bytes().decode("utf-8"),
                                         reason=args.reason, **expected)
            elif args.command in {"retire", "restore"}:
                digest = store.set_lifecycle(
                    args.item, status="retired" if args.command == "retire" else "active",
                    effective_from=args.effective_from, effective_until=args.effective_until,
                    reason=args.reason, **expected)
            elif args.command == "reject":
                digest = store.reject_item(args.item, reason=args.reason, **expected)
            elif args.command == "restore-intake":
                digest = store.restore_item(args.item, reason=args.reason, **expected)
            elif args.command == "set-links":
                digest = store.set_context_links(strict_json(args.links.read_bytes()), **expected)
            elif args.command == "cancel-replacement":
                digest = store.cancel_replacement(args.predecessor, reason=args.reason, **expected)
            elif args.command == "fork":
                digest = store.fork_release(args.release, **expected)
            else:
                digest = store.replace_item(
                    args.predecessor, args.successor, effective_from=args.effective_from,
                    reason=args.reason, **expected)
            result = {"status": "pending_review", "candidate_digest": digest, "approved": False}
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except (ValueError, OSError) as error:
        diagnostic = (error.diagnostic() if isinstance(error, KnowledgeError) else
                      {"status": "failed", "error_class": "io" if isinstance(error, OSError)
                       else "invalid_request", "message": str(error)})
        print(json.dumps(diagnostic, ensure_ascii=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
