# AtelierOS web studio

The studio connects the Next.js canvas to the FastAPI garment API. It supports project and garment creation, semantic sketch editing, revision history, aesthetic approval, cited research, material estimates and technical review drafts.

## Open an isolated local studio

Run from the repository root in PowerShell.

```powershell
uv sync --frozen --no-build
.\scripts\start-test-postgres.ps1
npm --prefix apps/web ci --ignore-scripts
npm --prefix apps/web run assets
uv run --frozen python -m scripts.e2e --serve
```

Open the loopback URL printed by the command and choose **Enter your studio**. This mode uses an isolated PostgreSQL schema and a synthetic issuer. Enter synthetic data only. Ctrl+C stops the workspace and removes its temporary schema.

Run `uv run --frozen python -m scripts.e2e` to exercise the browser journeys. The script uses local Edge on Windows when available. On other hosts install the Playwright Chromium browser first. Screenshots appear in `.local/ui`.

## Production configuration

The web server needs a configured OIDC issuer, registered callback `/auth/callback`, a 32-byte base64 `ATELIER_SESSION_KEY`, trusted `ATELIER_WEB_ORIGIN`, and `ATELIER_API_BASE_URL`. Set `ATELIER_OIDC_CLIENT_ID`, `ATELIER_OIDC_AUTHORIZATION_ENDPOINT`, and `ATELIER_OIDC_TOKEN_ENDPOINT` to the registered client and issuer endpoints. Confidential clients using `client_secret_post` can set `ATELIER_OIDC_CLIENT_SECRET`. The web and API processes use matching `ATELIER_JWT_ISSUER`, `ATELIER_JWT_AUDIENCE`, and `ATELIER_JWT_PUBLIC_KEY` values. Follow the [backend runbook](../../docs/P01_RUNBOOK.md) for provisioning and migration.

Set `NEXT_PUBLIC_TLDRAW_LICENSE_KEY` at build time to enable the production editor. The local editor retains the SDK watermark. [tldraw licensing](https://tldraw.dev/sdk-features/license-key)

The research board uses designer-supplied text, deterministic excerpt ranking and studio-owned or licensed moodboard images. An operator can enable web search and source capture as described in the [research workflow](../../docs/RESEARCH_WORKFLOW.md). Materials use studio-attested offers and exact decimal estimates. JSON handoffs are revision-bound drafts for patternmaker review. Live-provider verification, multimodal generation, sample feedback and production export approval remain outstanding.
