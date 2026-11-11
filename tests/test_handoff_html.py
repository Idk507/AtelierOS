"""Editable export preserves scope, evidence and safe download behavior."""

from tests.test_api import headers, setup_garment
from tests.test_handoff import approve, draft


def test_html_download_escapes_unicode_and_denies_other_tenant(api):
    garment = setup_garment(api)
    approve(api, garment, "aesthetic")
    route = f"/v1/garments/{garment['id']}"
    path, package = draft(api, route, {"base_revision": garment["draft_revision_id"]})
    response = api["client"].get(path + "/html", headers=headers(api))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "attachment" in response.headers["content-disposition"]
    assert "sandbox" in response.headers["content-security-policy"]
    assert package["digest"] in response.text
    denied = api["client"].get(
        path + "/html", headers=headers(api, organization_id=api["other_id"])
    )
    assert denied.status_code in (403, 404)


def test_html_renderer_preserves_unicode_and_escapes_markup():
    from apps.api.handoff_html import render_handoff_html

    export = {
        "status": "needs_review",
        "current": False,
        "digest": "digest",
        "package": {
            "garment_id": "g",
            "revision_id": "r",
            "revision_digest": "h",
            "observation": "<script>alert(1)</script> नमस्ते",
        },
    }
    html = render_handoff_html(export, "org", "artifact").decode("utf-8")
    assert "नमस्ते" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "needs_review" in html
