"""Fail-closed environment configuration; never read the project's private .env."""

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Public-key token verification and PostgreSQL connectivity configuration."""

    model_config = SettingsConfigDict(env_prefix="ATELIER_", extra="ignore")
    database_url: str = Field(repr=False)
    jwt_public_key: str
    jwt_issuer: str = Field(min_length=1)
    jwt_audience: str = Field(min_length=1)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    research_live_enabled: bool = False
    tavily_api_key: SecretStr | None = None
    research_source_hosts: list[str] = Field(default_factory=list)

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        """SQLite is not an authorization or transaction acceptance backend."""
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL with psycopg is required")
        return value

    @field_validator("jwt_public_key")
    @classmethod
    def public_key_only(cls, value: str) -> str:
        """Reject symmetric secrets, absent keys and accidental private keys."""
        if "BEGIN PUBLIC KEY" not in value or "PRIVATE" in value:
            raise ValueError("An RSA public verification key is required")
        key = load_pem_public_key(value.encode())
        if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
            raise ValueError("RSA verification keys must be at least 2048 bits")
        return value
