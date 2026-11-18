from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import AsyncContextManager, Callable, Protocol, runtime_checkable

from llm_inference import InferenceError, InferenceProvider, InferenceResponse
from llm_inference.contracts import canonical, strict_json

from .assessment import (
    NATIVE_ASSESSMENT_CONTRACT, project_native_assessment, request_for, validate_assessment,
    validate_same_day_attention,
)
from .contracts import TriageError, digest, nonblank, require, score, timestamp
from .inputs import ContextExport, ExportedContext, Inputs, validate_context, validate_rows
from .policy import (
    CONTROL_ALIGNMENT_ACTIVITY, FAILED_TEST_RETEST_ACTIVITY, IMPAIRMENT_RECORD_ACTIVITY,
    POLICY_VERSION, RESTORATION_CLOSURE_ACTIVITY, SAME_DAY_ATTENTION_ACTIVITY,
    derive_policy, gap_verification_activity,
)
from .planning import compose_plan, validate_plan
from .projection import PROJECTION_VERSION, project_related_context, project_ticket_text
from .prompt import assessment_prompt, prompt_from_identity
from .source_context import IsolatedKnowledgeReleaseContext, IsolatedProbeContext, NativeContext

RECOVERABLE = {
    "malformed_json", "schema_violation", "assessment_schema", "assessment_identity",
    "assessment_evidence", "assessment_contradiction", "fact_contract", "policy_verification",
    "plan_contract",
}

ACTION_MAX_CHARS = 300
ACTION_TARGET_CHARS = 280
ACTION_SAFETY_CHARS = ACTION_MAX_CHARS - ACTION_TARGET_CHARS


class AccountedProvider(InferenceProvider, Protocol):
    def configuration(self) -> dict: ...


@runtime_checkable
class CatalogProvider(AccountedProvider, Protocol):
    def models(self) -> list[dict]: ...


@dataclass(frozen=True)
class RunConfig:
    model: str
    knowledge_version: str
    assessment_time: str
    phase_attempt_budget: int
    attempt_ledger: str
    max_context_bytes: int = 64_000
    timeout_seconds: float = 90
    reasoning_effort: str | None = "low"
    execution_mode: str = "strict"
    minimum_request_interval_seconds: float = 0
    azure_max_completion_tokens: int = 4096
    azure_api: str = "chat_completions"

    def validate(self) -> None:
        require(nonblank(self.model) and nonblank(self.knowledge_version),
                "configuration", "Explicit model and knowledge version required")
        timestamp(self.assessment_time)
        require(type(self.phase_attempt_budget) is int and self.phase_attempt_budget > 0,
                "configuration", "Positive phase attempt budget required")
        require(nonblank(self.attempt_ledger), "configuration", "Persistent phase ledger required")
        require(self.execution_mode in {"strict", "copilot_experiment", "copilot_delivery"},
                "configuration", "Unknown inference execution mode")
        if self.execution_mode in {"copilot_experiment", "copilot_delivery"}:
            require(Path(self.attempt_ledger).name.lower().endswith(".experimental-ledger.json"),
                    "configuration", "Copilot runs require a separate .experimental-ledger.json")
        require(type(self.max_context_bytes) is int and self.max_context_bytes > 0,
                "configuration", "Positive context byte limit required")
        require(type(self.timeout_seconds) in {int, float}
                and math.isfinite(self.timeout_seconds) and 0 < self.timeout_seconds <= 300,
                "configuration", "Timeout must be finite in (0, 300]")
        require(type(self.minimum_request_interval_seconds) in {int, float}
                and math.isfinite(self.minimum_request_interval_seconds)
                and 0 <= self.minimum_request_interval_seconds <= 300,
                "configuration", "Minimum request interval must be finite in [0, 300]")
        require(type(self.azure_max_completion_tokens) is int
                and 0 < self.azure_max_completion_tokens <= 32768,
                "configuration", "Azure completion-token cap must be an integer in [1, 32768]")
        require(isinstance(self.azure_api, str) and self.azure_api in {"chat_completions", "responses"},
                "configuration", "Azure API must be chat_completions or responses")


def _distinct_actions(activities: list[str]) -> list[str]:
    return list(dict.fromkeys(activities))


def compose_action(core: str, activities: list[str],
                   fixed_activities: list[str] | None = None) -> dict:
    required = _distinct_actions(activities)
    fixed_required = _distinct_actions(fixed_activities or [])
    model_core = core
    for activity in fixed_required:
        if activity == FAILED_TEST_RETEST_ACTIVITY:
            model_core = model_core.replace(activity, "")
    model_core = " ".join(model_core.split())
    require(nonblank(model_core), "policy_verification",
            "Action core cannot consist only of code-owned activities")
    appended = [activity for activity in required if activity not in model_core]
    fixed = set(fixed_required)
    appended_fixed = [activity for activity in appended if activity in fixed]
    appended_model = [activity for activity in appended if activity not in fixed]
    parts = [model_core, *appended]
    return {"model_core": model_core, "required_activities": required,
            "fixed_required_activities": fixed_required,
            "appended_activities": appended,
            "fixed_appended_activities": appended_fixed,
            "model_appended_activities": appended_model,
            "composed": " ".join(parts)}


def require_fixed_actions_fit(fixed_activities: list[str]) -> None:
    fixed = _distinct_actions(fixed_activities)
    fixed_chars = sum(len(activity) + 1 for activity in fixed)
    require(fixed_chars + 1 <= ACTION_TARGET_CHARS, "policy_verification_impossible",
            f"Fixed verification activities consume {fixed_chars} characters including separators; "
            f"no nonempty action core can fit the {ACTION_TARGET_CHARS}-character safety target "
            f"({ACTION_SAFETY_CHARS} characters below the {ACTION_MAX_CHARS} hard limit).")


def action_retry_budget(composition: dict) -> dict:
    fixed = composition.get("fixed_required_activities",
                            composition["fixed_appended_activities"])
    model = composition["model_appended_activities"]
    require_fixed_actions_fit(fixed)
    fixed_chars = sum(len(activity) + 1 for activity in fixed)
    text_budget = ACTION_TARGET_CHARS - fixed_chars - len(model)
    require(text_budget >= len(model) + 1, "policy_verification_impossible",
            "Fixed activities and required separators leave no nonempty retry fields.")
    if model:
        current_text = len(composition["model_core"]) + sum(map(len, model))
        require(current_text > 0, "policy_verification_impossible",
                "Current action has no text to allocate proportionally.")
        core_cap = max(1, text_budget * len(composition["model_core"]) // current_text)
        core_cap = min(core_cap, text_budget - len(model))
        model_cap, remainder = divmod(text_budget - core_cap, len(model))
        core_cap += remainder
    else:
        core_cap, model_cap = text_budget, 0
    return {
        "hard_limit_chars": ACTION_MAX_CHARS,
        "safety_target_chars": ACTION_TARGET_CHARS,
        "safety_margin_chars": ACTION_SAFETY_CHARS,
        "fixed_appended_chars_with_separators": fixed_chars,
        "model_check_count": len(model),
        "model_separator_chars": len(model),
        "current_core_chars": len(composition["model_core"]),
        "current_model_check_chars": sum(map(len, model)),
        "core_max_chars": core_cap,
        "model_check_max_chars": model_cap,
    }


def action_overflow_message(composition: dict) -> tuple[str, dict]:
    budget = action_retry_budget(composition)
    model = composition["model_appended_activities"]
    return (
        f"Composed action {len(composition['composed'])}/{ACTION_MAX_CHARS}. "
        f"Retry target <= {ACTION_TARGET_CHARS}, leaving {ACTION_SAFETY_CHARS} safety characters. "
        f"Proportional core cap {budget['core_max_chars']}; uniform model-check cap "
        f"{budget['model_check_max_chars']} for {len(model)} editable checks. "
        "Fixed appended checks are code-owned and must remain exact. "
        "Shorten each model check without dropping its object or purpose; preserve every activity. "
        "Do not copy appended checks into the core."
    ), budget


def validate_output(payload: dict, findings: dict) -> None:
    require(isinstance(payload, dict) and set(payload) ==
            {"generated_at", "tickets_generated", "tickets"}, "output_schema", "Invalid wrapper")
    timestamp(payload["generated_at"])
    tickets = payload["tickets"]
    require(isinstance(tickets, list) and type(payload["tickets_generated"]) is int
            and len(tickets) == payload["tickets_generated"] == len(findings),
            "output_coverage", "Ticket count differs from selected input")
    seen_findings, seen_tickets = set(), set()
    names = {
        "ticket_id", "finding_id", "equipment_id", "summary", "recommended_action",
        "likelihood_of_failure", "impact_of_failure", "urgency", "review_required", "review_reason",
    }
    for ticket in tickets:
        require(isinstance(ticket, dict) and set(ticket) == names,
                "output_schema", "Invalid ticket fields")
        identifier = ticket["finding_id"]
        require(isinstance(identifier, str) and identifier in findings and identifier not in seen_findings,
                "output_coverage", "Unknown or duplicate finding")
        require(ticket["equipment_id"] == findings[identifier]["equipment_id"],
                "output_mapping", "Output equipment differs")
        expected_id = "TKT-" + identifier[2:]
        require(ticket["ticket_id"] == expected_id and expected_id not in seen_tickets,
                "output_identity", "Invalid or duplicate ticket ID")
        seen_findings.add(identifier)
        seen_tickets.add(expected_id)
        for field in ("summary", "recommended_action"):
            require(nonblank(ticket[field]) and len(ticket[field]) <= 300,
                    "output_text", "Ticket text must be nonempty and <=300 characters")
        for field in ("likelihood_of_failure", "impact_of_failure", "urgency"):
            item = ticket[field]
            require(isinstance(item, dict) and set(item) == {"score", "rationale"}
                    and nonblank(item["rationale"]), "output_score", "Invalid score object")
            score(item["score"])
        require(type(ticket["review_required"]) is bool
                and (ticket["review_reason"] is None or isinstance(ticket["review_reason"], str))
                and (not ticket["review_required"] or nonblank(ticket["review_reason"])),
                "output_review", "Invalid review disposition")
    require(seen_findings == set(findings), "output_coverage", "Incomplete selected coverage")


def save_json(path: Path, value: dict) -> None:
    encoded = (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    with path.open("wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def save_json_atomic(path: Path, value: dict) -> None:
    encoded = (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.stem}-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def checked_receipt(receipt: dict) -> None:
    require(isinstance(receipt, dict)
            and type(receipt.get("http_dispatches_observed")) is int
            and receipt["http_dispatches_observed"] == 1
            and type(receipt.get("sdk_retries")) is int and receipt["sdk_retries"] == 0
            and type(receipt.get("http_transport_retries")) is int
            and receipt["http_transport_retries"] == 0,
            "unverified_attempts", "Cannot establish one retry-free provider dispatch")


def checked_azure_receipt(receipt: dict, config: RunConfig, system: str, user: str) -> None:
    require(receipt.get("api") == "azure-openai-v1-" + config.azure_api.replace("_", "-")
            and receipt.get("max_completion_tokens") == config.azure_max_completion_tokens
            and receipt.get("requested_model") == config.model
            and receipt.get("wire_message_hashes_match") is True
            and receipt.get("system_sha256") == digest(system.encode())
            and receipt.get("user_sha256") == digest(user.encode()),
            "unverified_provider_call", "Azure API, cap, model or actual message hashes differ from configuration")


def copilot_preflight(provider: AccountedProvider, config: RunConfig) -> dict:
    configuration = provider.configuration()
    capabilities = configuration.get("capabilities") if isinstance(configuration, dict) else None
    require(isinstance(capabilities, dict) and configuration.get("provider") == "github-copilot"
            and capabilities.get("tools") is False
            and type(capabilities.get("adapter_retries")) is int
            and capabilities["adapter_retries"] == 0
            and capabilities.get("internal_http_retries") == "unknown",
            "provider_capabilities", "Copilot experiment requires explicit restricted capabilities")
    require(isinstance(provider, CatalogProvider),
            "provider_capabilities", "Copilot model catalog is required")
    models = provider.models()
    require(isinstance(models, list), "provider_capabilities", "Invalid model catalog")
    matches = [item for item in models if isinstance(item, dict) and item.get("id") == config.model]
    require(len(matches) == 1, "model_unavailable", "Selected Copilot model is not in catalog")
    model = matches[0]
    require(isinstance(model.get("provider"), dict) and model["provider"].get("kind") == "copilot"
            and isinstance(model.get("policy", {}), dict)
            and model.get("policy", {}).get("state") != "disabled",
            "model_unavailable", "Selected model is not an enabled Copilot model")
    require(config.reasoning_effort is None
            or config.reasoning_effort in (model.get("supportedReasoningEfforts") or []),
            "unsupported_control", "Selected model does not advertise requested reasoning effort")
    return model


def checked_copilot_receipt(receipt: dict, model: str, system: str, user: str) -> None:
    require(isinstance(receipt, dict)
            and receipt.get("provider") == "github-copilot"
            and type(receipt.get("adapter_attempts")) is int and receipt["adapter_attempts"] == 1
            and type(receipt.get("inference_calls_observed")) is int
            and receipt["inference_calls_observed"] == 1
            and receipt.get("dispatched") is True
            and receipt.get("session_deleted") is True
            and receipt.get("observed_model") == receipt.get("requested_model") == model
            and "boundary_violation" in receipt and receipt["boundary_violation"] is None
            and receipt.get("http_attempts", "missing") is None
            and not receipt.get("cleanup_errors") and not receipt.get("runtime_shutdown_error")
            and not receipt.get("primary_error_class"),
            "unverified_copilot_call", "Copilot call/session accounting or model boundary is unverified")
    audit = receipt.get("message_audit")
    require(isinstance(audit, list) and len(audit) == 2
            and all(isinstance(item, dict) and item.get("matches_sdk_input") is True for item in audit)
            and {item.get("kind") for item in audit} == {"system.message", "user.message"},
            "unverified_copilot_call", "Both actual Copilot system/user message audits are required")
    expected = {"system.message": digest(system.encode()), "user.message": digest(user.encode())}
    require(all(item.get("content_sha256") == expected[item["kind"]] for item in audit),
            "unverified_copilot_call", "Copilot message hashes differ from prepared workflow request")
    tools = receipt.get("tool_counts_observed")
    require(isinstance(tools, list) and tools
            and all(type(count) is int and count == 0 for count in tools),
            "unverified_copilot_call", "Zero observed model-facing tools must be established")


def reserve_attempt(path: Path, budget: int, token: str, execution_mode: str = "strict") -> None:
    initial = {"budget": budget, "reservations": []}
    if execution_mode in {"copilot_experiment", "copilot_delivery"}:
        initial["execution_mode"] = execution_mode
    ledger = strict_json(path.read_text(encoding="utf-8")) if path.exists() else initial
    require(isinstance(ledger, dict) and set(ledger) == set(initial)
            and ledger.get("execution_mode", "strict") == execution_mode
            and type(ledger["budget"]) is int and ledger["budget"] == budget
            and isinstance(ledger["reservations"], list)
            and all(nonblank(x) for x in ledger["reservations"])
            and len(set(ledger["reservations"])) == len(ledger["reservations"]),
            "attempt_ledger", "Corrupt or differently budgeted phase ledger")
    require(len(ledger["reservations"]) < budget and token not in ledger["reservations"],
            "attempt_budget", "Persistent phase attempt budget exhausted")
    ledger["reservations"].append(token)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".triage-ledger-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(ledger, indent=2) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


async def run_workflow(
    inputs: Inputs, context_source: ContextExport | NativeContext,
    provider_factory: Callable[[], AsyncContextManager[AccountedProvider]],
    config: RunConfig, output: Path, evidence: Path,
    *, purpose: str = "normal", overlay_ref: dict | None = None,
    selected_finding_ids: list[str] | None = None,
) -> dict:
    output, evidence = output.resolve(), evidence.resolve()
    copilot = config.execution_mode in {"copilot_experiment", "copilot_delivery"}
    experimental = config.execution_mode == "copilot_experiment"
    entries_key = "application_sends" if copilot else "attempts"
    report = {
        "run_status": "running", "published_output": False, "policy_version": POLICY_VERSION,
        "started_at": datetime.now(timezone.utc).isoformat(), "config": asdict(config),
        "input_sha256": {"findings": inputs.findings_hash, "registry": inputs.registry_hash},
        entries_key: [], "decisions": [], "execution_mode": config.execution_mode,
        "cache_mode": "no_application_result_cache",
        "semantic_status": "not_reviewed", "human_approval": "required_outside_generation",
        "output_path": str(output),
    }
    if copilot:
        report.update(acceptance_eligible=False, strict_attempt_contract="not_established",
                      http_attempts=None, usd_cost=None, output_token_cap=None,
                      knowledge_review="ai_assisted_not_human_or_expert_approval",
                      attempt_accounting_unit="application_sends_http_attempts_unknown")
        if not experimental:
            report["delivery_route_declared"] = True
    active, attempts = None, 0
    owned_evidence = False
    temporary: Path | None = None
    publication_succeeded = False
    previous_output_existed = False
    previous_output_bytes: bytes | None = None
    started = time.monotonic()
    try:
        config.validate()
        require(not experimental or output.name.lower().endswith(".experimental.json"),
                "configuration", "Copilot output must end with .experimental.json, never final tickets.json")
        require(output != evidence and not output.is_relative_to(evidence),
                "configuration", "Output must be outside the evidence directory")
        ledger = Path(config.attempt_ledger).resolve()
        require(ledger != output and not ledger.is_relative_to(evidence),
                "configuration", "Phase ledger must be outside output/evidence")
        require(not evidence.exists(), "evidence_exists", "Evidence directory already exists")
        require(not output.exists() or output.is_file(), "configuration", "Output is not a file")
        evidence.mkdir(parents=True)
        owned_evidence = True
        previous_output_existed = output.exists()
        previous_output_bytes = output.read_bytes() if previous_output_existed else None
        report["previous_output_sha256"] = (
            digest(previous_output_bytes) if previous_output_bytes is not None else None
        )
        data = inputs.data
        validate_rows(data["findings"], data["registry"])
        selected_ids = (
            sorted(data["findings"]) if selected_finding_ids is None
            else sorted(dict.fromkeys(selected_finding_ids))
        )
        require(bool(selected_ids)
                and all(identifier in data["findings"] for identifier in selected_ids),
                "configuration", "Selected findings must be nonempty known finding IDs")
        selected_findings = {
            identifier: data["findings"][identifier] for identifier in selected_ids
        }
        report["selected_finding_ids"] = selected_ids
        native = isinstance(context_source, NativeContext)
        if native:
            if isinstance(context_source, (IsolatedProbeContext, IsolatedKnowledgeReleaseContext)):
                require(purpose == "isolated_probe" and overlay_ref is None
                        and output.name.lower().endswith(".experimental.json"),
                        "context_overlay", "Isolated native probes require explicit purpose and experimental output")
            else:
                require(purpose == "normal" and overlay_ref is None,
                        "context_overlay", "Normal native context cannot accept evaluation overlays")
            bundle, context_text, snapshot = context_source.prepare(
                inputs, config.knowledge_version, config.assessment_time, config.max_context_bytes)
            context_gaps = snapshot["gaps"]
            report["knowledge_handoff"] = snapshot
        else:
            bundle, context_text, snapshot = validate_context(
                context_source, inputs, config.knowledge_version, config.assessment_time,
                config.max_context_bytes, purpose=purpose, overlay_ref=overlay_ref,
            )
            context_gaps = bundle["gaps"]
        report["context_hash"] = bundle["context_hash"]
        report["context"] = bundle
        report["knowledge_content_hash"] = snapshot["content_hash"]
        report["config_sha256"] = digest(canonical(asdict(config)).encode())
        selected_prompt = (
            prompt_from_identity(snapshot["activation"]["assessment_prompt"])
            if native else assessment_prompt()
        )
        report["implementation_sha256"] = {
            path.name: digest(path.read_bytes()) for path in sorted(Path(__file__).parent.glob("*.py"))
        }
        report["assessment_prompt"] = selected_prompt.identity()
        report["ticket_projection"] = PROJECTION_VERSION
        report["context_provenance"] = (
            "native_source_first_bundle_3" if native else "unauthenticated_provisional_export")
        report["knowledge_approval"] = (
            "local_release_and_activation_declarations_not_authenticated_or_domain_certification"
            if native else "producer_claim_not_independently_verified")
        report["context_gaps"] = context_gaps
        if native:
            report["knowledge_implementation_sha256"] = {
                path.name: digest(path.read_bytes())
                for path in sorted(Path(__file__).parents[1].joinpath("triage_knowledge").glob("*.py"))
            }
        report["context_export_sha256"] = (
            context_source.raw_sha256 if isinstance(context_source, ExportedContext) else None
        )
        for finding_id in selected_ids:
            require_fixed_actions_fit([
                gap_verification_activity(gap)
                for gap in context_gaps if finding_id in gap["finding_ids"]
            ])
        save_json(evidence / "run.json", report)
        tickets = []
        async with provider_factory() as provider:
            configuration = provider.configuration()
            if copilot:
                report["catalog_model"] = copilot_preflight(provider, config)
            else:
                require(isinstance(configuration, dict)
                    and type(configuration.get("sdk_retries")) is int
                    and configuration["sdk_retries"] == 0
                    and type(configuration.get("http_transport_retries")) is int
                    and configuration["http_transport_retries"] == 0
                    and configuration.get("tools") is False
                    and configuration.get("follow_redirects") is False,
                    "provider_capabilities", "Retry-free, tool-free direct provider required")
                if configuration.get("provider") == "azure-openai":
                    require(configuration.get("api") ==
                            "azure-openai-v1-" + config.azure_api.replace("_", "-")
                            and configuration.get("max_completion_tokens") == config.azure_max_completion_tokens,
                            "provider_capabilities", "Azure provider API/token cap differs from configuration")
            report["provider"] = configuration
            last_dispatch = None
            for active in selected_ids:
                finding = data["findings"][active]
                gaps = [g for g in context_gaps if active in g["finding_ids"]]
                attempts, feedback = 0, None
                feedback_detail, previous_draft = None, None
                retry_fixed_activities: list[str] = []
                retry_model_activities: list[str] = []
                retry_action_budget: dict | None = None
                while attempts < 2:
                    require(len(report[entries_key]) < config.phase_attempt_budget,
                            "attempt_budget", "Phase attempt budget exhausted")
                    request = request_for(config.model, context_text, active, finding["equipment_id"],
                                          config.timeout_seconds, config.reasoning_effort, feedback,
                                          [gap_verification_activity(gap) for gap in gaps],
                                          system_prompt=selected_prompt.text,
                                          possible_policy_activities=[
                                              SAME_DAY_ATTENTION_ACTIVITY,
                                              CONTROL_ALIGNMENT_ACTIVITY,
                                              IMPAIRMENT_RECORD_ACTIVITY,
                                              RESTORATION_CLOSURE_ACTIVITY,
                                          ],
                                          feedback_detail=feedback_detail, previous_draft=previous_draft,
                                          fixed_appended_activities=retry_fixed_activities,
                                          model_appended_activities=retry_model_activities,
                                          retry_action_budget=retry_action_budget,
                                          assessment_contract=selected_prompt.assessment_contract)
                    system, user, _ = request.prepared()
                    if last_dispatch is not None and config.minimum_request_interval_seconds > 0:
                        await asyncio.sleep(max(0, config.minimum_request_interval_seconds
                                                - (time.monotonic() - last_dispatch)))
                    reserve_attempt(ledger, config.phase_attempt_budget,
                                    f"{evidence}:{active}:{attempts + 1}", config.execution_mode)
                    attempts += 1
                    entry = {"finding_id": active, "attempt": attempts,
                             "status": "reserved", "provider_input": {"system": system, "user": user},
                             "provider_input_sha256": {
                                 "system": digest(system.encode()), "user": digest(user.encode()),
                             }}
                    report[entries_key].append(entry)
                    save_json(evidence / "run.json", report)
                    try:
                        last_dispatch = time.monotonic()
                        async with asyncio.timeout(config.timeout_seconds + (20 if copilot else 0)):
                            response = await provider.generate(request)
                        require(isinstance(response, InferenceResponse),
                                "provider_contract", "Provider returned an invalid response object")
                        entry["receipt"] = response.receipt
                        entry["response"] = response.text
                        if copilot:
                            checked_copilot_receipt(response.receipt, config.model, system, user)
                        else:
                            checked_receipt(response.receipt)
                            if configuration.get("provider") == "azure-openai":
                                checked_azure_receipt(response.receipt, config, system, user)
                        assessment_text = response.text
                        attention = []
                        if bundle.get("contract_version") == 3:
                            assessment_text, attention = project_native_assessment(
                                response.text, bundle["source_index"])
                            entry["assessment_projection_contract"] = selected_prompt.assessment_contract
                            entry["citation_catalog_sha256"] = strict_json(request.user)["citation_catalog_sha256"]
                            entry["projected_assessment"] = strict_json(assessment_text)
                            entry["same_day_attention"] = attention
                        assessment = validate_assessment(
                            assessment_text, finding, bundle["source_index"],
                            selected_prompt.assessment_contract,
                        )
                        attention = validate_same_day_attention(attention, finding, bundle["source_index"])
                        decision = derive_policy(
                            assessment["likelihood_of_failure"]["score"],
                            assessment["impact_of_failure"]["score"],
                            assessment["facts"], assessment["uncertainties"],
                            sce=data["registry"][finding["equipment_id"]]["safety_critical_element"] == "Yes",
                            gaps=gaps, same_day_attention=attention,
                        )
                        if feedback == "policy_verification" and retry_action_budget is not None:
                            dropped_fixed = [
                                activity for activity in retry_fixed_activities
                                if activity not in decision["fixed_verification_activities"]
                            ]
                            require(not dropped_fixed, "policy_verification",
                                    "Overflow repair changed facts and dropped code-owned activities: "
                                    + "; ".join(dropped_fixed))
                        if selected_prompt.assessment_contract == NATIVE_ASSESSMENT_CONTRACT:
                            composition = compose_action(
                                assessment["recommended_action"],
                                decision["verification_activities"],
                                decision["fixed_verification_activities"],
                            )
                        else:
                            validate_plan(
                                assessment["plan"], decision, assessment["facts"],
                                assessment["uncertainties"],
                            )
                            composition = compose_plan(assessment["plan"], decision)
                        entry["action_composition"] = composition
                        action = composition["composed"]
                        if len(action) > ACTION_MAX_CHARS and selected_prompt.assessment_contract == NATIVE_ASSESSMENT_CONTRACT:
                            feedback_message, retry_action_budget = action_overflow_message(composition)
                            retry_fixed_activities = decision["fixed_verification_activities"]
                            retry_model_activities = composition["model_appended_activities"]
                            raise TriageError("policy_verification", feedback_message)
                        if len(action) > ACTION_MAX_CHARS:
                            raise TriageError(
                                "plan_contract",
                                f"Composed plan is {len(action)}/{ACTION_MAX_CHARS} characters; "
                                "shorten plan fields without dropping required phases.",
                            )
                        if feedback == "policy_verification" and retry_action_budget is not None:
                            require(len(action) <= ACTION_MAX_CHARS, "policy_verification",
                                    f"Repaired action is {len(action)}/{ACTION_MAX_CHARS} characters; "
                                    "no truncation or required-activity dropping is permitted.")
                        missing = [] if selected_prompt.assessment_contract != NATIVE_ASSESSMENT_CONTRACT else [
                            activity for activity in decision["verification_activities"]
                            if activity != RESTORATION_CLOSURE_ACTIVITY and activity not in action
                        ]
                        require(not missing, "policy_verification",
                                "Required verification activity missing from action: " + "; ".join(missing))
                        projection = project_ticket_text(
                            decision,
                            assessment["likelihood_of_failure"]["score"],
                            assessment["impact_of_failure"]["score"],
                        )
                        ticket = {
                            "ticket_id": "TKT-" + active[2:], "finding_id": active,
                            "equipment_id": finding["equipment_id"],
                            "summary": assessment["summary"],
                            "recommended_action": action,
                            "likelihood_of_failure": {
                                "score": assessment["likelihood_of_failure"]["score"],
                                "rationale": (
                                    assessment["likelihood_of_failure"]["rationale"]
                                    + project_related_context(assessment["facts"], active)
                                ),
                            },
                            "impact_of_failure": {
                                name: assessment["impact_of_failure"][name]
                                for name in ("score", "rationale")
                            },
                            "urgency": {
                                "score": decision["final"],
                                "rationale": projection["urgency_rationale"],
                            },
                            "review_required": decision["review_required"],
                            "review_reason": projection["review_reason"],
                        }
                        entry.update(status="validated", assessment=assessment)
                        entry.pop("projected_assessment", None)
                        report["decisions"].append({
                            "finding_id": active, **decision, "ticket_projection": projection,
                        })
                        tickets.append(ticket)
                        save_json(evidence / "run.json", report)
                        break
                    except (InferenceError, TriageError) as error:
                        code = error.code
                        entry.update(status="failed", error_class=code, validation_message=str(error)[:500])
                        if isinstance(error, InferenceError):
                            entry["receipt"] = error.receipt
                            if code in RECOVERABLE:
                                if copilot:
                                    checked_copilot_receipt(error.receipt, config.model, system, user)
                                else:
                                    checked_receipt(error.receipt)
                                    if configuration.get("provider") == "azure-openai":
                                        checked_azure_receipt(error.receipt, config, system, user)
                                if error.response_text is not None:
                                    entry["response"] = error.response_text
                        save_json(evidence / "run.json", report)
                        if code not in RECOVERABLE or attempts == 2:
                            raise TriageError(code, "Finding assessment failed") from error
                        feedback = code
                        feedback_detail = str(error)[:500]
                        previous_draft = entry.get("response")
                    except TimeoutError as error:
                        entry.update(status="failed", error_class="timeout", dispatch_outcome="unknown")
                        save_json(evidence / "run.json", report)
                        raise TriageError("timeout", "Inference deadline exceeded; dispatch outcome unknown") from error
            active, attempts = None, 0
        active = None
        payload = {"generated_at": datetime.now(timezone.utc).isoformat(),
                   "tickets_generated": len(tickets), "tickets": tickets}
        validate_output(payload, selected_findings)
        encoded = (json.dumps(payload, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()
        report.update(run_status="ready_to_publish", intended_output_sha256=digest(encoded),
                      elapsed_seconds=time.monotonic() - started)
        save_json(evidence / "run.json", report)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".triage-", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
        temporary = None
        publication_succeeded = True
        observed_output = output.read_bytes()
        observed_hash = digest(observed_output)
        require(observed_output == encoded and observed_hash == report["intended_output_sha256"],
                "publication_verification",
                "Published output bytes differ from the validated publication candidate")
        published_at = datetime.now(timezone.utc).isoformat()
        publication_receipt = {
            "contract": "triage-publication-receipt-v1",
            "published_at": published_at,
            "publication_method": "same-directory-temporary-file_then_os_replace",
            "output_path": str(output),
            "output_sha256": observed_hash,
            "output_bytes": len(observed_output),
            "tickets_generated": len(tickets),
            "previous_output_sha256": report["previous_output_sha256"],
            "run_config_sha256": report["config_sha256"],
            "context_hash": report["context_hash"],
            "assessment_prompt": report["assessment_prompt"],
            "policy_version": POLICY_VERSION,
            "verified_after_replace": True,
        }
        save_json_atomic(evidence / "publication.json", publication_receipt)
        publication_receipt_sha256 = digest((evidence / "publication.json").read_bytes())
        report.update(
            run_status="published",
            published_output=True,
            published_at=published_at,
            output_sha256=observed_hash,
            publication_receipt="publication.json",
            publication_receipt_sha256=publication_receipt_sha256,
            elapsed_seconds=time.monotonic() - started,
        )
        save_json(evidence / "run.json", report)
        result = {"run_status": "draft_generated", "published_output": True,
                "output": str(output), "output_sha256": observed_hash,
                "publication_receipt": str(evidence / "publication.json"),
                "publication_receipt_sha256": publication_receipt_sha256,
                "tickets_generated": len(tickets), "semantic_status": "not_reviewed"}
        if experimental:
            result.update(run_status="experimental_draft_generated", acceptance_eligible=False,
                          execution_mode=config.execution_mode, http_attempts=None,
                          application_send_count=len(report[entries_key]))
        elif copilot:
            result.update(delivery_eligible=True, acceptance_eligible=False,
                          execution_mode=config.execution_mode, http_attempts=None,
                          application_send_count=len(report[entries_key]))
        return result
    except (TriageError, InferenceError, OSError, ValueError, TypeError, KeyError, AttributeError,
            RecursionError, TimeoutError) as error:
        if isinstance(error, TriageError):
            failure = error
        elif isinstance(error, InferenceError):
            failure = TriageError(error.code, "Provider lifecycle failed")
        else:
            code = "timeout" if isinstance(error, TimeoutError) else (
                "io" if isinstance(error, OSError) else "contract"
            )
            failure = TriageError(code, "Workflow failed before publication")
        failure.finding_id = failure.finding_id or active
        failure.attempts = attempts
        failure.execution_mode = config.execution_mode
        if publication_succeeded:
            rollback_temporary = None
            try:
                if previous_output_existed:
                    with tempfile.NamedTemporaryFile(
                        dir=output.parent, prefix=".triage-rollback-", suffix=".tmp",
                        delete=False,
                    ) as stream:
                        rollback_temporary = Path(stream.name)
                        stream.write(previous_output_bytes or b"")
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(rollback_temporary, output)
                    rollback_temporary = None
                else:
                    output.unlink(missing_ok=True)
                publication_succeeded = False
                report.update(publication_rolled_back=True, published_output=False)
                for key in (
                    "published_at", "output_sha256", "publication_receipt",
                    "publication_receipt_sha256", "post_publication_failure",
                ):
                    report.pop(key, None)
                try:
                    (evidence / "publication.json").unlink(missing_ok=True)
                except OSError as cleanup_error:
                    report["publication_receipt_cleanup_error"] = str(cleanup_error)[:500]
            except OSError as rollback_error:
                report["publication_rollback_error"] = str(rollback_error)[:500]
            finally:
                if rollback_temporary is not None:
                    rollback_temporary.unlink(missing_ok=True)
        failure.published_output = publication_succeeded
        report.update(run_status="failed", diagnostic=failure.diagnostic(),
                      elapsed_seconds=time.monotonic() - started)
        if publication_succeeded:
            report.update(
                published_output=True,
                output_sha256=digest(output.read_bytes()) if output.is_file() else None,
                post_publication_failure=True,
            )
        if owned_evidence:
            try:
                report["output_after_failure_sha256"] = digest(output.read_bytes()) if output.is_file() else None
                save_json(evidence / "run.json", report)
            except OSError:
                failure.args = (str(failure) + "; diagnostic persistence failed",)
        raise failure from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
