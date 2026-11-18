from __future__ import annotations

from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile

from llm_inference import InferenceError, InferenceResponse
from llm_inference.contracts import canonical, strict_json
from triage.assessment import FACT_NAMES, NATIVE_ASSESSMENT_CONTRACT
from triage.contracts import digest
from triage.inputs import EQUIPMENT_FIELDS, FINDING_FIELDS, context_body, read_inputs
from triage.workflow import RunConfig

ARTIFACT_ROOT: Path | None = None
CUTOFF = "2026-01-01T00:00:00+00:00"
REFERENCE = "finding:F-8001:finding_description"
QUOTE = "Visible surface mark."


def write_csv(path: Path, fields: tuple, rows: list) -> None:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    path.write_bytes(stream.getvalue().encode("utf-8"))


def source_files(root: Path, *, count: int = 1, sce: bool = False, redundancy: str = "None",
                 finding_description: str | None = None):
    equipment = dict(zip(EQUIPMENT_FIELDS, (
        "PMP-8001", "Pump", "Synthetic utility service", "3", "7",
        "Yes" if sce else "No", redundancy, "Partner availability is not verified.",
    )))
    rows = [dict(zip(FINDING_FIELDS, (
        f"F-{8001+i}", "2025-01-01", "PMP-8001", "Pump", "Routine",
        "Visual", finding_description or QUOTE + " Verify function before use.",
        "Synthetic inspector", "Inspector",
    ))) for i in range(count)]
    findings, registry = root / "findings.csv", root / "registry.csv"
    write_csv(findings, FINDING_FIELDS, rows)
    write_csv(registry, EQUIPMENT_FIELDS, [equipment])
    return read_inputs(findings, registry)


class FixtureContext:
    """Test-only context producer; deliberately not an actual knowledge module."""

    def __init__(self, inputs, gaps=None):
        knowledge = {"knowledge:fixture": "Synthetic guidance: justify scores using supplied evidence."}
        manifest = [{"source_id": key, "kind": "managed_knowledge", "sha256": digest(value.encode())}
                    for key, value in knowledge.items()]
        self.snapshot = {
            "knowledge_version": "fixture-v1", "content": knowledge,
            "content_hash": digest(canonical(knowledge).encode()),
            "source_manifest": manifest, "approved": True,
        }
        data = inputs.data
        index = {f"{kind}:{identifier}:{field}": value
                 for kind, rows in (("finding", data["findings"]), ("equipment", data["registry"]))
                 for identifier, row in rows.items() for field, value in row.items()}
        index.update(knowledge)
        self.bundle = {
            "contract_version": "triage-export-v0", "payload": {**data, "knowledge": deepcopy(knowledge)},
            "source_index": index, "finding_ids": sorted(data["findings"]),
            "knowledge_version": "fixture-v1", "assessment_time": CUTOFF,
            "source_manifest": [
                {"source_id": "findings", "kind": "finding_input", "sha256": inputs.findings_hash},
                {"source_id": "registry", "kind": "registry_input", "sha256": inputs.registry_hash},
                *manifest,
            ], "purpose": "normal", "gaps": gaps or [],
        }
        self.read_calls = 0
        self.rehash()

    def rehash(self):
        self.bundle["context_hash"] = digest(context_body(self.bundle).encode())

    def read_export(self):
        self.read_calls += 1
        return deepcopy({"snapshot": self.snapshot, "bundle": self.bundle})


def facts():
    return {name: {
        "state": "unknown", "applicability": "applicable",
        "reason": "Not established in inspected synthetic sources.",
        "evidence": [], "sources_checked": [REFERENCE],
        "verification_activity": None,
    } for name in FACT_NAMES}


def assessment(identifier="F-8001", likelihood=2, impact=3):
    support = {"rationale": "Synthetic component test, not a domain assessment.",
               "evidence": [{"source_ref": REFERENCE, "quote": QUOTE}]}
    return {
        "status": "assessed", "finding_id": identifier, "equipment_id": "PMP-8001",
        "summary": "Synthetic surface observation.", "recommended_action": "Inspect the surface.",
        "likelihood_of_failure": {"score": likelihood, **deepcopy(support)},
        "impact_of_failure": {"score": impact, **deepcopy(support)},
        "facts": facts(), "uncertainties": [], "inability_reason": None,
    }


def receipt():
    return {
        "provider": "synthetic-no-network", "sdk_retries": 0, "http_transport_retries": 0,
        "follow_redirects": False, "tools": False, "http_dispatches_observed": 1,
        "adapter_attempts": 1, "wire_message_hashes_match": True,
        "usage": None, "usd_cost": None, "observed_model": "synthetic-not-an-LLM",
    }


def native_response(value, catalog, same_day_attention=None):
    value = deepcopy(value)
    if (isinstance(value.get("likelihood_of_failure"), dict) and isinstance(value.get("facts"), dict)
            and "required_function_failed" in value["facts"]):
        value["likelihood_of_failure"]["required_function_failed"] = value["facts"].pop(
            "required_function_failed")
    response = {"assessment": value, "same_day_attention": deepcopy(same_day_attention or []),
                "citation_catalog_sha256": digest(canonical(catalog).encode())}
    selections = {(item["source_ref"], item["quote"]): key for key, item in catalog.items()}

    def selector(citation):
        if (not isinstance(citation, dict) or set(citation) != {"source_ref", "quote"}
                or not isinstance(citation["source_ref"], str) or not isinstance(citation["quote"], str)):
            return citation
        exact = selections.get((citation["source_ref"], citation["quote"]))
        if exact is not None:
            return exact
        matches = [key for key, item in catalog.items()
                   if item["source_ref"] == citation["source_ref"] and citation["quote"].strip()
                   and citation["quote"] in item["quote"]]
        return matches[0] if len(matches) == 1 else citation

    def select(item):
        if isinstance(item, dict):
            for name, child in item.items():
                if name in {"evidence", "directive_evidence", "trigger_evidence"} and isinstance(child, list):
                    item[name] = [selector(citation) for citation in child]
                else:
                    select(child)
        elif isinstance(item, list):
            for child in item:
                select(child)
    select(response)
    return response


class FakeProvider:
    def __init__(self, responses=None, *, close_error=False, enter_error=False, configuration=None):
        self.responses = list(responses if responses is not None else [assessment()])
        self.requests = []
        self.close_error, self.enter_error = close_error, enter_error
        self.settings = configuration if configuration is not None else receipt()

    def configuration(self):
        return deepcopy(self.settings)

    async def __aenter__(self):
        if self.enter_error:
            raise InferenceError("authentication", "Synthetic startup failure")
        return self

    async def __aexit__(self, *args):
        if self.close_error:
            raise InferenceError("cleanup", "Synthetic shutdown failure")

    async def generate(self, request):
        self.requests.append(request)
        value = self.responses.pop(0)
        if callable(value):
            value = value(request)
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, InferenceResponse):
            return value
        message = json.loads(request.user)
        if message.get("assessment_contract") in {
            NATIVE_ASSESSMENT_CONTRACT, "native-assessment-v3", "native-assessment-v4",
        }:
            try:
                candidate = strict_json(value) if isinstance(value, str) else deepcopy(value)
            except (ValueError, RecursionError):
                candidate = None
            if isinstance(candidate, dict) and "status" in candidate:
                value = native_response(candidate, message["citation_catalog"])
        return InferenceResponse(value if isinstance(value, str) else canonical(value), None, receipt())


class Artifacts:
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        try:
            if ARTIFACT_ROOT is not None:
                destination = ARTIFACT_ROOT / digest(self.id().encode())[:16]
                shutil.copytree(self.root, destination)
                (destination / "test-id.json").write_text(json.dumps({"test_id": self.id()}),
                                                         encoding="utf-8")
        finally:
            self.temporary.cleanup()

    def config(self, budget=20, **kwargs):
        return RunConfig(model="synthetic-deployment", knowledge_version="fixture-v1",
                         assessment_time=CUTOFF, phase_attempt_budget=budget,
                         attempt_ledger=str(self.root / "phase-ledger.json"), **kwargs)
