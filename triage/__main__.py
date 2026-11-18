from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from llm_inference import AzureOpenAIProvider, CopilotProvider, InferenceError
from llm_inference.contracts import strict_json

from .contracts import TriageError, require
from .inputs import ExportedContext, read_inputs
from .source_context import NativeContext
from .workflow import RunConfig, run_workflow


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise TriageError("configuration", message)


def main(argv: list[str] | None = None) -> int:
    parser = Parser(description="Generate human-approval drafts using pinned source-first knowledge and workflow policy.")
    parser.add_argument("--findings", type=Path, required=True, help="Already selected findings CSV")
    parser.add_argument("--registry", type=Path, required=True)
    context = parser.add_mutually_exclusive_group(required=True)
    context.add_argument("--knowledge-store", type=Path, help="Reviewed source-first schema-3 store")
    context.add_argument("--context-export", type=Path, help="Legacy v0 replay only; requires --legacy-replay")
    parser.add_argument("--activation", type=Path,
                        help="Reviewed triage-activation-v2 pins for knowledge, policies and prompt")
    parser.add_argument("--legacy-replay", action="store_true", help="Explicitly replay the retired v0 interface")
    parser.add_argument("--config", type=Path, required=True, help="Explicit RunConfig JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True, help="New per-run directory")
    parser.add_argument("--finding-id", action="append", dest="finding_ids",
                        help="Process only this finding while retaining the full input context; repeatable")
    parser.add_argument("--provider", choices=("azure", "copilot"), default="azure",
                        help="Copilot requires an explicit copilot execution mode in config")
    parser.add_argument("--allow-inference", action="store_true", help="Explicit opt-in to billable inference")
    try:
        args = parser.parse_args(argv)
        require(args.allow_inference, "inference_not_authorized", "Pass --allow-inference for a budgeted live run")
        native = args.knowledge_store is not None
        require((native and args.activation is not None and not args.legacy_replay)
                or (not native and args.activation is None and args.legacy_replay),
                "configuration", "Use --knowledge-store with --activation, or explicit --legacy-replay")
        sources = {p.resolve() for p in (args.findings, args.registry, args.context_export,
                                         args.config, args.activation) if p is not None}
        if native:
            store = args.knowledge_store.resolve()
            require(not args.output.resolve().is_relative_to(store)
                    and not args.evidence.resolve().is_relative_to(store)
                    and not Path(args.config).resolve().is_relative_to(args.evidence.resolve()),
                    "configuration", "Run outputs/evidence must not modify the knowledge store")
        require(args.output.resolve() not in sources
                and not any(p.is_relative_to(args.evidence.resolve()) for p in sources),
                "configuration", "Output/evidence must not overwrite input artifacts")
        config = RunConfig(**strict_json(args.config.read_text(encoding="utf-8")))
        copilot_mode = config.execution_mode in {"copilot_experiment", "copilot_delivery"}
        require((args.provider == "copilot") == copilot_mode,
                "configuration", "Copilot provider and an explicit Copilot mode must be selected together")
        require(Path(config.attempt_ledger).resolve() not in sources,
                "configuration", "Phase ledger must not overwrite input artifacts")
        require(not native or not Path(config.attempt_ledger).resolve().is_relative_to(store),
                "configuration", "Phase ledger must not modify the knowledge store")
        inputs = read_inputs(args.findings, args.registry)
        context = (NativeContext(store, strict_json(args.activation.read_text(encoding="utf-8")))
                   if native else ExportedContext(args.context_export))
        result = asyncio.run(run_workflow(
            inputs, context,
            (lambda: CopilotProvider()) if args.provider == "copilot" else
            (lambda: AzureOpenAIProvider(native_json_schema=True,
                                         max_completion_tokens=config.azure_max_completion_tokens,
                                         api=config.azure_api)),
            config, args.output, args.evidence,
            selected_finding_ids=args.finding_ids,
        ))
    except (TriageError, InferenceError, OSError, ValueError, TypeError, AttributeError, RecursionError) as error:
        if isinstance(error, TriageError):
            failure = error
        elif isinstance(error, InferenceError):
            failure = TriageError(error.code, "Inference configuration failed")
        else:
            failure = TriageError("configuration", "Could not read validated run inputs")
        print(json.dumps(failure.diagnostic(), ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
