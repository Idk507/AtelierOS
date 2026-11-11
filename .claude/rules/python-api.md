---
paths:
  - "apps/api/**/*.py"
  - "packages/**/*.py"
---
All service boundary methods use explicit tenant/auth context. Pydantic validates tool and HTTP DTOs; no untrusted dict directly reaches a tool. SQL writes preserve immutability, transactional approvals, idempotency and audit events. Type hints and useful docstrings required. Handle timeouts, provider failure and malformed model outputs explicitly. No network in unit tests. No raw secrets or private images in logs.
