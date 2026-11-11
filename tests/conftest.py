"""Isolated PostgreSQL schemas and signed synthetic users; no SQLite fallback."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from apps.api.config import Settings
from apps.api.models import Membership, Organization, User


@pytest.fixture(scope="session")
def keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


@pytest.fixture()
def database():
    url = os.environ.get(
        "ATELIER_TEST_DATABASE_URL",
        "postgresql+psycopg://atelier_test@127.0.0.1:55439/atelier_test",
    )
    parsed = make_url(url)
    if not (parsed.database or "").startswith("atelier_test"):
        raise RuntimeError("Tests require an explicitly disposable atelier_test* database")
    schema = "test_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        connect_args={
            "options": f"-csearch_path={schema} -cstatement_timeout=15000 -clock_timeout=10000"
        },
        pool_size=10,
    )
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine, config
    engine.dispose()
    # Only the unique schema created by this fixture is ever removed.
    if not schema.startswith("test_") or len(schema) != 37:
        raise RuntimeError("Unsafe test schema target")
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.fixture()
def api(database, keys):
    from apps.api.main import create_app

    engine, _ = database
    private, public = keys
    with Session(engine) as session, session.begin():
        organization = Organization(id=str(uuid4()), name="Synthetic studio", created_by="test")
        other = Organization(id=str(uuid4()), name="Other synthetic studio", created_by="test")
        session.add_all([organization, other])
        session.flush()
        users = {}
        for role in ("designer", "client-reviewer", "patternmaker", "production", "org-admin"):
            user = User(id=str(uuid4()), subject=role, created_by="test")
            session.add(user)
            session.flush()
            session.add(
                Membership(
                    organization_id=organization.id,
                    user_id=user.id,
                    roles=[role],
                    active=True,
                    created_by="test",
                )
            )
            users[role] = user.id
        session.flush()
        org_id, other_id = organization.id, other.id
    settings = Settings(
        database_url=str(engine.url),
        jwt_public_key=public,
        jwt_issuer="https://issuer.synthetic",
        jwt_audience="atelier-test",
        allowed_hosts=["testserver"],
    )
    app = create_app(settings, engine=engine)

    def token(role="designer", organization_id=org_id, principal_type="human", **overrides):
        now = datetime.now(UTC)
        claims = {
            "sub": role,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "organization_id": organization_id,
            "principal_type": principal_type,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
            **overrides,
        }
        return jwt.encode(claims, private, algorithm="RS256")

    with TestClient(app) as client:
        yield {
            "client": client,
            "token": token,
            "engine": engine,
            "users": users,
            "organization_id": org_id,
            "other_id": other_id,
            "settings": settings,
        }
