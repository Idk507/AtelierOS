"""Synthetic PostgreSQL checks for revision-bound release and frozen evidence."""

import pytest

from tests.test_api import headers, setup_garment


def approve(api, garment, purpose):
    response = api["client"].post(
        f"/v1/garments/{garment['id']}/approvals",
        headers=headers(api, "patternmaker" if purpose == "technical" else "designer"),
        json={
            "base_revision": garment["draft_revision_id"],
            "revision_id": garment["draft_revision_id"],
            "content_hash": garment["content_hash"],
            "purpose": purpose,
            "decision": "approve",
        },
    )
    assert response.status_code == 201, response.text


def draft(api, route, base):
    response = api["client"].post(route + "/handoff", headers=headers(api), json=base)
    assert response.status_code == 201, response.text
    path = route + "/handoff/" + response.json()["id"]
    return path, api["client"].get(path, headers=headers(api)).json()


def finding(api, route, base, severity="note", measured=True):
    response = api["client"].post(
        route + "/samples",
        headers=headers(api),
        json={
            **base,
            "sample_label": "Synthetic toile",
            "observation": "Check sleeve length",
            "severity": severity,
            "measurement": {
                "label": "Sleeve length",
                "value": "42.5",
                "unit": "cm",
                "source": "Synthetic manual measurement",
            }
            if measured
            else None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_release_fails_closed_without_professional_completeness_assessment(api):
    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approve(api, garment, "aesthetic")
    finding(api, route, base)
    approve(api, garment, "technical")
    path, exported = draft(api, route, base)
    body = {**base, "digest": exported["digest"]}
    client = api["client"]
    assert client.post(path + "/release", headers=headers(api), json=body).status_code == 403
    assert (
        client.post(
            path + "/release", headers=headers(api, "production"), json={**body, "digest": "0" * 64}
        ).status_code
        == 409
    )
    authorization = headers(api, "production")
    released = client.post(path + "/release", headers=authorization, json=body)
    assert released.status_code == 409, released.text
    assert released.json()["error"]["code"] == "professional_completeness_assessment_required"
    replay = client.post(path + "/release", headers=authorization, json=body)
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "professional_completeness_assessment_required"
    assert client.get(path, headers=headers(api)).json()["release"] is None
    finding(api, route, base)
    stale = client.get(path, headers=headers(api)).json()
    assert stale["status"] == "needs_review"
    assert stale["release"] is None
    assert stale["digest"] == exported["digest"]
    assert stale["package"] == exported["package"]
    rejected = client.post(path + "/release", headers=headers(api, "production"), json=body)
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "sample_snapshot_changed"


@pytest.mark.parametrize(
    "measured,severity,error",
    [
        (False, "note", "measurement_evidence_required"),
        (True, "blocking", "open_sample_findings"),
    ],
)
def test_incomplete_sample_evidence_cannot_release(api, measured, severity, error):
    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approve(api, garment, "aesthetic")
    finding(api, route, base, severity, measured)
    approve(api, garment, "technical")
    path, exported = draft(api, route, base)
    response = api["client"].post(
        path + "/release",
        headers=headers(api, "production"),
        json={**base, "digest": exported["digest"]},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == error


def test_technical_review_must_follow_latest_sample_evidence(api):
    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approve(api, garment, "aesthetic")
    approve(api, garment, "technical")
    finding(api, route, base)
    path, exported = draft(api, route, base)
    body = {**base, "digest": exported["digest"]}
    response = api["client"].post(path + "/release", headers=headers(api, "production"), json=body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "technical_approval_required"
    approve(api, garment, "technical")
    response = api["client"].post(path + "/release", headers=headers(api, "production"), json=body)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "professional_completeness_assessment_required"


def test_concurrent_feedback_and_release_never_leave_active_stale_release(api):
    from concurrent.futures import ThreadPoolExecutor

    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approve(api, garment, "aesthetic")
    finding(api, route, base)
    approve(api, garment, "technical")
    path, exported = draft(api, route, base)
    with ThreadPoolExecutor(max_workers=2) as executor:
        release = executor.submit(
            api["client"].post,
            path + "/release",
            headers=headers(api, "production"),
            json={**base, "digest": exported["digest"]},
        )
        feedback = executor.submit(finding, api, route, base)
        assert release.result().status_code == 409
        assert feedback.result()
    result = api["client"].get(path, headers=headers(api)).json()
    assert result["release"] is None
    assert result["status"] == "needs_review"
    assert result["package"] == exported["package"]


def test_pdf_export_is_scoped_revision_bound_and_marks_stale(api):
    from io import BytesIO

    from pypdf import PdfReader

    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approve(api, garment, "aesthetic")
    finding(api, route, base)
    path, package = draft(api, route, base)
    client = api["client"]
    response = client.get(path + "/pdf", headers=headers(api))
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert "no-store" in response.headers["cache-control"]
    content = " ".join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
    assert package["digest"] in content
    assert "Front and back views: not identified" in content
    assert "Synthetic manual measurement" in content
    denied = client.get(path + "/pdf", headers=headers(api, organization_id=api["other_id"]))
    assert denied.status_code in (403, 404)
    finding(api, route, base)
    stale = client.get(path + "/pdf", headers=headers(api))
    text = " ".join(page.extract_text() for page in PdfReader(BytesIO(stale.content)).pages)
    assert "NEEDS_REVIEW" in text


def test_pdf_handles_long_untrusted_text_and_discloses_unicode_replacement():
    from io import BytesIO

    from pypdf import PdfReader

    from apps.api.handoff_pdf import render_handoff_pdf

    observation = "<b>" + "X" * 1000 + "</b> नमस्ते"
    export = {
        "status": "needs_review",
        "current": False,
        "digest": "a" * 64,
        "release": None,
        "package": {
            "garment_id": "garment",
            "revision_id": "revision",
            "revision_digest": "b" * 64,
            "design": {"components": [{"geometry": [0, 0, 100, 100]}]},
            "sample_feedback": [
                {
                    "sample_label": "Synthetic",
                    "severity": "note",
                    "observation": observation,
                    "recorded_by": "reviewer",
                    "resolution": None,
                }
            ],
        },
    }
    data = render_handoff_pdf(export, "organization", "artifact")
    reader = PdfReader(BytesIO(data))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "HISTORICAL REVISION" in text
    assert "Text outside Latin-1" in text
    assert "<b>" in text and "</b>" in text
    assert "????" in text
    assert len(data) < 2 * 1024 * 1024
