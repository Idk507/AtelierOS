"""Revision-bound sample findings, measurements and patternmaker resolutions."""

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import Field, model_validator
from sqlalchemy import select

from apps.api.dto import RevisionCommand
from apps.api.main import Key, Svc
from apps.api.models import Base, new_id
from apps.api.research import ResearchRecord, revision_reference
from apps.api.research_images import thumbnail
from packages.domain.design import DomainError, Identifier, StrictModel

router = APIRouter(prefix="/v1/garments/{gid}/samples", tags=["samples"])


class SampleFeedback(ResearchRecord, Base):
    __tablename__ = "sample_feedback"
    __table_args__ = revision_reference()


class Measurement(StrictModel):
    label: str = Field(min_length=1, max_length=100)
    value: str = Field(pattern=r"^(0|[1-9][0-9]{0,5})(\.[0-9]{1,3})?$")
    unit: Literal["mm", "cm", "in"]
    source: str = Field(min_length=1, max_length=300)


class Annotation(StrictModel):
    x: int = Field(ge=0, le=1000)
    y: int = Field(ge=0, le=1000)


class Finding(RevisionCommand):
    sample_label: str = Field(min_length=1, max_length=100)
    component_id: Identifier | None = None
    observation: str = Field(min_length=1, max_length=1000)
    severity: Literal["note", "blocking"]
    measurement: Measurement | None = None
    photo_jpeg: str | None = Field(default=None, min_length=1, max_length=342_000)
    annotation: Annotation | None = None
    photo_rights_confirmed: bool = False

    @model_validator(mode="after")
    def check_evidence(self) -> "Finding":
        if self.measurement is not None and Decimal(self.measurement.value) <= 0:
            raise ValueError("Measurement must be positive")
        if self.photo_jpeg is not None and not self.photo_rights_confirmed:
            raise ValueError("Confirm photo reuse rights")
        if self.annotation is not None and self.photo_jpeg is None:
            raise ValueError("Annotation requires a photo")
        return self


class ResolveFinding(RevisionCommand):
    resolution: str = Field(min_length=1, max_length=1000)


def sample_snapshot(svc: Svc, gid: str, revision_id: str) -> list[dict[str, Any]]:
    rows = list(
        svc.session.scalars(
            select(SampleFeedback)
            .filter_by(organization_id=svc.organization_id, garment_id=gid, revision_id=revision_id)
            .order_by(SampleFeedback.created_at, SampleFeedback.id)
        )
    )
    resolutions = {
        row.payload["finding_id"]: row for row in rows if row.payload["kind"] == "resolution"
    }
    results = []
    for row in rows:
        if row.payload["kind"] != "finding":
            continue
        resolution = resolutions.get(row.id)
        results.append(
            {
                "id": row.id,
                **row.payload,
                "recorded_by": row.created_by,
                "recorded_at": row.created_at.isoformat(),
                "resolution": {
                    "id": resolution.id,
                    "note": resolution.payload["note"],
                    "by": resolution.created_by,
                    "at": resolution.created_at.isoformat(),
                }
                if resolution
                else None,
            }
        )
    return results


@router.get("")
def list_findings(gid: str, svc: Svc) -> list[dict[str, Any]]:
    garment = svc.garment(gid)
    return sample_snapshot(svc, gid, svc.revision(garment).id)


@router.get("/capabilities")
def capabilities(gid: str, svc: Svc) -> dict[str, bool]:
    """Expose scoped UI permissions without replacing write authorization."""
    svc.garment(gid)
    human = svc.identity.principal_type == "human"
    return {
        "can_record": human and bool(svc.roles & {"designer", "patternmaker", "production"}),
        "can_resolve": human and "patternmaker" in svc.roles,
    }


@router.post("", status_code=201)
def add_finding(gid: str, body: Finding, svc: Svc, key: Key) -> dict[str, str]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker", "production")

    def write() -> dict[str, str]:
        svc.check_head(garment, body.base_revision)
        revision = svc.revision(garment)
        if body.component_id and not any(
            component["id"] == body.component_id for component in revision.payload["components"]
        ):
            raise DomainError("unknown_component", 422)
        if len(sample_snapshot(svc, gid, revision.id)) >= 30:
            raise DomainError("sample_feedback_limit", 422)
        payload = {
            **body.model_dump(exclude={"base_revision", "photo_jpeg"}),
            "kind": "finding",
            "thumbnail_jpeg": thumbnail(body.photo_jpeg) if body.photo_jpeg else None,
        }
        row = SampleFeedback(
            id=new_id(),
            organization_id=svc.organization_id,
            garment_id=gid,
            revision_id=revision.id,
            created_by=svc.actor,
            payload=payload,
        )
        svc.session.add(row)
        svc.event("sample.finding_recorded", gid, revision.id, {"finding_id": row.id})
        return {"id": row.id}

    return svc.write(key, f"/v1/garments/{gid}/samples", body.model_dump(), write)


@router.post("/{finding_id}/resolve")
def resolve_finding(
    gid: str, finding_id: str, body: ResolveFinding, svc: Svc, key: Key
) -> dict[str, str]:
    garment = svc.garment(gid)
    svc.permit("patternmaker")

    def write() -> dict[str, str]:
        svc.check_head(garment, body.base_revision)
        finding = next(
            (
                row
                for row in sample_snapshot(svc, gid, body.base_revision)
                if row["id"] == finding_id
            ),
            None,
        )
        if finding is None:
            raise DomainError("not_found", 404)
        if finding["resolution"] is not None:
            raise DomainError("finding_already_resolved")
        row = SampleFeedback(
            id=new_id(),
            organization_id=svc.organization_id,
            garment_id=gid,
            revision_id=body.base_revision,
            created_by=svc.actor,
            payload={"kind": "resolution", "finding_id": finding_id, "note": body.resolution},
        )
        svc.session.add(row)
        svc.event("sample.finding_resolved", gid, body.base_revision, {"finding_id": finding_id})
        return {"id": row.id}

    return svc.write(
        key, f"/v1/garments/{gid}/samples/{finding_id}/resolve", body.model_dump(), write
    )
