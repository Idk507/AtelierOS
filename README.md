# AtelierOS — Claude Code implementation scaffold

This archive is a **plan, guardrail, and development configuration**, not a finished app. It carries the source proposal and a phase-gated scaffold for building the platform with Claude Code and Azure OpenAI as the runtime provider.

## Setup (Windows PowerShell)

```powershell
Expand-Archive .\atelieros_claude_starter.zip -DestinationPath .\atelieros
cd .\atelieros
Copy-Item .env.example .env
# Edit .env locally; never paste or commit keys.
python .claude/hooks/validate_scaffold.py
claude
```

Start with `/start-phase 0`; continue with `/start-phase 1` only after the previous gate is reviewed. Commands are skill entry points under `.claude/skills`, surfaced as slash commands in supported Claude Code versions. `/project-status`, `/review-gate`, `/architecture-decision`, `/security-audit`, `/eval-run` are provided. Follow `docs/BUILD_PLAN.md` for phase ordering.

The `.claude` folder contains **developer-side Claude Code configuration**. The application's own harness will be implemented under `packages/harness/` and is not itself made production-ready by this scaffold. Azure deployment names are required; do not assume an image generation deployment is available.

## Files that matter first
`CLAUDE.md` (short durable instructions), `docs/STATUS.md` (current gate), `docs/BUILD_PLAN.md` (planned sequence), `docs/ARCHITECTURE.md` (system contracts), `docs/SECURITY.md` (threat model), `docs/EVALS.md` (benchmarks), and `docs/phases/P00.md` (first increment). The full source proposal is in `docs/product` for selective lookup.

## Design constraints
No full repository implementation in one prompt, no hidden fake integration, no auto-approval, no image/technical equivalence claims, no autonomous external purchases. Hooks are defense-in-depth only and do not replace environment isolation or backend permissions.

## P00 review package

Design artifacts prepared; architecture review remains pending. See [scope](docs/P00_SCOPE.md), [contracts](docs/P00_CONTRACTS.md), [review checklist](docs/P00_REVIEW.md) and [P01 backlog](docs/P01_TASKS.md). Six ADRs are PROPOSED; fixtures are synthetic.

Offline checks with requirements-p00.txt dependencies installed:
```powershell
python scripts/validate_p00.py
python .claude/hooks/validate_scaffold.py
```
These checks do not verify database transactions, browser behavior, live inference or professional acceptance. No credentials needed.

## Implemented backend
P01 now provides the canonical-state API with real PostgreSQL acceptance tests. See [P01 runbook](docs/P01_RUNBOOK.md) and [current status](docs/STATUS.md). The original scaffold description above is historical; the full fashion application is not yet released.
