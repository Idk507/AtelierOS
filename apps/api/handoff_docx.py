"""Editable Word handoff document from a frozen canonical review package."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.shared import Inches

from packages.domain.design import DomainError


def render_handoff_docx(export: dict[str, Any], organization_id: str, artifact_id: str) -> bytes:
    """Build a bounded editable DOCX while preserving exact Unicode evidence."""
    package = export["package"]
    document = Document()
    document.add_heading("Technical review draft", 0)
    document.add_paragraph(
        f"Status: {export['status']} | Current revision: {export['current']}"
    )
    document.add_paragraph(
        "Draft only. Fit, sewing patterns and manufacturability require professional validation."
    )
    document.add_heading("Manifest", level=1)
    manifest = {
        "Organization": organization_id,
        "Garment": package["garment_id"],
        "Artifact": artifact_id,
        "Revision": package["revision_id"],
        "Revision digest": package["revision_digest"],
        "Package digest": export["digest"],
    }
    table = document.add_table(rows=0, cols=2)
    table.style = "Light Shading Accent 1"
    for label, value in manifest.items():
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    document.add_heading("Design geometry", level=1)
    document.add_paragraph("Front and back views are not identified in the design model.")
    document.add_paragraph("Canonical design JSON")
    document.add_paragraph(str(package["design"]))

    document.add_heading("Measurements and provenance", level=1)
    measurements = package.get("measurements") or []
    if not measurements:
        document.add_paragraph("No measurements recorded; points of measure remain open.")
    for row in measurements[:30]:
        document.add_paragraph(
            f"{row['label']}: {row['value']} {row['unit']} — source: {row['source']}; "
            f"recorded by {row['recorded_by']}"
        )

    document.add_heading("Materials and cost", level=1)
    offer = package.get("material_offer")
    document.add_paragraph(
        f"Material: {offer.get('name', 'Unknown')} | evidence: {offer.get('evidence', 'Unknown')}"
        if offer else "Material evidence not recorded."
    )
    document.add_paragraph(f"Estimate: {package.get('material_estimate', 'Not available')}")

    document.add_heading("Sample findings", level=1)
    findings = package.get("sample_feedback") or []
    if not findings:
        document.add_paragraph("No sample findings recorded.")
    for row in findings[:30]:
        document.add_paragraph(
            f"{row['sample_label']} | {row['severity']} | {row['observation']} | "
            f"recorded by {row['recorded_by']}"
        )
        if row.get("resolution"):
            document.add_paragraph(
                f"Resolution: {row['resolution']['note']} | by {row['resolution']['by']}"
            )
    document.add_heading("Review questions", level=1)
    for question in (
        "Identify required points of measure and tolerances.",
        "Confirm front and back views and technical construction details.",
        "Review material, BOM, cost assumptions and unresolved findings.",
        "Record professional limitations and required corrective actions.",
    ):
        document.add_paragraph(question, style="List Bullet")
    document.add_paragraph("No production release is available without a professional completeness assessment.")
    output = BytesIO()
    document.save(output)
    data = output.getvalue()
    if len(data) > 2 * 1024 * 1024:
        raise DomainError("export_too_large", 422)
    return data
