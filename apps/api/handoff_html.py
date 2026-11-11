"""Bounded editable HTML review document; not a DOCX or validated technical pack."""

import json
from html import escape
from typing import Any

from packages.domain.design import DomainError


def render_handoff_html(export: dict[str, Any], organization_id: str, artifact_id: str) -> bytes:
    """Preserve exact Unicode evidence in an escaped, self-contained document."""
    package = export["package"]
    metadata = {
        "organization_id": organization_id,
        "artifact_id": artifact_id,
        "garment_id": package["garment_id"],
        "revision_id": package["revision_id"],
        "revision_digest": package["revision_digest"],
        "package_digest": export["digest"],
        "status": export["status"],
        "current": export["current"],
    }
    rows = "".join(
        f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in metadata.items()
    )
    content = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        "<title>AtelierOS editable review draft</title></head><body>"
        "<h1>Technical review draft</h1><p>Editable HTML document; not DOCX. "
        "Fit, sewing patterns and manufacturability require professional validation.</p>"
        "<h2>Manifest and review status</h2><table>" + rows + "</table>"
        "<h2>Canonical evidence snapshot</h2><p>Front and back views are not identified. "
        "Missing measurements and material evidence remain open questions.</p><pre>"
        + escape(json.dumps(package, ensure_ascii=False, indent=2))
        + "</pre></body></html>"
    ).encode("utf-8")
    if len(content) > 2 * 1024 * 1024:
        raise DomainError("export_too_large", 422)
    return content
