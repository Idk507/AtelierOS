"""Strict HTTP commands; actors, roles and organization are never write fields."""

from typing import Literal

from pydantic import Field

from packages.domain.design import Design, Identifier, Patch, StrictModel


class ProjectCreate(StrictModel):
    """A project created in the authenticated organization."""

    name: str = Field(min_length=1, max_length=200)


class GarmentCreate(ProjectCreate):
    """A garment's initial, explicitly unapproved snapshot."""

    design: Design


class RevisionCommand(StrictModel):
    """Compare-and-swap precondition on every garment mutation."""

    base_revision: Identifier


class ProposalCreate(RevisionCommand):
    """An editable proposal, not approval or canonical state."""

    operations: list[Patch] = Field(min_length=1, max_length=100)
    justification: str = Field(min_length=1, max_length=2000)


class ApprovalCreate(RevisionCommand):
    """A human's decision binds an exact revision hash and purpose."""

    revision_id: Identifier
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    purpose: Literal["aesthetic", "technical", "handoff"]
    decision: Literal["approve", "reject"]


class UnlockCreate(RevisionCommand):
    """Request an unlock separately from any proposed geometry change."""

    component_id: Identifier
    reason: str = Field(min_length=1, max_length=2000)


class UnlockDecision(RevisionCommand):
    """An administrator's decision cannot approve the garment."""

    decision: Literal["grant", "reject"]


class ConstraintCreate(RevisionCommand):
    """Adding a hard lock is allowed; removing it uses separate unlock authorization."""

    component_id: Identifier
    kind: Literal["hard_lock"]
