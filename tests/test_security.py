"""Additional authorization, lock, transport and aggregate race regressions."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apps.api.models import Audit, Membership, ProjectGrant, User
from packages.domain.design import content_hash
from tests.test_api import headers, proposal, setup_garment


def test_valid_other_tenant_and_revoked_project_cannot_read_or_replay(api):
    garment = setup_garment(api)
    with Session(api["engine"]) as session, session.begin():
        outsider = User(subject="outsider", created_by="test")
        session.add(outsider)
        session.flush()
        session.add(
            Membership(
                organization_id=api["other_id"],
                user_id=outsider.id,
                created_by="test",
                roles=["designer"],
                active=True,
            )
        )
    client = api["client"]
    outsider_headers = headers(api, "outsider", organization_id=api["other_id"])
    endpoint = f"/v1/garments/{garment['id']}"
    assert client.get(endpoint, headers=outsider_headers).status_code == 404
    assert client.get(endpoint + "/audit", headers=outsider_headers).status_code == 404
    assert (
        client.post(
            endpoint + "/patch-proposals",
            headers=outsider_headers,
            json={
                "base_revision": garment["draft_revision_id"],
                "operations": [
                    {"op": "update", "target_component_id": "sleeve", "payload": {"geometry": [1]}}
                ],
                "justification": "forged",
            },
        ).status_code
        == 404
    )
    with Session(api["engine"]) as session, session.begin():
        session.execute(
            delete(ProjectGrant).where(ProjectGrant.user_id == api["users"]["designer"])
        )
    assert client.get(endpoint, headers=headers(api)).status_code == 404


@pytest.mark.parametrize(
    "target,op,payload",
    [
        ("neckline", "update", {"geometry": [1]}),
        ("bodice", "delete", {}),
        ("neckline", "update", {"locked": False}),
    ],
)
def test_http_lock_bypass_denied_and_audited(api, target, op, payload):
    garment = setup_garment(api)
    response = api["client"].post(
        f"/v1/garments/{garment['id']}/patch-proposals",
        headers=headers(api),
        json={
            "base_revision": garment["draft_revision_id"],
            "operations": [{"op": op, "target_component_id": target, "payload": payload}],
            "justification": "attempted bypass",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "locked_component"
    with Session(api["engine"]) as session:
        assert (
            session.scalar(
                select(func.count()).select_from(Audit).where(Audit.event_type == "security.denied")
            )
            == 1
        )


def test_unlock_requires_distinct_admin_and_preserves_geometry(api):
    garment = setup_garment(api)
    client = api["client"]
    gid, base = garment["id"], garment["draft_revision_id"]
    before = client.get(f"/v1/garments/{gid}", headers=headers(api)).json()
    request = client.post(
        f"/v1/garments/{gid}/unlock-requests",
        headers=headers(api),
        json={"base_revision": base, "component_id": "neckline", "reason": "Client revision"},
    )
    assert request.status_code == 201
    route = f"/v1/garments/{gid}/unlock-requests/{request.json()['id']}/decisions"
    assert (
        client.post(
            route, headers=headers(api), json={"base_revision": base, "decision": "grant"}
        ).status_code
        == 403
    )
    allowed = client.post(
        route, headers=headers(api, "org-admin"), json={"base_revision": base, "decision": "grant"}
    )
    assert allowed.status_code == 201, allowed.text
    after = client.get(f"/v1/garments/{gid}", headers=headers(api)).json()
    assert after["approved_revision_id"] is None
    assert after["design"]["components"][1]["locked"] is False
    for old, new in zip(before["design"]["components"], after["design"]["components"], strict=True):
        assert old["geometry"] == new["geometry"]
    assert before["content_hash"] != after["content_hash"]
    assert content_hash(before["design"]) == before["content_hash"]


def test_parallel_duplicate_create_returns_one_original_result(api):
    hdr = headers(api)

    def create(_):
        response = api["client"].post("/v1/projects", headers=hdr, json={"name": "Once"})
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert results[0] == results[1]
    assert results[0][0] == 201


def test_approval_edit_race_never_promotes_wrong_head(api):
    garment = setup_garment(api)
    client = api["client"]
    gid, base = garment["id"], garment["draft_revision_id"]
    patch = proposal(api, garment)

    def approve():
        return client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api),
            json={
                "base_revision": base,
                "revision_id": base,
                "content_hash": garment["content_hash"],
                "purpose": "aesthetic",
                "decision": "approve",
            },
        ).status_code

    def edit():
        return client.post(
            f"/v1/garments/{gid}/patch-proposals/{patch['id']}/accept",
            headers=headers(api),
            json={"base_revision": base},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        approval, changed = pool.submit(approve), pool.submit(edit)
        assert approval.result() in (201, 409)
        assert changed.result() == 201
    result = client.get(f"/v1/garments/{gid}", headers=headers(api)).json()
    assert result["approved_revision_id"] in (None, base)
    assert result["draft_revision_id"] != base


def test_missing_idempotency_oversized_body_and_safe_errors(api):
    client = api["client"]
    auth = {"Authorization": "Bearer " + api["token"]()}
    response = client.post("/v1/projects", headers=auth, json={"name": "No key"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    oversized = client.post("/v1/projects", headers=headers(api), content=b"x" * 1_048_577)
    assert oversized.status_code == 413
    assert "postgresql" not in oversized.text
    assert client.get("/health/ready").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_tenant_fk_rejects_revision_parent_substitution(api):
    garment = setup_garment(api)
    # Even direct SQL cannot assign a head to a revision outside the aggregate.
    other = setup_garment(api)
    with pytest.raises(DBAPIError), api["engine"].begin() as connection:
        from sqlalchemy import text

        connection.execute(
            text("UPDATE garments SET draft_revision_id=:revision WHERE id=:id"),
            {"revision": other["draft_revision_id"], "id": garment["id"]},
        )


def test_cross_language_hash_vectors():
    import json
    from pathlib import Path

    vectors = json.loads(Path("docs/contracts/hash-vectors.json").read_text(encoding="utf-8"))
    for vector in vectors:
        assert content_hash(vector["payload"]) == vector["sha256"]


def test_project_create_replay_rechecks_revoked_project_grant(api):
    hdr = headers(api)
    client = api["client"]
    response = client.post("/v1/projects", headers=hdr, json={"name": "Revoked project"})
    assert response.status_code == 201
    with Session(api["engine"]) as session, session.begin():
        session.execute(
            delete(ProjectGrant).where(ProjectGrant.project_id == response.json()["id"])
        )
    assert (
        client.post("/v1/projects", headers=hdr, json={"name": "Revoked project"}).status_code
        == 404
    )


def test_self_unlock_denied_even_with_both_roles(api):
    garment = setup_garment(api)
    with Session(api["engine"]) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.user_id == api["users"]["designer"])
        )
        member.roles = ["designer", "org-admin"]
    gid, base = garment["id"], garment["draft_revision_id"]
    request = api["client"].post(
        f"/v1/garments/{gid}/unlock-requests",
        headers=headers(api),
        json={"base_revision": base, "component_id": "neckline", "reason": "Self grant attempt"},
    )
    assert request.status_code == 201
    response = api["client"].post(
        f"/v1/garments/{gid}/unlock-requests/{request.json()['id']}/decisions",
        headers=headers(api),
        json={"base_revision": base, "decision": "grant"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "self_unlock_forbidden"


def test_nonfinite_geometry_is_a_structured_rejection(api):
    garment = setup_garment(api)
    response = api["client"].post(
        f"/v1/garments/{garment['id']}/patch-proposals",
        headers={**headers(api), "Content-Type": "application/json"},
        content=(
            ' {"base_revision":"' + garment["draft_revision_id"] + '",'
            '"operations":[{"op":"update","target_component_id":"sleeve",'
            '"payload":{"geometry":[NaN]}}],"justification":"invalid number"}'
        ),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_payload"


def test_designer_can_add_lock_but_cannot_use_constraint_to_unlock(api):
    garment = setup_garment(api)
    client = api["client"]
    gid, base = garment["id"], garment["draft_revision_id"]
    command = {"base_revision": base, "component_id": "sleeve", "kind": "hard_lock"}
    response = client.post(f"/v1/garments/{gid}/constraints", headers=headers(api), json=command)
    assert response.status_code == 201, response.text
    updated = client.get(f"/v1/garments/{gid}", headers=headers(api)).json()
    assert updated["design"]["components"][2]["locked"] is True
    assert updated["approved_revision_id"] is None
    assert (
        client.post(
            f"/v1/garments/{gid}/constraints",
            headers=headers(api),
            json={**command, "base_revision": updated["draft_revision_id"], "kind": "unlock"},
        ).status_code
        == 422
    )
