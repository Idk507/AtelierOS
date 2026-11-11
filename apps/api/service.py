"""Transactional P01 commands; caller owns commit/rollback for each request."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from apps.api import dto
from apps.api.auth import Identity
from apps.api.models import (
    Approval,
    Artifact,
    Audit,
    Garment,
    Idempotency,
    Membership,
    Outbox,
    Project,
    ProjectGrant,
    Proposal,
    Revision,
    UnlockRequest,
    User,
    new_id,
)
from packages.domain.design import Design, DomainError, Patch, apply_patch, content_hash

Result = dict[str, Any]


class Service:
    """Load locked membership and enforce resource scope before replay or mutation."""

    def __init__(self, session: Session, identity: Identity) -> None:
        self.session = session
        self.identity = identity
        self.organization_id = identity.organization_id
        user = session.scalar(select(User).where(User.subject == identity.subject))
        if user is None:
            raise DomainError("not_found", 404)
        membership = session.scalar(
            select(Membership)
            .where(
                Membership.user_id == user.id,
                Membership.organization_id == self.organization_id,
                Membership.active.is_(True),
            )
            .with_for_update(read=True)
        )
        if membership is None:
            raise DomainError("not_found", 404)
        self.actor = user.id
        self.roles = set(membership.roles)

    def permit(self, *roles: str, human: bool = True) -> None:
        """Human-sensitive commands cannot be invoked with service tokens."""
        if not self.roles.intersection(roles) or (
            human and self.identity.principal_type != "human"
        ):
            raise DomainError("forbidden", 403)

    def project(self, project_id: str) -> Project:
        """Require an explicit grant and lock it against concurrent revocation."""
        project = self.session.scalar(
            select(Project).where(
                Project.id == project_id, Project.organization_id == self.organization_id
            )
        )
        grant = self.session.scalar(
            select(ProjectGrant)
            .where(
                ProjectGrant.project_id == project_id,
                ProjectGrant.organization_id == self.organization_id,
                ProjectGrant.user_id == self.actor,
            )
            .with_for_update(read=True)
        )
        if project is None or grant is None:
            raise DomainError("not_found", 404)
        return project

    def garment(self, garment_id: str) -> Garment:
        """Serialize decisions on one aggregate, refreshing after lock acquisition."""
        garment = self.session.scalar(
            select(Garment).where(
                Garment.id == garment_id, Garment.organization_id == self.organization_id
            )
        )
        if garment is None:
            raise DomainError("not_found", 404)
        self.project(garment.project_id)
        locked = self.session.scalar(
            select(Garment)
            .where(
                Garment.id == garment_id,
                Garment.organization_id == self.organization_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked is None:
            raise DomainError("not_found", 404)
        return locked

    def revision(self, garment: Garment, revision_id: str | None = None) -> Revision:
        """Fetch a revision with all tenant and aggregate predicates."""
        revision = self.session.scalar(
            select(Revision).where(
                Revision.id == (revision_id or garment.draft_revision_id),
                Revision.organization_id == self.organization_id,
                Revision.garment_id == garment.id,
            )
        )
        if revision is None:
            raise DomainError("not_found", 404)
        return revision

    @staticmethod
    def check_head(garment: Garment, base: str) -> None:
        """Never silently rebase an edit or decision."""
        if garment.draft_revision_id != base:
            raise DomainError("stale_revision")

    def event(self, kind: str, aggregate: str, revision: str | None, detail: Result) -> None:
        """Append audit and delivery intent in the business transaction."""
        event_id = new_id()
        self.session.add(
            Audit(
                organization_id=self.organization_id,
                created_by=self.actor,
                aggregate_id=aggregate,
                revision_id=revision,
                event_type=kind,
                detail=detail,
            )
        )
        self.session.add(
            Outbox(
                id=event_id,
                organization_id=self.organization_id,
                created_by=self.actor,
                envelope={
                    "event_id": event_id,
                    "organization_id": self.organization_id,
                    "aggregate_id": aggregate,
                    "revision_id": revision,
                    "schema_version": 1,
                    "causation_id": self.causation_id,
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "event_type": kind,
                    "payload": detail,
                },
            )
        )

    def write(
        self,
        key: str,
        route: str,
        body: Result,
        execute: Callable[[], Result],
        reauthorize: Callable[[Result], object] | None = None,
    ) -> Result:
        """Advisory lock serializes a scoped key; commit response with its effect."""
        digest = content_hash(
            {
                "actor": self.actor,
                "organization_id": self.organization_id,
                "method": "POST",
                "route": route,
                "body": body,
            }
        )
        lock_bytes = hashlib.sha256(f"{self.organization_id}:{self.actor}:{key}".encode()).digest()[
            :8
        ]
        lock_id = int.from_bytes(lock_bytes, byteorder="big", signed=True)
        self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        existing = self.session.scalar(
            select(Idempotency).where(
                Idempotency.organization_id == self.organization_id,
                Idempotency.actor_id == self.actor,
                Idempotency.key == key,
            )
        )
        if existing is not None:
            if existing.request_digest != digest:
                raise DomainError("idempotency_conflict")
            if reauthorize is not None:
                reauthorize(existing.response)
            return existing.response
        self.causation_id = new_id()
        result = execute()
        self.session.add(
            Idempotency(
                organization_id=self.organization_id,
                created_by=self.actor,
                actor_id=self.actor,
                key=key,
                request_digest=digest,
                response=result,
            )
        )
        self.session.flush()
        return result

    def create_project(self, command: dto.ProjectCreate, key: str) -> Result:
        """Create a workspace and grant its creator access atomically."""
        self.permit("designer", "org-admin")

        def execute() -> Result:
            project = Project(
                id=new_id(),
                organization_id=self.organization_id,
                created_by=self.actor,
                name=command.name,
            )
            self.session.add(project)
            self.session.flush()
            self.session.add(
                ProjectGrant(
                    organization_id=self.organization_id,
                    created_by=self.actor,
                    project_id=project.id,
                    user_id=self.actor,
                )
            )
            self.event("project.created", project.id, None, {})
            return {"id": project.id, "name": project.name}

        return self.write(
            key,
            "/v1/projects",
            command.model_dump(),
            execute,
            lambda response: self.project(str(response["id"])),
        )

    def create_garment(self, project_id: str, command: dto.GarmentCreate, key: str) -> Result:
        """Create the first immutable unapproved revision."""
        self.project(project_id)
        self.permit("designer")

        def execute() -> Result:
            garment = Garment(
                id=new_id(),
                organization_id=self.organization_id,
                created_by=self.actor,
                project_id=project_id,
                name=command.name,
            )
            self.session.add(garment)
            self.session.flush()
            revision = Revision(
                id=new_id(),
                organization_id=self.organization_id,
                created_by=self.actor,
                garment_id=garment.id,
                parent_revision_id=None,
                payload=command.design.model_dump(),
                content_hash=content_hash(command.design),
            )
            self.session.add(revision)
            self.session.flush()
            garment.draft_revision_id = revision.id
            self.event(
                "design.revision.created",
                garment.id,
                revision.id,
                {"parent_revision_id": None, "invalidated_artifacts": []},
            )
            return {
                "id": garment.id,
                "draft_revision_id": revision.id,
                "approved_revision_id": None,
                "content_hash": revision.content_hash,
            }

        return self.write(key, f"/v1/projects/{project_id}/garments", command.model_dump(), execute)

    def read_garment(self, garment_id: str) -> Result:
        """Expose heads, snapshot and purpose-specific historical decisions."""
        garment = self.garment(garment_id)
        revision = self.revision(garment)
        approvals = self.session.scalars(
            select(Approval)
            .where(
                Approval.organization_id == self.organization_id, Approval.garment_id == garment.id
            )
            .order_by(Approval.created_at, Approval.id)
        ).all()
        return {
            "id": garment.id,
            "project_id": garment.project_id,
            "name": garment.name,
            "draft_revision_id": garment.draft_revision_id,
            "approved_revision_id": garment.approved_revision_id,
            "content_hash": revision.content_hash,
            "design": revision.payload,
            "approvals": [
                {
                    "id": a.id,
                    "revision_id": a.revision_id,
                    "purpose": a.purpose,
                    "decision": a.decision,
                    "role": a.role,
                    "actor_id": a.created_by,
                }
                for a in approvals
            ],
        }

    def propose(self, gid: str, command: dto.ProposalCreate, key: str) -> Result:
        """Validate and hash a preview without changing the draft head."""
        garment = self.garment(gid)
        self.permit("designer", "patternmaker")

        def execute() -> Result:
            return self.stage_proposal(
                garment, command.base_revision, command.operations, command.justification
            )

        return self.write(key, f"/v1/garments/{gid}/patch-proposals", command.model_dump(), execute)

    def stage_proposal(
        self, garment: Garment, base_revision: str, operations: list[Patch], justification: str
    ) -> Result:
        """Stage a lock-checked patch inside an authorized command transaction."""
        self.check_head(garment, base_revision)
        preview = apply_patch(Design.model_validate(self.revision(garment).payload), operations)
        proposal = Proposal(
            id=new_id(),
            organization_id=self.organization_id,
            created_by=self.actor,
            garment_id=garment.id,
            base_revision=base_revision,
            operations=[p.model_dump() for p in operations],
            justification=justification,
            preview_hash=content_hash(preview),
        )
        self.session.add(proposal)
        self.event(
            "canvas.patch.proposed",
            garment.id,
            base_revision,
            {"patch_id": proposal.id, "preview_hash": proposal.preview_hash},
        )
        return {
            "id": proposal.id,
            "base_revision": base_revision,
            "preview_hash": proposal.preview_hash,
            "status": "proposed",
        }

    def get_proposal(self, gid: str, pid: str) -> Proposal:
        """Reject proposal ID substitution across garments and tenants."""
        proposal = self.session.scalar(
            select(Proposal).where(
                Proposal.id == pid,
                Proposal.garment_id == gid,
                Proposal.organization_id == self.organization_id,
            )
        )
        if proposal is None:
            raise DomainError("not_found", 404)
        return proposal

    def preview(self, gid: str, pid: str) -> Result:
        """Read-only deterministic preview; stale bases fail visibly."""
        garment = self.garment(gid)
        proposal = self.get_proposal(gid, pid)
        self.check_head(garment, proposal.base_revision)
        design = apply_patch(
            Design.model_validate(self.revision(garment).payload),
            [Patch.model_validate(p) for p in proposal.operations],
        )
        changed = {operation["target_component_id"] for operation in proposal.operations}
        if "garment" in changed:
            changed.add("material")
        impact = self.affected_artifacts(garment, changed)
        return {
            "id": pid,
            "base_revision": proposal.base_revision,
            "preview_hash": content_hash(design),
            "design": design.model_dump(),
            "status": proposal.status,
            "artifact_impact": [{"id": item.id, "kind": item.kind} for item in impact],
        }

    def affected_artifacts(self, garment: Garment, changed: set[str]) -> list[Artifact]:
        """Traverse artifact dependencies within the garment, including cyclic graphs."""
        from collections import defaultdict

        artifacts = list(
            self.session.scalars(
                select(Artifact).where(
                    Artifact.organization_id == self.organization_id,
                    Artifact.garment_id == garment.id,
                )
            )
        )
        if "*" in changed:
            return artifacts
        dependents: dict[str, list[Artifact]] = defaultdict(list)
        for artifact in artifacts:
            for dependency in artifact.depends_on:
                dependents[dependency].append(artifact)
        queue = list(changed | {"*"})
        affected: dict[str, Artifact] = {}
        while queue:
            for artifact in dependents.get(queue.pop(), []):
                if artifact.id not in affected:
                    affected[artifact.id] = artifact
                    queue.append(artifact.id)
        return list(affected.values())

    def commit(self, garment: Garment, design: Design, changed: set[str]) -> Result:
        """Commit a child and invalidate only affected artifact dependency edges."""
        parent = garment.draft_revision_id
        revision = Revision(
            id=new_id(),
            organization_id=self.organization_id,
            created_by=self.actor,
            garment_id=garment.id,
            parent_revision_id=parent,
            payload=design.model_dump(),
            content_hash=content_hash(design),
        )
        self.session.add(revision)
        self.session.flush()
        garment.draft_revision_id = revision.id
        affected = self.affected_artifacts(garment, changed)
        for artifact in affected:
            artifact.status = "needs_review"
        invalidated = [artifact.id for artifact in affected]
        self.event(
            "design.revision.created",
            garment.id,
            revision.id,
            {"parent_revision_id": parent, "invalidated_artifacts": sorted(invalidated)},
        )
        return {
            "new_revision": revision.id,
            "content_hash": revision.content_hash,
            "diff": sorted(changed),
            "invalidated_artifacts": sorted(invalidated),
            "approval_status": "unapproved",
        }

    def decide_proposal(
        self, gid: str, pid: str, command: dto.RevisionCommand, key: str, accept: bool
    ) -> Result:
        """Recheck locks and preview inside the head transaction before accepting."""
        garment = self.garment(gid)
        self.permit("designer")
        proposal = self.get_proposal(gid, pid)
        action = "accept" if accept else "reject"

        def execute() -> Result:
            self.check_head(garment, command.base_revision)
            if proposal.base_revision != command.base_revision or proposal.status != "proposed":
                raise DomainError("proposal_not_pending")
            if not accept:
                proposal.status = "rejected"
                self.event("canvas.patch.rejected", gid, command.base_revision, {"patch_id": pid})
                return {"id": pid, "status": "rejected"}
            operations = [Patch.model_validate(p) for p in proposal.operations]
            design = apply_patch(Design.model_validate(self.revision(garment).payload), operations)
            if content_hash(design) != proposal.preview_hash:
                raise DomainError("preview_hash_mismatch")
            changed = {p.target_component_id for p in operations}
            comparison_id = None
            if "garment" in changed:
                from apps.api.materials import comparison_link, eligible_offer

                if design.material_id is not None:
                    eligible_offer(self.session, self.organization_id, gid, design.material_id)
                    comparison_id = comparison_link(self, gid, pid)
                changed.add("material")
            result = self.commit(garment, design, changed)
            if comparison_id:
                self.event(
                    "material.substitution_committed",
                    gid,
                    result["new_revision"],
                    {"comparison_id": comparison_id, "offer_id": design.material_id},
                )
            proposal.status = "accepted"
            return result

        return self.write(
            key, f"/v1/garments/{gid}/patch-proposals/{pid}/{action}", command.model_dump(), execute
        )

    def approve(self, gid: str, command: dto.ApprovalCreate, key: str) -> Result:
        """Purpose authorization and exact hash checks occur under aggregate lock."""
        garment = self.garment(gid)
        permitted = {
            "aesthetic": ("designer", "client-reviewer"),
            "technical": ("patternmaker",),
            "handoff": ("production",),
        }[command.purpose]
        self.permit(*permitted)

        def execute() -> Result:
            self.check_head(garment, command.base_revision)
            if command.revision_id != command.base_revision:
                raise DomainError("stale_revision")
            revision = self.revision(garment)
            if command.content_hash != revision.content_hash:
                raise DomainError("approval_hash_mismatch")
            if command.purpose == "handoff":
                raise DomainError("handoff_not_available", 422)
            approval = Approval(
                id=new_id(),
                organization_id=self.organization_id,
                created_by=self.actor,
                garment_id=gid,
                revision_id=revision.id,
                content_hash=revision.content_hash,
                purpose=command.purpose,
                decision=command.decision,
                role=next(r for r in permitted if r in self.roles),
            )
            self.session.add(approval)
            evidence: Result = {}
            if command.purpose == "technical":
                from apps.api.samples import sample_snapshot

                evidence["sample_digest"] = content_hash(
                    {"samples": sample_snapshot(self, gid, revision.id)}
                )
            if command.purpose == "aesthetic":
                garment.approved_revision_id = (
                    revision.id if command.decision == "approve" else None
                )
            self.event(
                "approval.decided",
                gid,
                revision.id,
                {
                    "approval_id": approval.id,
                    "purpose": command.purpose,
                    "decision": command.decision,
                    "content_hash": revision.content_hash,
                    **evidence,
                },
            )
            return {
                "id": approval.id,
                "revision_id": revision.id,
                "purpose": command.purpose,
                "decision": command.decision,
            }

        return self.write(key, f"/v1/garments/{gid}/approvals", command.model_dump(), execute)

    def request_unlock(self, gid: str, command: dto.UnlockCreate, key: str) -> Result:
        """Record an exact component lock request, with no implicit unlock."""
        garment = self.garment(gid)
        self.permit("designer")

        def execute() -> Result:
            self.check_head(garment, command.base_revision)
            design = Design.model_validate(self.revision(garment).payload)
            if not any(c.id == command.component_id and c.locked for c in design.components):
                raise DomainError("not_locked", 422)
            request = UnlockRequest(
                id=new_id(),
                organization_id=self.organization_id,
                created_by=self.actor,
                garment_id=gid,
                base_revision=command.base_revision,
                component_id=command.component_id,
                reason=command.reason,
            )
            self.session.add(request)
            self.event(
                "constraint.unlock.requested",
                gid,
                command.base_revision,
                {"unlock_request_id": request.id, "component_id": command.component_id},
            )
            return {"id": request.id, "status": "pending"}

        return self.write(key, f"/v1/garments/{gid}/unlock-requests", command.model_dump(), execute)

    def add_constraint(self, gid: str, command: dto.ConstraintCreate, key: str) -> Result:
        """Adding a lock produces a new unapproved revision, never an unlock."""
        garment = self.garment(gid)
        self.permit("designer")

        def execute() -> Result:
            self.check_head(garment, command.base_revision)
            design = Design.model_validate(self.revision(garment).payload)
            target = next((c for c in design.components if c.id == command.component_id), None)
            if target is None:
                raise DomainError("unknown_component", 422)
            if target.locked:
                raise DomainError("constraint_already_exists")
            target.locked = True
            return self.commit(garment, design, {"*"})

        return self.write(key, f"/v1/garments/{gid}/constraints", command.model_dump(), execute)

    def decide_unlock(self, gid: str, uid: str, command: dto.UnlockDecision, key: str) -> Result:
        """A distinct administrator authorizes a new draft with only lock changed."""
        garment = self.garment(gid)
        self.permit("org-admin")
        request = self.session.scalar(
            select(UnlockRequest).where(
                UnlockRequest.id == uid,
                UnlockRequest.garment_id == gid,
                UnlockRequest.organization_id == self.organization_id,
            )
        )
        if request is None:
            raise DomainError("not_found", 404)

        def execute() -> Result:
            self.check_head(garment, command.base_revision)
            if (
                request is None
                or request.status != "pending"
                or (request.base_revision != command.base_revision)
            ):
                raise DomainError("unlock_not_pending")
            if request.created_by == self.actor:
                raise DomainError("self_unlock_forbidden", 403)
            result: Result = {"id": uid, "status": "rejected"}
            if command.decision == "grant":
                design = Design.model_validate(self.revision(garment).payload)
                for component in design.components:
                    if component.id == request.component_id:
                        component.locked = False
                result = self.commit(garment, design, {"*"})
            request.status = command.decision
            self.event(
                "constraint.unlock.decided",
                gid,
                garment.draft_revision_id,
                {"unlock_request_id": uid, "decision": command.decision},
            )
            return result

        return self.write(
            key,
            f"/v1/garments/{gid}/unlock-requests/{uid}/decisions",
            command.model_dump(),
            execute,
        )
