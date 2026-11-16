from __future__ import annotations

import csv
import io

from triage_knowledge import TableSource

CUTOFF = "2026-01-01T00:00:00+00:00"
FINDING_FIELDS = (
    "finding_id", "reported_date", "equipment_id", "equipment_type", "inspection_type",
    "inspection_method", "finding_description", "reported_by", "reporter_role",
)
REGISTRY_FIELDS = (
    "equipment_id", "equipment_type", "service_description", "criticality_score",
    "reliability_score", "safety_critical_element", "redundancy", "engineer_comment",
)


def csv_bytes(fields: tuple[str, ...], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def finding(identifier: str = "F-8001", equipment: str = "PMP-8001") -> dict:
    return dict(zip(FINDING_FIELDS, (
        identifier, "2025-01-01", equipment, "Pump", "Routine", "Visual",
        "Visible surface mark. Verify function before use.", "Synthetic inspector", "Inspector",
    )))


def equipment(identifier: str = "PMP-8001", redundancy: str = "None") -> dict:
    return dict(zip(REGISTRY_FIELDS, (
        identifier, "Pump", "Synthetic utility service", "3", "7", "No",
        redundancy, "Partner availability is not verified. Source check \u2713.",
    )))


def tables(findings: list[dict] | None = None, registry: list[dict] | None = None,
           *, input_kind: str = "finding_input") -> tuple[TableSource, TableSource]:
    return (
        TableSource.from_bytes(
            csv_bytes(FINDING_FIELDS, findings if findings is not None else [finding()]),
            source_id="findings", kind=input_kind,
        ),
        TableSource.from_bytes(
            csv_bytes(REGISTRY_FIELDS, registry if registry is not None else [equipment()]),
            source_id="registry", kind="registry_input",
        ),
    )
