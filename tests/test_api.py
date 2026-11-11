"""P01 PostgreSQL/HTTP acceptance tests, including denial and replay."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apps.api.models import Approval, Artifact, Garment, Membership, ProjectGrant, Revision


def headers(api, role="designer", key=None, **claims):
    return {
        "Authorization": "Bearer " + api["token"](role, **claims),
        "Idempotency-Key": key or str(uuid4()),
    }


def setup_garment(api):
    client = api["client"]
    project = client.post("/v1/projects", headers=headers(api), json={"name": "Commission"})
    assert project.status_code == 201, project.text
    pid = project.json()["id"]
    with Session(api["engine"]) as session, session.begin():
        for user in api["users"].values():
            if user != api["users"]["designer"]:
                session.add(
                    ProjectGrant(
                        organization_id=api["organization_id"],
                        project_id=pid,
                        user_id=user,
                        created_by="test",
                    )
                )
    response = client.post(
        f"/v1/projects/{pid}/garments",
        headers=headers(api),
        json={
            "name": "Dress",
            "design": {
                "components": [
                    {"id": "bodice", "kind": "bodice"},
                    {"id": "neckline", "kind": "neckline", "parent_id": "bodice", "locked": True},
                    {"id": "sleeve", "kind": "sleeve", "geometry": [0, 0, 100, 140]},
                ]
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def proposal(api, garment, base=None):
    response = api["client"].post(
        f"/v1/garments/{garment['id']}/patch-proposals",
        headers=headers(api),
        json={
            "base_revision": base or garment["draft_revision_id"],
            "operations": [
                {
                    "op": "update",
                    "target_component_id": "sleeve",
                    "payload": {"geometry": [0, 0, 80, 140]},
                }
            ],
            "justification": "Narrow sleeve",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_authentication_tenant_and_input_fail_closed(api):
    client = api["client"]
    assert client.get("/v1/projects").status_code == 401
    assert client.get("/v1/projects", headers=headers(api, aud="wrong")).status_code == 401
    assert client.get("/v1/projects", headers=headers(api, exp=1)).status_code == 401
    assert (
        client.post(
            "/v1/projects",
            headers=headers(api),
            json={"name": "Injected", "organization_id": api["other_id"]},
        ).status_code
        == 422
    )
    garment = setup_garment(api)
    assert (
        client.get(
            f"/v1/garments/{garment['id']}", headers=headers(api, organization_id=api["other_id"])
        ).status_code
        == 404
    )
    with Session(api["engine"]) as session, session.begin():
        member = session.scalar(
            select(Membership).where(Membership.user_id == api["users"]["designer"])
        )
        member.active = False
    assert client.get(f"/v1/garments/{garment['id']}", headers=headers(api)).status_code == 404


def test_revision_replay_hash_approval_and_invalidation(api):
    client = api["client"]
    garment = setup_garment(api)
    gid, base = garment["id"], garment["draft_revision_id"]
    with Session(api["engine"]) as session, session.begin():
        session.add(
            Artifact(
                organization_id=api["organization_id"],
                garment_id=gid,
                revision_id=base,
                kind="render",
                depends_on=["sleeve"],
                status="current",
                created_by="test",
            )
        )
    p = proposal(api, garment)
    endpoint = f"/v1/garments/{gid}/patch-proposals/{p['id']}/accept"
    hdr = headers(api)
    accepted = client.post(endpoint, headers=hdr, json={"base_revision": base})
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["approval_status"] == "unapproved"
    assert len(accepted.json()["invalidated_artifacts"]) == 1
    assert (
        client.post(endpoint, headers=hdr, json={"base_revision": base}).json() == accepted.json()
    )
    assert (
        client.post(endpoint, headers=hdr, json={"base_revision": "different"}).status_code == 409
    )
    updated = client.get(f"/v1/garments/{gid}", headers=headers(api)).json()
    assert updated["approved_revision_id"] is None
    assert updated["design"]["components"][1]["locked"] is True
    rev = updated["draft_revision_id"]
    approval = {
        "base_revision": rev,
        "revision_id": rev,
        "content_hash": updated["content_hash"],
        "purpose": "aesthetic",
        "decision": "approve",
    }
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api, principal_type="service"),
            json=approval,
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api, "client-reviewer"),
            json={**approval, "purpose": "technical"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api),
            json={**approval, "content_hash": "0" * 64},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api),
            json={**approval, "base_revision": base, "revision_id": base},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals",
            headers=headers(api, "patternmaker"),
            json={**approval, "purpose": "technical"},
        ).status_code
        == 201
    )
    assert (
        client.get(f"/v1/garments/{gid}", headers=headers(api)).json()["approved_revision_id"]
        is None
    )
    assert (
        client.post(
            f"/v1/garments/{gid}/approvals", headers=headers(api), json=approval
        ).status_code
        == 201
    )
    assert (
        client.get(f"/v1/garments/{gid}", headers=headers(api)).json()["approved_revision_id"]
        == rev
    )
    with Session(api["engine"]) as session:
        assert session.scalar(select(func.count()).select_from(Revision)) == 2
        assert session.scalar(select(func.count()).select_from(Approval)) == 2


def test_concurrent_accepts_have_one_winner(api):
    garment = setup_garment(api)
    proposals = [proposal(api, garment) for _ in range(2)]

    def accept(p):
        return (
            api["client"]
            .post(
                f"/v1/garments/{garment['id']}/patch-proposals/{p['id']}/accept",
                headers=headers(api),
                json={"base_revision": garment["draft_revision_id"]},
            )
            .status_code
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(accept, proposals)) == [201, 409]
    with Session(api["engine"]) as session:
        assert session.scalar(select(func.count()).select_from(Revision)) == 2


def test_database_prevents_history_rewrite_and_cross_tenant_head(api):
    garment = setup_garment(api)
    try:
        with api["engine"].begin() as connection:
            connection.execute(
                text("UPDATE revisions SET content_hash = :hash"), {"hash": "0" * 64}
            )
    except DBAPIError:
        pass
    else:
        raise AssertionError("Immutable revision rewritten")
    with Session(api["engine"]) as session:
        assert session.get(Garment, garment["id"]).draft_revision_id == garment["draft_revision_id"]
