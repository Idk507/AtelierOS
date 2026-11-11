# P01 backend runbook

This is the tested canonical-state backend, not a released fashion studio. Canvas,
providers, orchestrated workflows and technical exports belong to later phases.
No real customer data or paid inference is needed for P01.

## Reproducible local verification (Windows)

Prerequisites: Python 3.12, uv 0.11.32, PostgreSQL 18 and Node.js (hash check only).
From the repository root:

```powershell
uv sync --frozen --no-build
.\scripts\start-test-postgres.ps1
uv run --frozen pytest -q
uv run --frozen ruff check apps/api packages/domain tests migrations
uv run --frozen ruff format --check apps/api packages/domain tests migrations
uv run --frozen mypy
node scripts/verify-hashes.mjs
uv run --frozen python scripts/validate_p00.py
uv run --frozen python .claude/hooks/validate_scaffold.py
uv run --frozen pip-audit
```

The test cluster uses trust authentication on 127.0.0.1:55439, separate from any
existing PostgreSQL installation/service. It is disposable and must contain only
synthetic data. Tests create and remove uniquely named schemas; they refuse a
database name outside `atelier_test*`. To use a different disposable PostgreSQL
instance set `ATELIER_TEST_DATABASE_URL`. No SQLite fallback or skipped DB tests.
Stop the local cluster when finished:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D .local/postgres-test -m fast -w stop
```

## Start an explicitly configured API

Runtime reads process environment, not the private `.env` file. Set:

- `ATELIER_DATABASE_URL`: PostgreSQL psycopg URL; production requires TLS,
  restricted database login and infrastructure-managed encryption/backups.
- `ATELIER_JWT_ISSUER`, `ATELIER_JWT_AUDIENCE`: the trusted issuer and API audience.
- `ATELIER_JWT_PUBLIC_KEY`: PEM RSA public key (at least 2048 bits), never private key.
- `ATELIER_ALLOWED_HOSTS`: JSON list of authorized hosts; defaults to loopback.

Use the migration owner on an explicitly selected database:

```powershell
uv run --frozen alembic upgrade head
uv run --frozen python -m apps.api.manage --subject '<issuer-subject>' --roles designer --organization-name 'Studio'
```

Provisioning prints organization/user IDs, never a token or key. Provision supporting
roles with `--organization-id` and `--project-id`; existing subject membership roles
are explicitly replaced by the supplied list. The single configured issuer owns
the subject namespace. Provisioning is an operator action, not an HTTP endpoint.

Configure the issuer to sign RS256 bearer tokens with `sub`, `iss`, `aud`, `exp`,
`iat`, `nbf`, `organization_id` and `principal_type` (`human` or `service`). Roles in
tokens are ignored: membership and project grants come from PostgreSQL. Configure
the issuer so a service principal cannot mint a human identity. There is no dev
header bypass, shared-secret token minting endpoint or implicit administrator.
Configure and test the chosen identity provider before real-user deployment.
Key rotation in P01 uses a coordinated public-key update and process restart;
overlapping JWKS rotation is not yet implemented.

Before starting the server switch to a restricted HTTP database login. Review
`infra/p01_runtime_permissions.sql` with the DBA; it is a template for the `public`
schema, does not create a login/password, and is not run automatically. Schema
owners and migration credentials must not be used by the HTTP process.

```powershell
uv run --frozen uvicorn apps.api.main:build_app --factory --host 127.0.0.1 --port 8000
```

`/docs` and `/openapi.json` describe implemented endpoints. `/health/live` is process
liveness; `/health/ready` verifies migrated schema version. Deploy behind TLS with
request timeouts, header limits, connection limits and ingress rate limiting. The
API bounds bodies at 1 MiB, validates host names, and returns no-store responses.
Logs contain request IDs, method, status and duration; no bearer tokens or bodies.

## Transactions, retries and recovery

Every POST needs `Idempotency-Key`. Reuse the exact key and body after a network
failure; do not generate a new key until the original result is reconciled.
Same actor/organization/key with another route or body is a 409. Access is rechecked
before returning original responses. Membership and project grants are locked
against revocation while a request runs; garment commands serialize by row lock.
Stale edits/approvals fail 409. An accepted patch creates an unapproved child,
retains historical approvals and invalidates affected artifacts.

Geometry operations supported in P01: create/update/delete. A `garment` target may
update only material_id; this records intent and does not verify a catalog offer.
Move, transform and group tools are P02. Unlock requires a distinct org-admin
actor, creates a child with changed lock only, and grants no garment approval.
Aesthetic and technical approvals are separate. Handoff approval fails closed with
422 until P07 provides reviewed technical artifacts and export validation.

Internal outbox delivery supports one logical dispatcher with parallel workers
using SKIP LOCKED. Its callback may perform only database effects in the same
transaction; receipts deduplicate replay. External calls never run in that
transaction. `reserve_attempt` commits pending intent before a provider call;
repeated pending admission returns `reconcile`, not permission to call again.
`finish_attempt` records a reconciled terminal outcome. No external connector or
background provider runner is enabled in P01; P05 adds bounded retry/cancellation
and per-action authorization. `attempts` currently counts committed deliveries,
not failed transactions. Dispatcher dead-letter policy remains P05 work.

## Migrations and rollback

The initial migration is frozen SQL with tenant composite foreign keys and
append-only revision, approval, audit and receipt triggers. Upgrade/downgrade/
upgrade is tested in disposable schemas. **Downgrade drops application data.**
Run `uv run alembic downgrade base` only against an explicitly disposable database.
For live deployments take a verified backup and prefer forward migrations plus
application rollback. Never run startup migrations in HTTP workers.

## Evidence limits

Passing local tests establishes P01 behavior, not production launch readiness.
Remaining release gates include real IdP integration, independently reviewed
least-privilege deployment, retention/deletion, load tests, external telemetry,
designer acceptance, browser UX and P02–P08 functionality. CI workflow is supplied
but remote CI has not run until pushed to a configured remote.

Implementation references: [SQLAlchemy sessions](https://docs.sqlalchemy.org/en/20/orm/session_api.html),
[PyJWT validation](https://pyjwt.readthedocs.io/en/latest/api.html),
[FastAPI bearer authentication](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
