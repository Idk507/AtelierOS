"""FastAPI application factory with explicit configuration and transactional routes."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from apps.api import dto
from apps.api.auth import Identity, verify_token
from apps.api.config import Settings
from apps.api.models import Audit, Garment, Project, ProjectGrant
from apps.api.service import Service
from packages.domain.design import DomainError

logger = logging.getLogger("atelier.api")
bearer = HTTPBearer(auto_error=False)


class BodyLimit:
    """Bound streaming request bodies before parsing, regardless of Content-Length."""

    def __init__(self, app: ASGIApp, limit: int = 1_048_576) -> None:
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        buffered = bytearray()
        while True:
            message = await receive()
            chunk = message.get("body", b"")
            if len(buffered) + len(chunk) > self.limit:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "payload_too_large",
                            "message": "Request exceeds size limit",
                            "request_id": scope.get("state", {}).get("request_id", str(uuid4())),
                        }
                    },
                    413,
                )
                await response(scope, receive, send)
                return
            buffered.extend(chunk)
            if message["type"] == "http.disconnect" or not message.get("more_body", False):
                break

        pending = True

        async def bounded_receive() -> Message:
            nonlocal pending
            if pending:
                pending = False
                return {"type": "http.request", "body": bytes(buffered), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)


def identity(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> Identity:
    """Validate configured issuer credentials; missing bearer fails closed."""
    if credentials is None or len(credentials.credentials) > 8192:
        raise DomainError("unauthenticated", 401)
    return verify_token(credentials.credentials, request.app.state.settings)


def service(request: Request, actor: Annotated[Identity, Depends(identity)]) -> Iterator[Service]:
    """Commit before response generation; failed business writes roll back entirely."""
    instance = None
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        try:
            with session.begin():
                instance = Service(session, actor)
                yield instance
        except DomainError as exc:
            # Denials are a separate audit transaction, never a partial business commit.
            if instance is not None:
                with session.begin():
                    session.add(
                        Audit(
                            organization_id=instance.organization_id,
                            created_by=instance.actor,
                            aggregate_id="request",
                            revision_id=None,
                            event_type="security.denied",
                            detail={"code": exc.code, "request_id": request.state.request_id},
                        )
                    )
            raise


Svc = Annotated[Service, Depends(service, scope="function")]
Key = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_.:-]+$"),
]


def create_app(settings: Settings, *, engine: Engine | None = None) -> FastAPI:
    """Construct the API without migrations, external calls or demo authentication."""
    app = FastAPI(title="AtelierOS API", version="0.1.0")
    from apps.api.handoff import router as handoff_router
    from apps.api.materials import router as materials_router
    from apps.api.research import router as research_router
    from apps.api.samples import router as samples_router
    from apps.api.workflows import router as workflow_router

    app.include_router(research_router)
    app.include_router(materials_router)
    app.include_router(handoff_router)
    app.include_router(samples_router)
    app.include_router(workflow_router)
    app.state.settings = settings
    app.state.engine = (
        engine
        if engine is not None
        else create_engine(
            settings.database_url,
            pool_pre_ping=True,
            connect_args={
                "options": (
                    str(make_url(settings.database_url).query.get("options", ""))
                    + " -cstatement_timeout=15000 -clock_timeout=10000"
                )
            },
        )
    )
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.middleware("http")
    async def request_metadata(request: Request, call_next: Any) -> Any:
        request.state.request_id = str(uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            "request id=%s method=%s status=%s duration_ms=%.2f",
            request.state.request_id,
            request.method,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    def error(request: Request, code: str, status: int) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": code,
                    "message": code.replace("_", " "),
                    "request_id": getattr(request.state, "request_id", str(uuid4())),
                }
            },
            status_code=status,
            headers={"WWW-Authenticate": "Bearer"} if status == 401 else None,
        )

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return error(request, exc.code, exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(request, "invalid_payload", 422)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        response = error(request, code, exc.status_code)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error("database_failure request_id=%s", request.state.request_id)
        return error(request, "temporarily_unavailable", 503)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unexpected_failure request_id=%s", request.state.request_id)
        return error(request, "internal_error", 500)

    @app.get("/health/live", include_in_schema=False)
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    def ready() -> dict[str, str]:
        with app.state.engine.connect() as connection:
            version = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if version != "0006":
                raise DomainError("schema_not_ready", 503)
        return {"status": "ready"}

    @app.post("/v1/projects", status_code=201)
    def create_project(command: dto.ProjectCreate, svc: Svc, key: Key) -> dict[str, Any]:
        return svc.create_project(command, key)

    @app.get("/v1/projects")
    def projects(
        svc: Svc, limit: Annotated[int, Query(ge=1, le=100)] = 50, after: str = ""
    ) -> list[dict[str, str]]:
        records = svc.session.scalars(
            select(Project)
            .join(
                ProjectGrant,
                (ProjectGrant.project_id == Project.id)
                & (ProjectGrant.organization_id == Project.organization_id),
            )
            .where(
                Project.organization_id == svc.organization_id,
                ProjectGrant.user_id == svc.actor,
                Project.id > after,
            )
            .order_by(Project.id)
            .limit(limit)
        )
        return [{"id": p.id, "name": p.name} for p in records]

    @app.get("/v1/projects/{project_id}")
    def project(project_id: str, svc: Svc) -> dict[str, str]:
        item = svc.project(project_id)
        return {"id": item.id, "name": item.name}

    @app.post("/v1/projects/{project_id}/garments", status_code=201)
    def create_garment(
        project_id: str, command: dto.GarmentCreate, svc: Svc, key: Key
    ) -> dict[str, Any]:
        return svc.create_garment(project_id, command, key)

    @app.get("/v1/projects/{project_id}/garments")
    def garments(
        project_id: str, svc: Svc, limit: Annotated[int, Query(ge=1, le=100)] = 50, after: str = ""
    ) -> list[dict[str, Any]]:
        svc.project(project_id)
        records = svc.session.scalars(
            select(Garment)
            .where(
                Garment.organization_id == svc.organization_id,
                Garment.project_id == project_id,
                Garment.id > after,
            )
            .order_by(Garment.id)
            .limit(limit)
        )
        return [
            {
                "id": g.id,
                "name": g.name,
                "draft_revision_id": g.draft_revision_id,
                "approved_revision_id": g.approved_revision_id,
            }
            for g in records
        ]

    @app.get("/v1/garments/{gid}")
    def garment(gid: str, svc: Svc) -> dict[str, Any]:
        return svc.read_garment(gid)

    @app.get("/v1/garments/{gid}/revisions/{rid}")
    def revision(gid: str, rid: str, svc: Svc) -> dict[str, Any]:
        item = svc.revision(svc.garment(gid), rid)
        return {
            "id": item.id,
            "parent_revision_id": item.parent_revision_id,
            "content_hash": item.content_hash,
            "design": item.payload,
        }

    @app.post("/v1/garments/{gid}/patch-proposals", status_code=201)
    def propose(gid: str, command: dto.ProposalCreate, svc: Svc, key: Key) -> dict[str, Any]:
        return svc.propose(gid, command, key)

    @app.get("/v1/garments/{gid}/patch-proposals/{pid}/preview")
    def preview(gid: str, pid: str, svc: Svc) -> dict[str, Any]:
        return svc.preview(gid, pid)

    @app.post("/v1/garments/{gid}/patch-proposals/{pid}/accept", status_code=201)
    def accept(
        gid: str, pid: str, command: dto.RevisionCommand, svc: Svc, key: Key
    ) -> dict[str, Any]:
        return svc.decide_proposal(gid, pid, command, key, True)

    @app.post("/v1/garments/{gid}/patch-proposals/{pid}/reject")
    def reject(
        gid: str, pid: str, command: dto.RevisionCommand, svc: Svc, key: Key
    ) -> dict[str, Any]:
        return svc.decide_proposal(gid, pid, command, key, False)

    @app.post("/v1/garments/{gid}/approvals", status_code=201)
    def approve(gid: str, command: dto.ApprovalCreate, svc: Svc, key: Key) -> dict[str, Any]:
        return svc.approve(gid, command, key)

    @app.post("/v1/garments/{gid}/unlock-requests", status_code=201)
    def unlock(gid: str, command: dto.UnlockCreate, svc: Svc, key: Key) -> dict[str, Any]:
        return svc.request_unlock(gid, command, key)

    @app.post("/v1/garments/{gid}/constraints", status_code=201)
    def constraint(gid: str, command: dto.ConstraintCreate, svc: Svc, key: Key) -> dict[str, Any]:
        return svc.add_constraint(gid, command, key)

    @app.post("/v1/garments/{gid}/unlock-requests/{uid}/decisions", status_code=201)
    def unlock_decision(
        gid: str, uid: str, command: dto.UnlockDecision, svc: Svc, key: Key
    ) -> dict[str, Any]:
        return svc.decide_unlock(gid, uid, command, key)

    @app.get("/v1/garments/{gid}/audit")
    def audit(
        gid: str, svc: Svc, limit: Annotated[int, Query(ge=1, le=100)] = 50
    ) -> list[dict[str, Any]]:
        svc.garment(gid)
        records = svc.session.scalars(
            select(Audit)
            .where(Audit.organization_id == svc.organization_id, Audit.aggregate_id == gid)
            .order_by(Audit.created_at.desc(), Audit.id)
            .limit(limit)
        )
        return [
            {
                "id": a.id,
                "event_type": a.event_type,
                "revision_id": a.revision_id,
                "created_at": a.created_at.isoformat(),
                "detail": a.detail,
            }
            for a in records
        ]

    return app


def build_app() -> FastAPI:
    """Uvicorn --factory entry point; absent auth/DB settings prevent startup."""
    return create_app(Settings())
