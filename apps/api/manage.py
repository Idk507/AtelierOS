"""Explicit operator provisioning; there is no unauthenticated bootstrap endpoint."""

from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.models import Membership, Organization, Project, ProjectGrant, User, new_id

ROLES = ("designer", "client-reviewer", "patternmaker", "production", "org-admin")


def provision(
    session: Session,
    subject: str,
    roles: list[str],
    *,
    organization_id: str | None = None,
    organization_name: str | None = None,
    project_id: str | None = None,
) -> tuple[str, str]:
    """Grant an issuer subject explicit roles and optional project access atomically.

    Operators must use a migration/provisioning DB role unavailable to the HTTP
    service. Existing memberships are replaced with the explicitly supplied roles.
    """
    if not subject or len(subject) > 200 or not roles or not set(roles) <= set(ROLES):
        raise ValueError("Supply a valid subject and explicit supported roles")
    if bool(organization_id) == bool(organization_name):
        raise ValueError("Choose an existing organization ID or a new organization name")
    if organization_id:
        organization = session.get(Organization, organization_id)
        if organization is None:
            raise ValueError("Organization does not exist")
    else:
        organization = Organization(
            id=new_id(), name=organization_name or "", created_by="operator"
        )
        session.add(organization)
        session.flush()
    user = session.scalar(select(User).where(User.subject == subject))
    if user is None:
        user = User(id=new_id(), subject=subject, created_by="operator")
        session.add(user)
        session.flush()
    membership = session.scalar(
        select(Membership)
        .where(Membership.organization_id == organization.id, Membership.user_id == user.id)
        .with_for_update()
    )
    if membership is None:
        membership = Membership(
            organization_id=organization.id,
            user_id=user.id,
            roles=sorted(set(roles)),
            active=True,
            created_by="operator",
        )
        session.add(membership)
    else:
        membership.roles, membership.active = sorted(set(roles)), True
    if project_id:
        project = session.scalar(
            select(Project).where(
                Project.id == project_id, Project.organization_id == organization.id
            )
        )
        if project is None:
            raise ValueError("Project does not belong to this organization")
        grant = session.scalar(
            select(ProjectGrant).where(
                ProjectGrant.organization_id == organization.id,
                ProjectGrant.project_id == project_id,
                ProjectGrant.user_id == user.id,
            )
        )
        if grant is None:
            session.add(
                ProjectGrant(
                    organization_id=organization.id,
                    project_id=project_id,
                    user_id=user.id,
                    created_by="operator",
                )
            )
    return organization.id, user.id


def main() -> None:
    """Provision only the database explicitly selected in the process environment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--roles", nargs="+", choices=ROLES, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--organization-id")
    group.add_argument("--organization-name")
    parser.add_argument("--project-id")
    args = parser.parse_args()
    url = os.environ.get("ATELIER_DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        parser.error("Set ATELIER_DATABASE_URL explicitly; private .env files are not loaded")
    engine = create_engine(url)
    try:
        with Session(engine) as session, session.begin():
            organization, user = provision(
                session,
                args.subject,
                args.roles,
                organization_id=args.organization_id,
                organization_name=args.organization_name,
                project_id=args.project_id,
            )
        print(f"Provisioned organization_id={organization} user_id={user}")
    except ValueError as exc:
        parser.error(str(exc))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
