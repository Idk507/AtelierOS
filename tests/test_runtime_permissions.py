"""Exercise HTTP service commands using the restricted database role template."""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apps.api.auth import Identity
from apps.api.dto import ProjectCreate
from apps.api.service import Service


def test_restricted_runtime_can_execute_but_cannot_rewrite_history(api):
    engine = api["engine"]
    suffix = uuid4().hex
    api_role, worker_role = "test_api_" + suffix, "test_worker_" + suffix
    with engine.begin() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
        template = Path("infra/p01_runtime_permissions.sql").read_text()
        template = "\n".join(line.split("--")[0] for line in template.splitlines())
        template = template.replace("atelier_api", api_role).replace("atelier_worker", worker_role)
        template = template.replace("SCHEMA public", f'SCHEMA "{schema}"')
        for statement in template.split(";"):
            if statement.strip():
                connection.execute(text(statement))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{api_role}"'))
            with Session(bind=connection) as session:
                service = Service(session, Identity("designer", api["organization_id"], "human"))
                response = service.create_project(ProjectCreate(name="Least privilege"), new_key())
                session.flush()
                assert service.project(response["id"]).name == "Least privilege"
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{api_role}"'))
            connection.execute(text("UPDATE revisions SET content_hash='forbidden'"))
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{api_role}"'))
            connection.execute(text("UPDATE memberships SET roles='[\"org-admin\"]'::jsonb"))
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text(f'SET LOCAL ROLE "{api_role}"'))
            connection.execute(text("UPDATE memberships SET id=id"))
    finally:
        # Only these freshly generated group roles are ever removed.
        with engine.begin() as connection:
            for role in (api_role, worker_role):
                connection.execute(text(f'DROP OWNED BY "{role}"'))
                connection.execute(text(f'DROP ROLE "{role}"'))


def new_key():
    return str(uuid4())
