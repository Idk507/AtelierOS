"""Operator identity bootstrap is explicit and project-scoped."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.manage import provision
from apps.api.models import Membership


def test_provision_and_replace_roles_without_duplicate_membership(database):
    engine, _ = database
    with Session(engine) as session, session.begin():
        org, user = provision(
            session,
            "synthetic-operator-subject",
            ["designer"],
            organization_name="Synthetic operator studio",
        )
    with Session(engine) as session, session.begin():
        assert provision(
            session, "synthetic-operator-subject", ["patternmaker"], organization_id=org
        ) == (org, user)
        membership = session.scalar(select(Membership).where(Membership.user_id == user))
        assert membership.roles == ["patternmaker"]
    with pytest.raises(ValueError), Session(engine) as session, session.begin():
        provision(session, "subject", ["superuser"], organization_id=org)
