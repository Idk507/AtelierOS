"""Revision-bound technical handoff drafts with explicit review status."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select

from apps.api.dto import RevisionCommand
from apps.api.main import Key, Svc
from apps.api.materials import MaterialOffer, revision_estimate
from apps.api.models import Approval, Artifact, Audit, Garment, new_id
from apps.api.samples import sample_snapshot
from packages.domain.design import DomainError, content_hash

router = APIRouter(prefix="/v1/garments/{gid}/handoff", tags=["handoff"])


class Release(RevisionCommand):
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def release_prerequisites(svc: Svc, garment: Garment, record: Artifact) -> dict[str, str]:
    """Require a current evidence snapshot and professional review of that evidence."""
    if (
        record.revision_id != garment.draft_revision_id
        or record.revision_id != garment.approved_revision_id
    ):
        raise DomainError("stale_handoff")
    current = sample_snapshot(svc, garment.id, record.revision_id)
    if record.review_payload is None or record.review_payload["samples"] != current:
        raise DomainError("sample_snapshot_changed")
    if any(row["severity"] == "blocking" and row["resolution"] is None for row in current):
        raise DomainError("open_sample_findings")
    if not any(row["measurement"] is not None for row in current):
        raise DomainError("measurement_evidence_required")
    revision = svc.revision(garment)
    decisions = {}
    for purpose in ("aesthetic", "technical"):
        decision = svc.session.scalar(
            select(Approval)
            .filter_by(
                organization_id=svc.organization_id,
                garment_id=garment.id,
                revision_id=record.revision_id,
                content_hash=revision.content_hash,
                purpose=purpose,
            )
            .order_by(Approval.created_at.desc(), Approval.id.desc())
            .limit(1)
        )
        if decision is None or decision.decision != "approve":
            raise DomainError(f"{purpose}_approval_required")
        if purpose == "technical":
            review = svc.session.scalar(
                select(Audit)
                .filter_by(
                    organization_id=svc.organization_id,
                    aggregate_id=garment.id,
                    revision_id=record.revision_id,
                    event_type="approval.decided",
                )
                .where(Audit.detail["approval_id"].astext == decision.id)
            )
            if review is None or review.detail.get("sample_digest") != content_hash(
                {"samples": current}
            ):
                raise DomainError("technical_approval_required")
            evidence_times = [
                datetime.fromisoformat(
                    row["resolution"]["at"] if row["resolution"] else row["recorded_at"]
                )
                for row in current
            ]
            if any(value > decision.created_at for value in evidence_times):
                raise DomainError("technical_approval_required")
            decisions["technical_reviewer"] = decision.created_by
        decisions[f"{purpose}_approval_id"] = decision.id
    # A revision approval and one measurement cannot establish a complete tech pack.
    # Keep production release closed until an explicit package-bound professional
    # completeness assessment has a reviewed contract and persistence model.
    raise DomainError("professional_completeness_assessment_required", 409)


@router.get("")
def list_drafts(gid: str, svc: Svc) -> list[dict[str, Any]]:
    """Return draft metadata and disclose whether each revision is current."""
    garment = svc.garment(gid)
    records = svc.session.scalars(
        select(Artifact)
        .filter_by(organization_id=svc.organization_id, garment_id=gid, kind="technical_draft")
        .order_by(Artifact.created_at.desc())
        .limit(25)
    )
    return [
        {
            "id": record.id,
            "revision_id": record.revision_id,
            "status": record.status,
            "current": record.revision_id == garment.draft_revision_id,
        }
        for record in records
    ]


@router.post("", status_code=201)
def create_draft(gid: str, body: RevisionCommand, svc: Svc, key: Key) -> dict[str, Any]:
    """Capture a review draft from the current aesthetically approved revision."""
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker", "production")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        if garment.approved_revision_id != body.base_revision:
            raise DomainError("aesthetic_approval_required", 409)
        identifier = new_id()
        svc.session.add(
            Artifact(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                kind="technical_draft",
                depends_on=["*"],
                status="draft",
                created_by=svc.actor,
                review_payload={"samples": sample_snapshot(svc, gid, body.base_revision)},
            )
        )
        svc.event("spec.draft_created", gid, body.base_revision, {"artifact_id": identifier})
        return {"id": identifier, "revision_id": body.base_revision, "status": "draft"}

    return svc.write(key, f"/v1/garments/{gid}/handoff", body.model_dump(), write)


@router.get("/{draft_id}")
def export_draft(gid: str, draft_id: str, svc: Svc) -> dict[str, Any]:
    """Produce a portable JSON package, with old revisions visibly marked stale."""
    garment = svc.garment(gid)
    record = get_draft(svc, gid, draft_id)
    package = draft_package(svc, garment, record)
    digest = content_hash(package)
    current = record.revision_id == garment.draft_revision_id
    release = svc.session.scalar(
        select(Audit)
        .filter_by(
            organization_id=svc.organization_id,
            aggregate_id=gid,
            revision_id=record.revision_id,
            event_type="handoff.released",
        )
        .where(Audit.detail["draft_id"].astext == record.id)
        .order_by(Audit.created_at.desc())
        .limit(1)
    )
    active_release = None
    if release is not None and current and release.detail["digest"] == digest:
        try:
            if release_prerequisites(svc, garment, record) == release.detail["prerequisites"]:
                active_release = {
                    "approval_id": release.detail["approval_id"],
                    "by": release.created_by,
                    "at": release.created_at.isoformat(),
                }
        except DomainError:
            pass
    evidence_current = record.review_payload is None or record.review_payload[
        "samples"
    ] == sample_snapshot(svc, gid, record.revision_id)
    return {
        "package": package,
        "digest": digest,
        "current": current,
        "release": active_release,
        "status": "released"
        if active_release
        else record.status
        if current and evidence_current and release is None
        else "needs_review",
    }


@router.get("/{draft_id}/pdf")
def export_pdf(gid: str, draft_id: str, svc: Svc) -> Response:
    """Return a private, revision-bound PDF review draft."""
    from apps.api.handoff_pdf import render_handoff_pdf

    result = export_draft(gid, draft_id, svc)
    pdf = render_handoff_pdf(result, svc.organization_id, draft_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="atelier-handoff.pdf"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{draft_id}/docx")
def export_docx(gid: str, draft_id: str, svc: Svc) -> Response:
    """Return an editable Word document for the frozen review snapshot."""
    from apps.api.handoff_docx import render_handoff_docx

    result = export_draft(gid, draft_id, svc)
    return Response(
        content=render_handoff_docx(result, svc.organization_id, draft_id),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="atelier-handoff.docx"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def get_draft(svc: Svc, gid: str, draft_id: str) -> Artifact:
    record = svc.session.scalar(
        select(Artifact).filter_by(
            id=draft_id, organization_id=svc.organization_id, garment_id=gid, kind="technical_draft"
        )
    )
    if record is None:
        raise DomainError("not_found", 404)
    return record


def draft_package(svc: Svc, garment: Garment, record: Artifact) -> dict[str, Any]:
    gid = garment.id
    revision = svc.revision(garment, record.revision_id)
    material_id = revision.payload.get("material_id")
    offer = (
        svc.session.scalar(
            select(MaterialOffer).filter_by(
                id=material_id, organization_id=svc.organization_id, garment_id=gid
            )
        )
        if material_id
        else None
    )
    package = {
        "schema_version": 1,
        "kind": "technical_review_draft",
        "garment_id": gid,
        "revision_id": revision.id,
        "revision_digest": revision.content_hash,
        "design": revision.payload,
        "component_inventory": [
            {
                "component_id": component["id"],
                "kind": component["kind"],
                "parent_id": component.get("parent_id"),
                "locked": component.get("locked", False),
                "view": component.get("view"),
            }
            for component in revision.payload["components"]
        ],
        "material_offer": offer.payload if offer else None,
        "measurements": None,
        "patternmaker_review_required": True,
    }
    estimate = revision_estimate(svc, gid, revision.id)
    if estimate is not None:
        package["material_estimate"] = estimate
    if record.review_payload is not None:
        samples = record.review_payload["samples"]
        package["sample_feedback"] = samples
        package["measurements"] = [
            {**item["measurement"], "finding_id": item["id"], "recorded_by": item["recorded_by"]}
            for item in samples
            if item["measurement"] is not None
        ]
        package["bill_of_materials"] = (
            [
                {
                    "name": offer.payload["name"],
                    "offer_id": offer.id,
                    "length_metres": estimate["criteria"]["length_metres"] if estimate else None,
                    "evidence": offer.payload["evidence"],
                }
            ]
            if offer
            else []
        )
    else:
        package["bill_of_materials"] = []
    package["open_questions"] = [
        {
            "code": "view_attribution_missing",
            "question": "Which components belong to front and back views?",
            "status": "open",
        },
        {
            "code": "measurement_completeness_unassessed",
            "question": "Which points of measure and tolerances are required?",
            "status": "professional_review_required",
        },
        {
            "code": "bill_of_materials_incomplete",
            "question": "Are all materials, quantities and trims represented?",
            "status": "open",
        },
    ]
    if not offer:
        package["open_questions"].append(
            {
                "code": "material_unknown",
                "question": "Which material offer and evidence apply?",
                "status": "open",
            }
        )
    if offer and package.get("bill_of_materials"):
        package["bill_of_materials"][0]["quantity_status"] = (
            "known" if estimate else "unknown"
        )
    if not package["measurements"]:
        package["open_questions"].append(
            {
                "code": "measurements_missing",
                "question": "No sample measurements have been recorded.",
                "status": "open",
            }
        )
    return package


@router.post("/{draft_id}/release", status_code=201)
def release_draft(gid: str, draft_id: str, body: Release, svc: Svc, key: Key) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("production")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        record = get_draft(svc, gid, draft_id)
        expected = content_hash(draft_package(svc, garment, record))
        if body.digest != expected:
            raise DomainError("handoff_digest_mismatch")
        prerequisites = release_prerequisites(svc, garment, record)
        if prerequisites["technical_reviewer"] == svc.actor:
            raise DomainError("independent_release_required", 403)
        existing = export_draft(gid, draft_id, svc)["release"]
        if existing is not None:
            raise DomainError("handoff_already_released")
        approval = Approval(
            id=new_id(),
            organization_id=svc.organization_id,
            garment_id=gid,
            revision_id=record.revision_id,
            content_hash=svc.revision(garment).content_hash,
            purpose="handoff",
            decision="approve",
            role="production",
            created_by=svc.actor,
        )
        svc.session.add(approval)
        svc.event(
            "handoff.released",
            gid,
            record.revision_id,
            {
                "draft_id": record.id,
                "digest": expected,
                "approval_id": approval.id,
                "prerequisites": prerequisites,
            },
        )
        return {
            "approval_id": approval.id,
            "draft_id": record.id,
            "digest": expected,
            "status": "released",
        }

    return svc.write(
        key, f"/v1/garments/{gid}/handoff/{draft_id}/release", body.model_dump(), write
    )


@router.get("/{draft_id}/html")
def export_html(gid: str, draft_id: str, svc: Svc) -> Response:
    """Download an editable HTML snapshot through the same scoped export contract."""
    from apps.api.handoff_html import render_handoff_html

    result = export_draft(gid, draft_id, svc)
    return Response(
        content=render_handoff_html(result, svc.organization_id, draft_id),
        media_type="text/html",
        headers={
            "Content-Disposition": 'attachment; filename="atelier-handoff.html"',
            "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )
