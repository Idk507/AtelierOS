"""Issuer-validated identity; application roles are loaded from PostgreSQL."""

from dataclasses import dataclass
from typing import Literal

import jwt

from apps.api.config import Settings
from packages.domain.design import DomainError


@dataclass(frozen=True)
class Identity:
    """Signed identity claims; this object grants no project membership."""

    subject: str
    organization_id: str
    principal_type: Literal["human", "service"]


def verify_token(token: str, settings: Settings) -> Identity:
    """Verify a fixed algorithm, issuer, audience, time claims and actor type."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={
                "require": [
                    "exp",
                    "iat",
                    "nbf",
                    "sub",
                    "iss",
                    "aud",
                    "organization_id",
                    "principal_type",
                ]
            },
        )
        subject, organization = claims["sub"], claims["organization_id"]
        kind = claims["principal_type"]
        if not isinstance(subject, str) or not 1 <= len(subject) <= 200:
            raise ValueError("invalid subject")
        if not isinstance(organization, str) or not 1 <= len(organization) <= 100:
            raise ValueError("invalid organization")
        if kind not in ("human", "service"):
            raise ValueError("invalid principal type")
        return Identity(subject, organization, kind)
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise DomainError("unauthenticated", 401) from exc
