"""Build citation-linked briefs from designer-supplied, reusable text snapshots."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from pydantic import Field, field_validator
from sqlalchemy import ForeignKeyConstraint, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api import web_research
from apps.api.config import Settings
from apps.api.dto import RevisionCommand
from apps.api.main import Key, Svc
from apps.api.models import Base, Scoped, new_id
from apps.api.research_images import thumbnail
from packages.domain.design import DomainError, Identifier, content_hash

router = APIRouter(prefix="/v1/garments/{gid}/research", tags=["research"])


class ResearchRecord(Scoped):
    """Immutable evidence bound to the garment and revision that captured it."""

    garment_id: Mapped[str] = mapped_column(String(100))
    revision_id: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


def revision_reference() -> tuple[ForeignKeyConstraint]:
    return (
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )


class ResearchSource(ResearchRecord, Base):
    __tablename__ = "research_sources"
    __table_args__ = revision_reference()


class ResearchBrief(ResearchRecord, Base):
    __tablename__ = "research_briefs"
    __table_args__ = revision_reference()


class SourceCreate(RevisionCommand):
    title: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(min_length=1, max_length=4000)
    url: str | None = Field(default=None, max_length=2048)
    rights: Literal["owned", "licensed", "reference_only"]

    @field_validator("url")
    @classmethod
    def citation_link(cls, value: str | None) -> str | None:
        """Citation URLs are labels only. The service never fetches them."""
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or "\\" in value
            or any(ord(char) <= 32 for char in value)
        ):
            raise ValueError("Use a public HTTPS citation URL")
        return value


class BriefCreate(RevisionCommand):
    question: str = Field(min_length=1, max_length=500)
    source_ids: list[Identifier] = Field(min_length=1, max_length=12)


class SearchCreate(RevisionCommand):
    query: str = Field(min_length=1, max_length=300)
    geography: str = Field(default="", max_length=80)
    period: Literal["week", "month", "year"] | None = None
    limit: int = Field(default=5, ge=1, le=8)


class CaptureCreate(RevisionCommand):
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)


class ImageCreate(RevisionCommand):
    title: str = Field(min_length=1, max_length=200)
    caption: str = Field(min_length=1, max_length=500)
    rights: Literal["owned", "licensed"]
    image_base64: str = Field(min_length=1, max_length=342_000)


@router.post("/images", status_code=201)
def add_image(gid: str, body: ImageCreate, key: Key, svc: Svc) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        payload = {
            "title": body.title,
            "url": None,
            "excerpt": body.caption,
            "rights": body.rights,
            "source_kind": "studio_image",
            "thumbnail_jpeg": thumbnail(body.image_base64),
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        payload["digest"] = content_hash(payload)
        identifier = new_id()
        svc.session.add(
            ResearchSource(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                created_by=svc.actor,
                payload=payload,
            )
        )
        svc.event("research.image_captured", gid, body.base_revision, {"source_id": identifier})
        return {"id": identifier, "digest": payload["digest"]}

    return svc.write(key, f"/v1/garments/{gid}/research/images", body.model_dump(), write)


@router.get("/capabilities")
def research_capabilities(gid: str, svc: Svc, request: Request) -> dict[str, bool]:
    svc.garment(gid)
    settings: Settings = request.app.state.settings
    return {
        "search": settings.research_live_enabled and bool(settings.tavily_api_key),
        "capture": settings.research_live_enabled and bool(settings.research_source_hosts),
    }


@router.post("/search")
def find_sources(
    gid: str, body: SearchCreate, key: Key, svc: Svc, request: Request
) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")
    settings: Settings = request.app.state.settings
    secret = settings.tavily_api_key
    if not settings.research_live_enabled or not secret:
        raise DomainError("research_search_disabled", 503)

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        query = f"{body.query} ({body.geography})" if body.geography else body.query
        hits = web_research.search(query, body.limit, body.period, secret.get_secret_value())
        svc.event("research.search_completed", gid, body.base_revision, {"result_count": len(hits)})
        return {"results": [hit.model_dump() for hit in hits]}

    return svc.write(key, f"/v1/garments/{gid}/research/search", body.model_dump(), write)


@router.post("/capture", status_code=201)
def capture_source(
    gid: str, body: CaptureCreate, key: Key, svc: Svc, request: Request
) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")
    settings: Settings = request.app.state.settings
    if not settings.research_live_enabled or not settings.research_source_hosts:
        raise DomainError("research_capture_disabled", 503)

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        excerpt = web_research.capture(body.url, settings.research_source_hosts)
        payload = {
            "title": body.title,
            "url": body.url,
            "excerpt": excerpt,
            "rights": "reference_only",
            "source_kind": "web_snapshot",
            "retrieved_at": datetime.now(UTC).isoformat(),
        }
        payload["digest"] = content_hash(payload)
        identifier = new_id()
        svc.session.add(
            ResearchSource(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                created_by=svc.actor,
                payload=payload,
            )
        )
        svc.event("research.source_captured", gid, body.base_revision, {"source_id": identifier})
        return {"id": identifier, **payload}

    return svc.write(key, f"/v1/garments/{gid}/research/capture", body.model_dump(), write)


@router.get("")
def research_board(gid: str, svc: Svc) -> dict[str, Any]:
    """Load the workspace board, including links to earlier revisions."""
    svc.garment(gid)
    scope = {"organization_id": svc.organization_id, "garment_id": gid}
    sources = svc.session.scalars(
        select(ResearchSource)
        .filter_by(**scope)
        .order_by(ResearchSource.created_at.desc())
        .limit(50)
    )
    briefs = svc.session.scalars(
        select(ResearchBrief).filter_by(**scope).order_by(ResearchBrief.created_at.desc()).limit(20)
    )
    return {
        "sources": [{"id": s.id, "revision_id": s.revision_id, **s.payload} for s in sources],
        "briefs": [{"id": b.id, "revision_id": b.revision_id, **b.payload} for b in briefs],
    }


@router.post("/sources", status_code=201)
def add_source(gid: str, body: SourceCreate, key: Key, svc: Svc) -> dict[str, Any]:
    """Capture a text snapshot with a rights declaration and provenance digest."""
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        payload = body.model_dump(exclude={"base_revision"})
        payload["source_kind"] = "designer_supplied"
        payload["digest"] = content_hash(payload)
        identifier = new_id()
        svc.session.add(
            ResearchSource(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                created_by=svc.actor,
                payload=payload,
            )
        )
        svc.event("research.source_captured", gid, body.base_revision, {"source_id": identifier})
        return {"id": identifier, **payload}

    return svc.write(key, f"/v1/garments/{gid}/research/sources", body.model_dump(), write)


@router.post("/briefs", status_code=201)
def create_brief(gid: str, body: BriefCreate, key: Key, svc: Svc) -> dict[str, Any]:
    """Rank licensed excerpts deterministically. Input text has no execution path."""
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        sources = list(
            svc.session.scalars(
                select(ResearchSource).where(
                    ResearchSource.organization_id == svc.organization_id,
                    ResearchSource.garment_id == gid,
                    ResearchSource.id.in_(body.source_ids),
                )
            )
        )
        if len(sources) != len(set(body.source_ids)):
            raise DomainError("not_found", 404)
        if any(s.payload["rights"] == "reference_only" for s in sources):
            raise DomainError("source_reuse_forbidden", 422)
        terms = set(re.findall(r"\w+", body.question.casefold()))
        cards = []
        for source in sources:
            excerpt = source.payload["excerpt"]
            cards.append(
                {
                    "source_id": source.id,
                    "source_digest": source.payload["digest"],
                    "title": source.payload["title"],
                    "excerpt": excerpt,
                    "relevance": len(terms.intersection(re.findall(r"\w+", excerpt.casefold()))),
                }
            )
        cards.sort(key=lambda card: (-card["relevance"], card["source_id"]))
        payload = {"question": body.question, "cards": cards, "method": "local_excerpt_ranking"}
        identifier = new_id()
        svc.session.add(
            ResearchBrief(
                id=identifier,
                organization_id=svc.organization_id,
                garment_id=gid,
                revision_id=body.base_revision,
                created_by=svc.actor,
                payload=payload,
            )
        )
        svc.event("research.brief_created", gid, body.base_revision, {"brief_id": identifier})
        return {"id": identifier, **payload}

    return svc.write(key, f"/v1/garments/{gid}/research/briefs", body.model_dump(), write)
