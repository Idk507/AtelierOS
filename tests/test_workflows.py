from fastapi.testclient import TestClient

from apps.api.main import create_app
from tests.test_api import headers, setup_garment


def test_checkpoint_review_replay_and_explicit_commit(api):
    garment = setup_garment(api)
    client = api["client"]
    root = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    command = {
        **base,
        "mode": "geometry",
        "edit": {"component_id": "sleeve", "geometry": [0, 0, 80, 140]},
    }
    assert (
        client.post(
            root + "/workflows",
            headers=headers(api),
            json={**command, "edit": {**command["edit"], "component_id": "neckline"}},
        ).status_code
        == 409
    )
    assert (
        client.post(
            root + "/workflows", headers=headers(api), json={**command, "tools": ["write_revision"]}
        ).status_code
        == 422
    )
    created = client.post(root + "/workflows", headers=headers(api), json=command)
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["status"] == "awaiting_review" and run["proposal_id"] is None
    assert client.get(root + "/workflows", headers=headers(api)).json()[0] == run
    route = root + f"/workflows/{run['id']}/decision"
    decision = {**base, "decision": "approve", "checkpoint_digest": run["checkpoint_digest"]}
    assert client.post(route, headers=headers(api), json=decision).status_code == 403
    assert (
        client.post(
            route, headers=headers(api, organization_id=api["other_id"]), json=decision
        ).status_code
        == 404
    )
    assert (
        client.post(
            route,
            headers=headers(api, "patternmaker"),
            json={**decision, "checkpoint_digest": "tampered"},
        ).status_code
        == 409
    )
    replay_key = headers(api, "patternmaker")
    with TestClient(create_app(api["settings"], engine=api["engine"])) as restarted:
        result = restarted.post(route, headers=replay_key, json=decision)
        assert result.status_code == 200, result.text
    assert client.post(route, headers=replay_key, json=decision).json() == result.json()
    assert (
        client.post(route, headers=headers(api, "patternmaker"), json=decision).status_code == 409
    )
    assert (
        client.get(root, headers=headers(api)).json()["draft_revision_id"] == base["base_revision"]
    )
    proposal = result.json()["proposal_id"]
    committed = client.post(
        root + f"/patch-proposals/{proposal}/accept", headers=headers(api), json=base
    )
    assert committed.status_code == 201, committed.text


def test_concept_can_be_cancelled_without_creating_a_revision(api):
    garment = setup_garment(api)
    client = api["client"]
    route = f"/v1/garments/{garment['id']}/workflows"
    base = {"base_revision": garment["draft_revision_id"]}
    result = client.post(route, headers=headers(api), json={**base, "mode": "concept"})
    assert result.status_code == 201, result.text
    run = result.json()
    assert run["result"]["thumbnail_jpeg"] and run["result"]["estimated_cost"] == 0
    decision = client.post(
        route + f"/{run['id']}/decision",
        headers=headers(api),
        json={**base, "decision": "cancel", "checkpoint_digest": run["checkpoint_digest"]},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "cancelled" and decision.json()["proposal_id"] is None
