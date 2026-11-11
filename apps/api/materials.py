"""Compare studio-supplied offers using evidence and exact decimal arithmetic."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter
from pydantic import Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.dto import RevisionCommand
from apps.api.main import Key, Svc
from apps.api.models import Audit, Base, new_id
from apps.api.research import ResearchRecord, revision_reference
from packages.domain.design import DomainError, Identifier, Patch

router = APIRouter(prefix="/v1/garments/{gid}/materials", tags=["materials"])
Money = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,7})(\.[0-9]{1,4})?$")]


class MaterialOffer(ResearchRecord, Base):
    """A scoped, immutable record of an attested offer."""

    __tablename__ = "material_offers"
    __table_args__ = revision_reference()


class MaterialComparison(ResearchRecord, Base):
    __tablename__ = "material_comparisons"
    __table_args__ = revision_reference()


class OfferCreate(RevisionCommand):
    name: str = Field(min_length=1, max_length=120)
    evidence: str = Field(min_length=1, max_length=1000)
    price_per_metre: Money
    currency: Literal["INR", "USD", "EUR", "GBP"]
    stretch_percent: int | None = Field(default=None, ge=0, le=300)
    available: bool | None = None
    composition: str | None = Field(default=None, max_length=120)
    width_cm: int | None = Field(default=None, gt=0, le=500)
    gsm: int | None = Field(default=None, gt=0, le=2000)
    observed_on: str | None = None
    supersedes_offer_id: Identifier | None = None


class Compare(RevisionCommand):
    length_metres: Money
    waste_percent: int = Field(ge=0, le=100)
    trim_cost: Money
    other_cost: Money
    currency: Literal["INR", "USD", "EUR", "GBP"]
    minimum_stretch_percent: int = Field(ge=0, le=300)
    minimum_width_cm: int | None = Field(default=None, gt=0, le=500)
    maximum_gsm: int | None = Field(default=None, gt=0, le=2000)


class CatalogImport(RevisionCommand):
    csv_text: str = Field(min_length=1, max_length=60_000)


class Substitution(RevisionCommand):
    comparison_id: Identifier
    offer_id: Identifier


def comparison_link(svc: Svc, gid: str, proposal_id: str) -> str | None:
    link = svc.session.scalar(
        select(Audit)
        .filter_by(
            organization_id=svc.organization_id,
            aggregate_id=gid,
            event_type="material.substitution_proposed",
        )
        .where(Audit.detail["patch_id"].astext == proposal_id)
        .limit(1)
    )
    return str(link.detail["comparison_id"]) if link else None


def revision_estimate(svc: Svc, gid: str, revision: str) -> dict[str, Any] | None:
    link = svc.session.scalar(
        select(Audit)
        .filter_by(
            organization_id=svc.organization_id,
            aggregate_id=gid,
            revision_id=revision,
            event_type="material.substitution_committed",
        )
        .limit(1)
    )
    if link is None:
        return None
    comparison = svc.session.scalar(
        select(MaterialComparison).filter_by(
            organization_id=svc.organization_id, garment_id=gid, id=link.detail["comparison_id"]
        )
    )
    if comparison is None:
        return None
    offer = next(
        (row for row in comparison.payload["offers"] if row["id"] == link.detail["offer_id"]), None
    )
    if offer is None:
        return None
    return {
        "comparison_id": comparison.id,
        "offer_id": offer["id"],
        "total": offer["total"],
        "currency": offer["currency"],
        "criteria": comparison.payload["criteria"],
        "exclusions": comparison.payload["exclusions"],
    }


def superseded(session: Session, organization_id: str, gid: str, offer_id: str) -> bool:
    return (
        session.scalar(
            select(MaterialOffer.id)
            .filter_by(organization_id=organization_id, garment_id=gid)
            .where(MaterialOffer.payload["supersedes_offer_id"].astext == offer_id)
            .limit(1)
        )
        is not None
    )


def eligible_offer(session: Session, organization_id: str, gid: str, offer_id: str) -> None:
    """Reject substituted IDs and unavailable or unconfirmed offers at commit."""
    offer = session.scalar(
        select(MaterialOffer).filter_by(
            id=offer_id, organization_id=organization_id, garment_id=gid
        )
    )
    if (
        offer is None
        or offer.payload["available"] is not True
        or superseded(session, organization_id, gid, offer_id)
    ):
        raise DomainError("material_offer_unavailable", 422)


@router.get("")
def list_offers(gid: str, svc: Svc) -> list[dict[str, Any]]:
    svc.garment(gid)
    rows = svc.session.scalars(
        select(MaterialOffer)
        .filter_by(organization_id=svc.organization_id, garment_id=gid)
        .order_by(MaterialOffer.created_at.desc())
        .limit(50)
    )
    return [{"id": row.id, **row.payload} for row in rows]


def store_offer(gid: str, body: OfferCreate, svc: Svc, source: str) -> dict[str, Any]:
    observed = body.observed_on
    if observed is not None:
        try:
            if (
                date.fromisoformat(observed).isoformat() != observed
                or observed > datetime.now(UTC).date().isoformat()
            ):
                raise ValueError
        except ValueError as exc:
            raise DomainError("invalid_offer_observation_date", 422) from exc
    previous = body.supersedes_offer_id
    if previous:
        existing = svc.session.scalar(
            select(MaterialOffer.id).filter_by(
                id=previous, organization_id=svc.organization_id, garment_id=gid
            )
        )
        if existing is None or superseded(svc.session, svc.organization_id, gid, previous):
            raise DomainError("material_offer_unavailable", 422)
    payload = {
        **body.model_dump(exclude={"base_revision"}),
        "captured_at": datetime.now(UTC).isoformat(),
        "source_kind": source,
        "unit": "metre",
    }
    identifier = new_id()
    svc.session.add(
        MaterialOffer(
            id=identifier,
            organization_id=svc.organization_id,
            garment_id=gid,
            revision_id=body.base_revision,
            created_by=svc.actor,
            payload=payload,
        )
    )
    svc.event("material.offer_recorded", gid, body.base_revision, {"offer_id": identifier})
    return {"id": identifier, **payload}


@router.post("/import", status_code=201)
def import_catalog(gid: str, body: CatalogImport, svc: Svc, key: Key) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "production")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        reader = csv.DictReader(io.StringIO(body.csv_text.removeprefix("\ufeff")), strict=True)
        columns = {
            "name",
            "evidence",
            "price_per_metre",
            "currency",
            "available",
            "stretch_percent",
            "composition",
            "width_cm",
            "gsm",
            "observed_on",
            "supersedes_offer_id",
        }
        required = {"name", "evidence", "price_per_metre", "currency", "observed_on"}
        try:
            fields = reader.fieldnames or []
        except csv.Error as exc:
            raise DomainError("invalid_catalog_columns", 422) from exc
        if len(fields) != len(set(fields)) or not required <= set(fields) <= columns:
            raise DomainError("invalid_catalog_columns", 422)
        rows: list[OfferCreate] = []
        try:
            for raw in reader:
                if len(rows) >= 50 or None in raw or None in raw.values():
                    raise ValueError
                row: dict[str, Any] = {
                    column: value.strip() for column, value in raw.items() if value.strip()
                }
                if not required <= row.keys():
                    raise ValueError
                for name in ("width_cm", "gsm", "stretch_percent"):
                    if name in row:
                        row[name] = int(row[name])
                if "available" in row:
                    row["available"] = {"true": True, "false": False, "unknown": None}[
                        row["available"].lower()
                    ]
                rows.append(
                    OfferCreate.model_validate({**row, "base_revision": body.base_revision})
                )
        except (ValueError, KeyError, csv.Error, ValidationError) as exc:
            raise DomainError("invalid_catalog_row", 422) from exc
        if not rows:
            raise DomainError("empty_catalog", 422)
        offers = [store_offer(gid, row, svc, "studio_catalog_import") for row in rows]
        return {"imported": len(offers), "offers": offers}

    return svc.write(key, f"/v1/garments/{gid}/materials/import", body.model_dump(), write)


@router.post("/offers", status_code=201)
def record_offer(gid: str, body: OfferCreate, svc: Svc, key: Key) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "production")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        return store_offer(gid, body, svc, "studio_attested")

    return svc.write(key, f"/v1/garments/{gid}/materials/offers", body.model_dump(), write)


@router.post("/compare")
def compare(gid: str, body: Compare, svc: Svc, key: Key) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "production", "patternmaker")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        length = Decimal(body.length_metres)
        if length <= 0:
            raise DomainError("invalid_length", 422)
        rows = list_offers(gid, svc)
        retired = {offer.get("supersedes_offer_id") for offer in rows}
        for offer in rows:
            stretch, width, gsm = (
                offer.get(field) for field in ("stretch_percent", "width_cm", "gsm")
            )
            wrong_size = (
                body.minimum_width_cm is not None
                and width is not None
                and width < body.minimum_width_cm
            )
            too_heavy = body.maximum_gsm is not None and gsm is not None and gsm > body.maximum_gsm
            if (
                offer["id"] in retired
                or offer["available"] is False
                or wrong_size
                or too_heavy
                or (stretch is not None and stretch < body.minimum_stretch_percent)
            ):
                status = "incompatible"
            elif (
                offer["available"] is not True
                or stretch is None
                or (body.minimum_width_cm is not None and width is None)
                or (body.maximum_gsm is not None and gsm is None)
            ):
                status = "unknown"
            else:
                status = "compatible"
            total = None
            if offer["currency"] == body.currency:
                amount = (
                    length
                    * (1 + Decimal(body.waste_percent) / 100)
                    * Decimal(offer["price_per_metre"])
                    + Decimal(body.trim_cost)
                    + Decimal(body.other_cost)
                )
                total = str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            offer.update({"compatibility": status, "total": total})
        snapshot = {
            "revision_id": body.base_revision,
            "offers": rows,
            "criteria": body.model_dump(exclude={"base_revision"}),
            "exclusions": ["tax", "shipping", "currency conversion"],
        }
        identifier = new_id()
        svc.session.add(
            MaterialComparison(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                created_by=svc.actor,
                payload=snapshot,
            )
        )
        svc.event(
            "material.comparison_recorded", gid, body.base_revision, {"comparison_id": identifier}
        )
        return {"id": identifier, **snapshot}

    return svc.write(key, f"/v1/garments/{gid}/materials/compare", body.model_dump(), write)


@router.post("/substitutions", status_code=201)
def stage_substitution(gid: str, body: Substitution, svc: Svc, key: Key) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        comparison = svc.session.scalar(
            select(MaterialComparison).filter_by(
                id=body.comparison_id,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
            )
        )
        if comparison is None:
            raise DomainError("material_comparison_not_found", 404)
        candidate = next(
            (offer for offer in comparison.payload["offers"] if offer["id"] == body.offer_id), None
        )
        if (
            candidate is None
            or candidate["compatibility"] != "compatible"
            or candidate["total"] is None
        ):
            raise DomainError("material_comparison_ineligible", 422)
        eligible_offer(svc.session, svc.organization_id, gid, body.offer_id)
        if svc.revision(garment).payload.get("material_id") == body.offer_id:
            raise DomainError("material_already_selected", 422)
        operation = Patch(
            op="update", target_component_id="garment", payload={"material_id": body.offer_id}
        )
        proposal = svc.stage_proposal(
            garment, body.base_revision, [operation], f"Material comparison {comparison.id}"
        )
        svc.event(
            "material.substitution_proposed",
            gid,
            body.base_revision,
            {"comparison_id": comparison.id, "offer_id": body.offer_id, "patch_id": proposal["id"]},
        )
        return {
            **proposal,
            "comparison_id": comparison.id,
            "estimated_total": candidate["total"],
            "currency": candidate["currency"],
            "operations": [operation.model_dump()],
        }

    return svc.write(key, f"/v1/garments/{gid}/materials/substitutions", body.model_dump(), write)
