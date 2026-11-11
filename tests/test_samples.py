"""Synthetic PostgreSQL acceptance cases for revision-bound sample evidence."""

import pytest

from tests.test_api import headers, proposal, setup_garment


def finding(garment):
    return {
        "base_revision": garment["draft_revision_id"],
        "sample_label": "Synthetic toile 1",
        "component_id": "sleeve",
        "observation": "Sleeve needs review",
        "severity": "blocking",
        "measurement": {
            "label": "Sleeve length",
            "value": "52.5",
            "unit": "cm",
            "source": "Synthetic manual measurement",
        },
    }


def test_sample_replay_resolution_and_provenance(api):
    garment = setup_garment(api)
    client = api["client"]
    route = f"/v1/garments/{garment['id']}/samples"
    body = finding(garment)
    auth = headers(api)
    created = client.post(route, headers=auth, json=body)
    assert created.status_code == 201, created.text
    assert client.post(route, headers=auth, json=body).json() == created.json()
    assert (
        client.post(route, headers=auth, json={**body, "observation": "Different"}).status_code
        == 409
    )
    rows = client.get(route, headers=headers(api)).json()
    assert len(rows) == 1
    assert rows[0]["recorded_by"] == api["users"]["designer"]
    assert rows[0]["measurement"]["value"] == "52.5"
    resolution_route = route + f"/{created.json()['id']}/resolve"
    resolution = {
        "base_revision": body["base_revision"],
        "resolution": "Synthetic review completed",
    }
    assert client.post(resolution_route, headers=headers(api), json=resolution).status_code == 403
    auth = headers(api, "patternmaker")
    resolved = client.post(resolution_route, headers=auth, json=resolution)
    assert resolved.status_code == 200, resolved.text
    assert client.post(resolution_route, headers=auth, json=resolution).json() == resolved.json()
    assert (
        client.post(
            resolution_route, headers=headers(api, "patternmaker"), json=resolution
        ).status_code
        == 409
    )
    row = client.get(route, headers=headers(api)).json()[0]
    assert row["observation"] == body["observation"]
    assert row["resolution"]["by"] == api["users"]["patternmaker"]


def test_sample_scope_roles_and_stale_revision(api):
    garment = setup_garment(api)
    client = api["client"]
    route = f"/v1/garments/{garment['id']}/samples"
    body = finding(garment)
    assert client.post(route, headers=headers(api, "client-reviewer"), json=body).status_code == 403
    assert (
        client.post(route, headers=headers(api, principal_type="service"), json=body).status_code
        == 403
    )
    assert (
        client.get(route, headers=headers(api, organization_id=api["other_id"])).status_code == 404
    )
    assert (
        client.post(
            route, headers=headers(api), json={**body, "component_id": "missing"}
        ).status_code
        == 422
    )
    patch = proposal(api, garment)
    accepted = client.post(
        f"/v1/garments/{garment['id']}/patch-proposals/{patch['id']}/accept",
        headers=headers(api),
        json={"base_revision": body["base_revision"]},
    )
    assert accepted.status_code == 201, accepted.text
    assert client.post(route, headers=headers(api), json=body).status_code == 409
    assert client.get(route, headers=headers(api)).json() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"measurement": {"label": "Length", "value": "0", "unit": "cm", "source": "Synthetic"}},
        {"photo_jpeg": "invalid"},
        {"photo_jpeg": "invalid", "photo_rights_confirmed": True},
        {"annotation": {"x": 10, "y": 20}},
        {"annotation": {"x": 1001, "y": 20}},
    ],
)
def test_sample_invalid_evidence_has_no_effect(api, changes):
    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}/samples"
    response = api["client"].post(route, headers=headers(api), json={**finding(garment), **changes})
    assert response.status_code == 422, response.text
    assert api["client"].get(route, headers=headers(api)).json() == []
