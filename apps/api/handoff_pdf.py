"""Bounded PDF rendering for revision-bound technical draft packages."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.graphics.shapes import Drawing, PolyLine
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from packages.domain.design import DomainError


def render_handoff_pdf(export: dict[str, Any], organization_id: str, artifact_id: str) -> bytes:
    """Render a portable review draft without changing its canonical package."""
    package = export["package"]
    styles = getSampleStyleSheet()
    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=(595, 842),
        leftMargin=45,
        rightMargin=45,
        topMargin=40,
        bottomMargin=40,
        title="AtelierOS technical draft",
    )
    story: list[Any] = []

    def add(value: Any, style: str = "BodyText") -> None:
        # Built-in PDF fonts support Latin-1. Signal replacement rather than pretending
        # unsupported glyphs were accurately reproduced.
        text = str(value).encode("latin-1", "replace").decode("latin-1")
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles[style]))
        story.append(Spacer(1, 5))

    add("TECHNICAL REVIEW DRAFT", "Title")
    add(
        "Status: "
        + export["status"].upper()
        + (" | HISTORICAL REVISION" if not export["current"] else "")
    )
    add("Draft only. Fit, sewing patterns and manufacturability require professional validation.")
    add("Text outside Latin-1 may be represented by ?; consult the JSON package for exact text.")
    add("Manifest", "Heading2")
    for label, value in [
        ("Organization", organization_id),
        ("Garment", package["garment_id"]),
        ("Artifact", artifact_id),
        ("Revision", package["revision_id"]),
        ("Revision digest", package["revision_digest"]),
        ("Package digest", export["digest"]),
    ]:
        add(f"{label}: {value}")
    add("Semantic component geometry (view not specified)", "Heading2")
    components = package["design"]["components"]
    if sum(len(c.get("geometry", [])) for c in components) > 200_000:
        raise DomainError("export_too_large", 422)
    points = [
        (g[i], g[i + 1])
        for component in components
        for g in [component.get("geometry", [])]
        for i in range(0, len(g) - 1, 2)
    ]
    if len(points) > 100_000:
        raise DomainError("export_too_large", 422)
    if points:
        minx, maxx = min(p[0] for p in points), max(p[0] for p in points)
        miny, maxy = min(p[1] for p in points), max(p[1] for p in points)
        scale = min(490 / max(1, maxx - minx), 200 / max(1, maxy - miny))
        drawing = Drawing(500, 210)
        for component in components:
            g = component.get("geometry", [])
            coords = [
                (5 + (g[i] - minx) * scale, 205 - (g[i + 1] - miny) * scale)
                for i in range(0, len(g) - 1, 2)
            ]
            if len(coords) >= 2:
                drawing.add(
                    PolyLine([v for point in coords for v in point], strokeColor=colors.black)
                )
        story.append(drawing)
    else:
        add("No component geometry recorded.")
    add("Front and back views: not identified; professional review required.")
    add("Measurements and provenance", "Heading2")
    measurements = package.get("measurements") or []
    if not measurements:
        add("No measurements recorded; points of measure remain open.")
    for row in measurements[:30]:
        add(
            f"{row['label']}: {row['value']} {row['unit']} | "
            f"source: {row['source']} | recorded by {row['recorded_by']}"
        )
    add("Materials and cost", "Heading2")
    offer = package.get("material_offer")
    add(
        f"Material: {offer.get('name', 'Unknown')} | evidence: {offer.get('evidence', 'Unknown')}"
        if offer
        else "Material evidence not recorded."
    )
    estimate = package.get("material_estimate")
    add(f"Estimate: {estimate}" if estimate else "Cost estimate not available.")
    add("Sample findings", "Heading2")
    if not package.get("sample_feedback"):
        add("No sample findings recorded.")
    for row in (package.get("sample_feedback") or [])[:30]:
        add(
            f"{row['sample_label']} | {row['severity']} | {row['observation']} | "
            f"recorded by {row['recorded_by']}"
        )
        if row.get("resolution"):
            add(f"Resolution: {row['resolution']['note']} | by {row['resolution']['by']}")
        elif row["severity"] == "blocking":
            add("OPEN BLOCKING FINDING")
    add("Approval", "Heading2")
    add(
        f"Release: {export['release']}"
        if export.get("release")
        else "No current handoff release. Aesthetic and technical approvals "
        "require independent verification."
    )
    doc.build(story)
    data = out.getvalue()
    if len(data) > 2 * 1024 * 1024:
        raise DomainError("export_too_large", 422)
    return data
