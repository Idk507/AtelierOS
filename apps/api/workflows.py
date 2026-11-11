"""A bounded LangGraph draft workflow with application-owned durable review state."""

from typing import Any, Literal, TypedDict

from fastapi import APIRouter
from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.dto import RevisionCommand
from apps.api.main import Key, Svc
from apps.api.models import Base, Proposal, new_id
from apps.api.multimodal import FixtureProvider, GeometryEdit
from apps.api.research import ResearchRecord, revision_reference
from packages.domain.design import Design, DomainError, Patch, apply_patch, content_hash

router = APIRouter(prefix="/v1/garments/{gid}/workflows", tags=["workflows"])


class WorkflowRun(ResearchRecord, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = revision_reference()

    status: Mapped[str] = mapped_column(String(30))
    decided_by: Mapped[str | None] = mapped_column(String(200))
    proposal_id: Mapped[str | None] = mapped_column(ForeignKey("proposals.id"))


class StartRun(RevisionCommand):
    mode: Literal["concept", "geometry"]
    edit: GeometryEdit | None = None


class DecideRun(RevisionCommand):
    checkpoint_digest: str
    decision: Literal["approve", "reject", "cancel"]


class State(TypedDict):
    mode: str
    source: dict[str, Any]
    edit: dict[str, Any] | None
    result: dict[str, Any]
    preview_digest: str | None


def generate(state: State) -> dict[str, Any]:
    """Only the fixed local capability can run in this graph node."""
    if state["mode"] == "concept" and state["edit"] is None:
        result = FixtureProvider().run("image", "Offline garment concept")
        return {"result": result.model_dump(exclude_none=True)}
    if state["mode"] == "geometry" and state["edit"] is not None:
        edit = GeometryEdit.model_validate(state["edit"])
        if edit.component_id == "garment":
            raise DomainError("workflow_scope_denied", 422)
        operation = Patch(
            op="update", target_component_id=edit.component_id, payload={"geometry": edit.geometry}
        )
        return {
            "result": {
                "provider": "studio",
                "estimated_cost": 0,
                "operations": [operation.model_dump()],
            }
        }
    raise DomainError("invalid_workflow_input", 422)


def check_proposal(state: State) -> dict[str, Any]:
    """Independently validate the edits against canonical locks and structure."""
    operations = state["result"].get("operations")
    if operations is None:
        return {"preview_digest": None}
    design = Design.model_validate(state["source"])
    candidate = apply_patch(design, [Patch.model_validate(operation) for operation in operations])
    return {"preview_digest": content_hash(candidate)}


graph = (
    StateGraph(State)
    .add_node("generate", generate)
    .add_node("check_proposal", check_proposal)
    .add_edge(START, "generate")
    .add_edge("generate", "check_proposal")
    .add_edge("check_proposal", END)
    .compile()
)


def view(run: WorkflowRun, actor: str) -> dict[str, Any]:
    return {
        "id": run.id,
        "revision_id": run.revision_id,
        "status": run.status,
        "proposal_id": run.proposal_id,
        "created_by_viewer": run.created_by == actor,
        **run.payload,
    }


@router.get("")
def list_runs(gid: str, svc: Svc) -> list[dict[str, Any]]:
    svc.garment(gid)
    runs = svc.session.scalars(
        select(WorkflowRun)
        .filter_by(organization_id=svc.organization_id, garment_id=gid)
        .order_by(WorkflowRun.created_at.desc())
        .limit(12)
    )
    return [view(run, svc.actor) for run in runs]


@router.post("", status_code=201)
def start_run(gid: str, body: StartRun, key: Key, svc: Svc) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")

    def write() -> dict[str, Any]:
        svc.check_head(garment, body.base_revision)
        revision = svc.revision(garment)
        with tracing_context(enabled=False):
            state = graph.invoke(
                {
                    "mode": body.mode,
                    "source": revision.payload,
                    "edit": body.edit.model_dump() if body.edit else None,
                    "result": {},
                    "preview_digest": None,
                },
                config={"recursion_limit": 4, "callbacks": []},
            )
        payload = {
            "mode": body.mode,
            "revision_digest": revision.content_hash,
            "result": state["result"],
            "preview_digest": state["preview_digest"],
        }
        payload["checkpoint_digest"] = content_hash(payload)
        run = WorkflowRun(
            id=new_id(),
            organization_id=svc.organization_id,
            garment_id=gid,
            revision_id=revision.id,
            created_by=svc.actor,
            payload=payload,
            status="awaiting_review",
        )
        svc.session.add(run)
        svc.event("workflow.review_requested", gid, revision.id, {"workflow_id": run.id})
        return view(run, svc.actor)

    return svc.write(key, f"/v1/garments/{gid}/workflows", body.model_dump(), write)


@router.post("/{run_id}/decision")
def decide_run(gid: str, run_id: str, body: DecideRun, key: Key, svc: Svc) -> dict[str, Any]:
    garment = svc.garment(gid)
    svc.permit("designer", "patternmaker")

    def write() -> dict[str, Any]:
        run = svc.session.scalar(
            select(WorkflowRun)
            .filter_by(id=run_id, organization_id=svc.organization_id, garment_id=gid)
            .with_for_update()
        )
        if run is None:
            raise DomainError("not_found", 404)
        if run.status != "awaiting_review":
            raise DomainError("workflow_already_decided")
        if body.decision == "cancel":
            if run.created_by != svc.actor:
                raise DomainError("forbidden", 403)
        elif run.created_by == svc.actor:
            raise DomainError("independent_review_required", 403)
        expected = {
            name: value for name, value in run.payload.items() if name != "checkpoint_digest"
        }
        if (
            body.checkpoint_digest != run.payload["checkpoint_digest"]
            or content_hash(expected) != body.checkpoint_digest
        ):
            raise DomainError("workflow_checkpoint_mismatch")
        if body.decision == "approve":
            svc.check_head(garment, body.base_revision)
            if run.revision_id != body.base_revision:
                raise DomainError("stale_workflow")
            revision = svc.revision(garment)
            if revision.content_hash != run.payload["revision_digest"]:
                raise DomainError("workflow_checkpoint_mismatch")
            operations = run.payload["result"].get("operations")
            if operations:
                candidate = apply_patch(
                    Design.model_validate(revision.payload),
                    [Patch.model_validate(operation) for operation in operations],
                )
                if content_hash(candidate) != run.payload["preview_digest"]:
                    raise DomainError("workflow_checkpoint_mismatch")
                proposal = Proposal(
                    id=new_id(),
                    organization_id=svc.organization_id,
                    garment_id=gid,
                    base_revision=revision.id,
                    created_by=svc.actor,
                    operations=operations,
                    justification=f"Independent review of workflow {run.id}",
                    preview_hash=run.payload["preview_digest"],
                    status="proposed",
                )
                svc.session.add(proposal)
                svc.session.flush()
                run.proposal_id = proposal.id
        run.status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[
            body.decision
        ]
        run.decided_by = svc.actor
        svc.event(
            "workflow.review_decided",
            gid,
            run.revision_id,
            {"workflow_id": run.id, "status": run.status, "proposal_id": run.proposal_id},
        )
        return view(run, svc.actor)

    return svc.write(
        key, f"/v1/garments/{gid}/workflows/{run_id}/decision", body.model_dump(), write
    )
