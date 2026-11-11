from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models import Artifact
from tests.test_api import headers, setup_garment


def test_material_comparison_and_revision_commit(api):
    client = api["client"]
    garment = setup_garment(api)
    route = f"/v1/garments/{garment['id']}"
    base = {"base_revision": garment["draft_revision_id"]}
    approval = client.post(
        route + "/approvals",
        headers=headers(api),
        json={
            **base,
            "revision_id": base["base_revision"],
            "content_hash": garment["content_hash"],
            "purpose": "aesthetic",
            "decision": "approve",
        },
    )
    assert approval.status_code == 201, approval.text
    handoff = client.post(route + "/handoff", headers=headers(api), json=base)
    assert handoff.status_code == 201, handoff.text
    for name, stretch, available in [
        ("Available twill", 12, True),
        ("Unavailable silk", 3, False),
        ("Unmeasured crepe", None, True),
    ]:
        response = client.post(
            route + "/materials/offers",
            headers=headers(api),
            json={
                **base,
                "name": name,
                "stretch_percent": stretch,
                "available": available,
                "currency": "INR",
                "price_per_metre": "800.00",
                "evidence": "Synthetic supplier note",
            },
        )
        assert response.status_code == 201, response.text
    comparison = client.post(
        route + "/materials/compare",
        headers=headers(api),
        json={
            **base,
            "length_metres": "3.00",
            "waste_percent": 10,
            "trim_cost": "200.00",
            "other_cost": "100.00",
            "currency": "INR",
            "minimum_stretch_percent": 8,
        },
    )
    assert comparison.status_code == 200, comparison.text
    offers = {item["compatibility"]: item for item in comparison.json()["offers"]}
    assert set(offers) == {"compatible", "incompatible", "unknown"}
    assert offers["compatible"]["total"] == "2940.00"
    for status in ("incompatible", "compatible"):
        proposal = client.post(
            route + "/patch-proposals",
            headers=headers(api),
            json={
                **base,
                "operations": [
                    {
                        "op": "update",
                        "target_component_id": "garment",
                        "payload": {"material_id": offers[status]["id"]},
                    }
                ],
                "justification": "Review material change",
            },
        )
        assert proposal.status_code == 201, proposal.text
        response = client.post(
            route + f"/patch-proposals/{proposal.json()['id']}/accept",
            headers=headers(api),
            json=base,
        )
        assert response.status_code == (422 if status == "incompatible" else 201), response.text
    updated = client.get(route, headers=headers(api)).json()
    assert updated["design"]["material_id"] == offers["compatible"]["id"]
    assert updated["design"]["components"][1]["locked"] is True
    assert updated["approved_revision_id"] == base["base_revision"]
    draft = client.get(route + f"/handoff/{handoff.json()['id']}", headers=headers(api)).json()
    assert draft["current"] is False
    assert draft["status"] == "needs_review"
    assert draft["package"]["revision_id"] == base["base_revision"]


def test_imported_catalog_gates_substitution_and_propagates_impact(api):
    client = api["client"]
    garment = setup_garment(api)
    gid = garment["id"]
    revision = garment["draft_revision_id"]
    route = f"/v1/garments/{gid}"
    base = {"base_revision": revision}
    observed = datetime.now(UTC).date().isoformat()
    columns = (
        "name,evidence,price_per_metre,currency,observed_on,"
        "available,stretch_percent,width_cm,gsm\n"
    )
    catalog = columns + (
        f"Twill,Quote A,800,INR,{observed},true,12,150,200\n"
        f"Crepe,Quote B,600,INR,{observed},true,12,,180\n"
        f"Silk,Quote C,900,INR,{observed},false,12,150,150\n"
    )
    imported = client.post(
        route + "/materials/import", headers=headers(api), json={**base, "csv_text": catalog}
    )
    assert imported.status_code == 201, imported.text
    offers = {offer["name"]: offer for offer in imported.json()["offers"]}
    assert offers["Twill"]["unit"] == "metre"
    assert offers["Twill"]["observed_on"] == observed
    invalid = catalog + f"Invalid,Quote D,wrong,INR,{observed},true,12,100,200\n"
    assert (
        client.post(
            route + "/materials/import", headers=headers(api), json={**base, "csv_text": invalid}
        ).status_code
        == 422
    )
    assert len(client.get(route + "/materials", headers=headers(api)).json()) == 3
    criteria = {
        **base,
        "length_metres": "3",
        "waste_percent": 10,
        "trim_cost": "200",
        "other_cost": "100",
        "currency": "INR",
        "minimum_stretch_percent": 8,
        "minimum_width_cm": 140,
        "maximum_gsm": 220,
    }
    comparison = client.post(
        route + "/materials/compare", headers=headers(api), json=criteria
    ).json()
    assert {offer["name"]: offer["compatibility"] for offer in comparison["offers"]} == {
        "Twill": "compatible",
        "Crepe": "unknown",
        "Silk": "incompatible",
    }
    substitution = route + "/materials/substitutions"
    selection = {**base, "comparison_id": comparison["id"], "offer_id": offers["Twill"]["id"]}
    assert (
        client.post(
            substitution,
            headers=headers(api),
            json={**selection, "offer_id": offers["Crepe"]["id"]},
        ).status_code
        == 422
    )

    bom, notes, unrelated = [str(uuid4()) for _ in range(3)]
    with Session(api["engine"]) as session, session.begin():
        for identifier, kind, dependencies in [
            (bom, "bom", ["material", notes]),
            (notes, "technical_notes", [bom]),
            (unrelated, "sleeve_preview", ["sleeve"]),
        ]:
            session.add(
                Artifact(
                    id=identifier,
                    organization_id=api["organization_id"],
                    garment_id=gid,
                    revision_id=revision,
                    kind=kind,
                    depends_on=dependencies,
                    status="draft",
                    created_by="test",
                )
            )
    staged = client.post(substitution, headers=headers(api), json=selection)
    assert staged.status_code == 201, staged.text
    assert staged.json()["estimated_total"] == "2940.00"
    patch = route + f"/patch-proposals/{staged.json()['id']}"
    preview = client.get(patch + "/preview", headers=headers(api)).json()
    assert {artifact["id"] for artifact in preview["artifact_impact"]} == {bom, notes}

    replacement = client.post(
        route + "/materials/offers",
        headers=headers(api),
        json={
            **base,
            "name": "Twill updated",
            "price_per_metre": "820",
            "currency": "INR",
            "evidence": "Quote A2",
            "available": True,
            "stretch_percent": 12,
            "width_cm": 150,
            "gsm": 200,
            "supersedes_offer_id": offers["Twill"]["id"],
        },
    )
    assert replacement.status_code == 201, replacement.text
    assert client.post(patch + "/accept", headers=headers(api), json=base).status_code == 422
    refreshed = client.post(
        route + "/materials/compare", headers=headers(api), json=criteria
    ).json()
    staged = client.post(
        substitution,
        headers=headers(api),
        json={**selection, "comparison_id": refreshed["id"], "offer_id": replacement.json()["id"]},
    )
    committed = client.post(
        route + f"/patch-proposals/{staged.json()['id']}/accept", headers=headers(api), json=base
    )
    assert committed.status_code == 201, committed.text
    assert set(committed.json()["invalidated_artifacts"]) == {bom, notes}
    change = committed.json()
    new_base = {"base_revision": change["new_revision"]}
    approved = client.post(
        route + "/approvals",
        headers=headers(api),
        json={
            **new_base,
            "revision_id": change["new_revision"],
            "content_hash": change["content_hash"],
            "purpose": "aesthetic",
            "decision": "approve",
        },
    )
    assert approved.status_code == 201, approved.text
    handoff = client.post(route + "/handoff", headers=headers(api), json=new_base)
    assert handoff.status_code == 201, handoff.text
    package = client.get(route + f"/handoff/{handoff.json()['id']}", headers=headers(api)).json()[
        "package"
    ]
    assert package["material_estimate"]["comparison_id"] == refreshed["id"]
    assert package["material_estimate"]["total"] == "3006.00"
