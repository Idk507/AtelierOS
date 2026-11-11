"""Transaction rollback, migration reversibility and durable recovery acceptance."""

import pytest
from alembic import command
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from apps.api.models import Audit, Outbox, Project, Receipt, ToolAttempt
from apps.api.recovery import consume_one, finish_attempt, reserve_attempt
from apps.api.service import Service
from packages.domain.design import DomainError


def test_migration_upgrade_downgrade_upgrade(database):
    engine, config = database
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert connection.scalar(text("SELECT to_regclass('revisions')")) is None
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006"


def test_internal_consumer_rolls_back_then_deduplicates(api):
    # Generate an outbox event through the API, not by assuming a fixture succeeds.
    from tests.test_api import headers

    response = api["client"].post("/v1/projects", headers=headers(api), json={"name": "Recovery"})
    assert response.status_code == 201
    calls = []

    def fail(session, envelope):
        calls.append(envelope["event_id"])
        raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError):
        consume_one(api["engine"], "test-consumer", fail)
    with Session(api["engine"]) as session:
        assert session.scalar(select(func.count()).select_from(Receipt)) == 0
        assert session.scalar(select(Outbox)).delivered is False

    def success(session, envelope):
        calls.append(envelope["event_id"])
        session.add(
            Audit(
                organization_id=api["organization_id"],
                created_by="test",
                aggregate_id="consumer",
                revision_id=None,
                event_type="consumer.effect",
                detail={},
            )
        )

    assert consume_one(api["engine"], "test-consumer", success) is True
    assert consume_one(api["engine"], "test-consumer", success) is False
    assert len(calls) == 2
    with Session(api["engine"]) as session:
        assert session.scalar(select(func.count()).select_from(Receipt)) == 1
        assert (
            session.scalar(
                select(func.count()).select_from(Audit).where(Audit.event_type == "consumer.effect")
            )
            == 1
        )


def test_attempt_intent_survives_unknown_outcome(api):
    org = api["organization_id"]
    engine = api["engine"]
    assert reserve_attempt(engine, org, "call-1", "a" * 64, "test") == "admitted"
    assert reserve_attempt(engine, org, "call-1", "a" * 64, "test") == "reconcile"
    with pytest.raises(DomainError):
        reserve_attempt(engine, org, "call-1", "b" * 64, "test")
    finish_attempt(engine, org, "call-1", "a" * 64, "succeeded")
    assert reserve_attempt(engine, org, "call-1", "a" * 64, "test") == "succeeded"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ToolAttempt)) == 1


def test_failed_event_write_rolls_back_business_and_idempotency(api, monkeypatch):
    from tests.test_api import headers

    original = Service.event

    def crash(self, *args):
        original(self, *args)
        raise RuntimeError("synthetic commit interruption")

    monkeypatch.setattr(Service, "event", crash)
    with pytest.raises(RuntimeError):
        api["client"].post("/v1/projects", headers=headers(api), json={"name": "No partial write"})
    with Session(api["engine"]) as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 0
        assert session.scalar(select(func.count()).select_from(Outbox)) == 0
