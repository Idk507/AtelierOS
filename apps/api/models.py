"""PostgreSQL records; immutable snapshots and tenant-scoped composite keys."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    """Generate an opaque production identifier."""
    return str(uuid4())


class Base(DeclarativeBase):
    """Migration metadata root."""


class Record:
    """Shared identity and creation provenance."""

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(200))


class Organization(Record, Base):
    """Top-level tenant; provisioning is an operator action."""

    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))


class User(Record, Base):
    """Issuer-qualified subject; emails and measurements are not required."""

    __tablename__ = "users"
    subject: Mapped[str] = mapped_column(String(200), unique=True)


class Scoped(Record):
    """Every tenant-owned row has an explicit organization FK."""

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)


class Membership(Scoped, Base):
    """Roles are database grants, never trusted token role claims."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    roles: Mapped[list[str]] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Project(Scoped, Base):
    """A tenant's design workspace."""

    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("organization_id", "id"),)
    name: Mapped[str] = mapped_column(String(200))


class ProjectGrant(Scoped, Base):
    """Explicit project membership for all roles, including organization admins."""

    __tablename__ = "project_grants"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "project_id"], ["projects.organization_id", "projects.id"]
        ),
        UniqueConstraint("organization_id", "project_id", "user_id"),
    )
    project_id: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class Garment(Scoped, Base):
    """Mutable head pointers to immutable, organization-bound revisions."""

    __tablename__ = "garments"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "project_id"], ["projects.organization_id", "projects.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "id", "draft_revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
            name="fk_draft_head",
            use_alter=True,
        ),
        ForeignKeyConstraint(
            ["organization_id", "id", "approved_revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
            name="fk_approved_head",
            use_alter=True,
        ),
    )
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    draft_revision_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_revision_id: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Revision(Scoped, Base):
    """Canonical payload protected by database immutability triggers."""

    __tablename__ = "revisions"
    __table_args__ = (
        UniqueConstraint("organization_id", "garment_id", "id"),
        ForeignKeyConstraint(
            ["organization_id", "garment_id"], ["garments.organization_id", "garments.id"]
        ),
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "parent_revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )
    garment_id: Mapped[str] = mapped_column(String(100), index=True)
    parent_revision_id: Mapped[str | None] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content_hash: Mapped[str] = mapped_column(String(64))


class Proposal(Scoped, Base):
    """Immutable proposed operations with separately tracked acceptance state."""

    __tablename__ = "proposals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "base_revision"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )
    garment_id: Mapped[str] = mapped_column(String(100), index=True)
    base_revision: Mapped[str] = mapped_column(String(100))
    operations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    justification: Mapped[str] = mapped_column(String(2000))
    preview_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="proposed")


class UnlockRequest(Scoped, Base):
    """A distinct human decision for a precise revision's component lock."""

    __tablename__ = "unlock_requests"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "base_revision"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )
    garment_id: Mapped[str] = mapped_column(String(100))
    base_revision: Mapped[str] = mapped_column(String(100))
    component_id: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(30), default="pending")


class Approval(Scoped, Base):
    """Append-only purpose-specific human decisions."""

    __tablename__ = "approvals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )
    garment_id: Mapped[str] = mapped_column(String(100), index=True)
    revision_id: Mapped[str] = mapped_column(String(100))
    content_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(30))
    decision: Mapped[str] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(30))


class Artifact(Scoped, Base):
    """Dependency metadata only; generation belongs to later phases."""

    __tablename__ = "artifacts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "garment_id", "revision_id"],
            ["revisions.organization_id", "revisions.garment_id", "revisions.id"],
        ),
    )
    garment_id: Mapped[str] = mapped_column(String(100))
    revision_id: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(50))
    depends_on: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    review_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


class Audit(Scoped, Base):
    """Append-only business events, containing IDs and digests, not raw assets."""

    __tablename__ = "audit_events"
    aggregate_id: Mapped[str] = mapped_column(String(100), index=True)
    revision_id: Mapped[str | None] = mapped_column(String(100))
    event_type: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Idempotency(Scoped, Base):
    """Original command responses committed with their business effects."""

    __tablename__ = "idempotency"
    __table_args__ = (UniqueConstraint("organization_id", "actor_id", "key"),)
    actor_id: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Outbox(Scoped, Base):
    """At-least-once event delivery intent; payload stays unchanged on retries."""

    __tablename__ = "outbox"
    __table_args__ = (UniqueConstraint("organization_id", "id"),)
    envelope: Mapped[dict[str, Any]] = mapped_column(JSONB)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Receipt(Scoped, Base):
    """Consumer deduplication committed with an internal transactional effect."""

    __tablename__ = "event_receipts"
    __table_args__ = (
        UniqueConstraint("organization_id", "consumer", "event_id"),
        ForeignKeyConstraint(
            ["organization_id", "event_id"], ["outbox.organization_id", "outbox.id"]
        ),
    )
    consumer: Mapped[str] = mapped_column(String(100))
    event_id: Mapped[str] = mapped_column(String(100))


class ToolAttempt(Scoped, Base):
    """Durable side-effect admission; unknown outcomes require reconciliation."""

    __tablename__ = "tool_attempts"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key"),)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="pending")
