"""PostgreSQL internal event delivery and external intent reconciliation primitives."""

from collections.abc import Callable
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from apps.api.models import Outbox, Receipt, ToolAttempt, new_id
from packages.domain.design import DomainError


def consume_one(
    engine: Engine, consumer: str, apply: Callable[[Session, dict[str, Any]], None]
) -> bool:
    """Single logical consumer; callback may perform only same-transaction DB effects.

    A crash rolls back both receipt and effect. External side effects must instead
    use a committed ToolAttempt intent and a provider idempotency/reconciliation
    protocol (P05); they must never run in this transaction.
    """
    with Session(engine) as session, session.begin():
        event = session.scalar(
            select(Outbox)
            .where(Outbox.delivered.is_(False))
            .order_by(Outbox.created_at, Outbox.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if event is None:
            return False
        receipt = session.scalar(
            select(Receipt).where(
                Receipt.organization_id == event.organization_id,
                Receipt.consumer == consumer,
                Receipt.event_id == event.id,
            )
        )
        if receipt is None:
            apply(session, event.envelope)
            session.add(
                Receipt(
                    organization_id=event.organization_id,
                    created_by="outbox-worker",
                    consumer=consumer,
                    event_id=event.id,
                )
            )
        event.delivered = True
        event.attempts += 1
        return True


def reserve_attempt(engine: Engine, organization_id: str, key: str, digest: str, actor: str) -> str:
    """Commit intent before invoking a provider; repeated pending intents reconcile."""
    with Session(engine) as session, session.begin():
        inserted = session.scalar(
            insert(ToolAttempt)
            .values(
                id=new_id(),
                organization_id=organization_id,
                created_by=actor,
                idempotency_key=key,
                request_digest=digest,
                status="pending",
            )
            .on_conflict_do_nothing(index_elements=["organization_id", "idempotency_key"])
            .returning(ToolAttempt.id)
        )
        attempt = session.scalar(
            select(ToolAttempt)
            .where(
                ToolAttempt.organization_id == organization_id, ToolAttempt.idempotency_key == key
            )
            .with_for_update()
        )
        if attempt is None:
            raise RuntimeError("Attempt admission failed")
        if attempt.request_digest != digest:
            raise DomainError("idempotency_conflict")
        return (
            "admitted"
            if inserted
            else ("reconcile" if attempt.status == "pending" else attempt.status)
        )


def finish_attempt(
    engine: Engine,
    organization_id: str,
    key: str,
    digest: str,
    outcome: Literal["succeeded", "failed"],
) -> None:
    """Record a reconciled outcome without permitting terminal-state rewrites."""
    with Session(engine) as session, session.begin():
        attempt = session.scalar(
            select(ToolAttempt)
            .where(
                ToolAttempt.organization_id == organization_id, ToolAttempt.idempotency_key == key
            )
            .with_for_update()
        )
        if attempt is None:
            raise DomainError("not_found", 404)
        if attempt.request_digest != digest:
            raise DomainError("idempotency_conflict")
        if attempt.status not in ("pending", outcome):
            raise DomainError("attempt_already_final")
        attempt.status = outcome
