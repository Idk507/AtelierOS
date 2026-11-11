# AtelierOS API

P01 FastAPI/PostgreSQL backend implemented. See [runbook](../../docs/P01_RUNBOOK.md) for locked setup, authentication, migration, provisioning and tests. Start with `uv run uvicorn apps.api.main:build_app --factory`. Runtime settings must be explicit; no private .env auto-loading or authentication bypass.
