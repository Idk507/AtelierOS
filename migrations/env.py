"""Alembic execution with explicit URL or caller-owned test connection."""

import os

from alembic import context
from sqlalchemy import create_engine

from apps.api.models import Base

config = context.config


def run() -> None:
    """Use one transaction for schema DDL; do not load private env files."""
    supplied = config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    url = os.environ.get("ATELIER_DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Set ATELIER_DATABASE_URL to an explicitly selected PostgreSQL database")
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run()
