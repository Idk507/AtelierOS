# AtelierOS — Claude Code operating contract

You are implementing an AI-native, designer-controlled fashion product development system. Product source of truth: `docs/product/AtelierOS_3_0_Complete_Solution_Proposal.md`; current execution plan: `docs/BUILD_PLAN.md`; phase ledger: `docs/STATUS.md`. Do not reread the full proposal on every turn. Open only relevant headings and the current phase contract.

## Product invariant
The Digital Garment Twin (DGT) is the canonical, organization-scoped, versioned record for garment design intent, structured components, locks, materials, evidence, approvals and dependent artifacts. LLM outputs and generated images are proposals, never approved design state or evidence of physical fit. All sensitive writes require transactionally enforced authorization and concurrency control.

## Engineering workflow
1. At session start, read `docs/STATUS.md`, the active `docs/phases/P*.md`, and only files required for the task. State the exact current gate and the intended edits.
2. Implement one narrow vertical slice per request. Before modifying code, give a brief change plan and expected tests. Do not implement later phases speculatively.
3. Prefer existing utilities; avoid duplicative context dumps, unnecessary agents, and repository-wide reading. Use skills only when task-specific; subagents return concise findings only.
4. No credentials, test data uploads, deployment, destructive DB commands, migrations of non-disposable data, or live supplier messaging without explicit approval. Never silently enable external browsing or image-generation spending.
5. Fail closed on missing organization scope, wrong revision, unverified catalog fields, broken citations, invalid tool payload, or an incomplete human approval.
6. Add type hints, docstrings and comprehensive error handling to Python code; tests for state changes, permissions, idempotency, and negative cases. Prefer deterministic validators over LLM judgment.
7. At the end, run relevant checks; report PASS/FAIL/SKIPPED with evidence. Update `docs/STATUS.md` with tested results and next gate. Stop and request architectural review at each phase gate, not every file.

## Stack
Python 3.12 / FastAPI / Pydantic v2 / SQLAlchemy 2 / PostgreSQL + pgvector / LangGraph; TypeScript React/Next.js and tldraw canvas; Azure OpenAI deployments via provider adapters. Use pytest, Ruff, mypy; frontend TypeScript strict, ESLint, Playwright. No Docker, Redis, or mandatory cloud resources in the local MVP. Use local SQLite only for isolated protocol demos, not as a substitute for PostgreSQL authorization/locking acceptance tests.

## Azure OpenAI
Azure OpenAI is the **runtime application LLM/image/embedding provider**. Claude Code's own model/billing/auth is separate; Azure credentials do not change Claude Code inference provider. Use `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_IMAGE_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`; never expose values in logs. Use deployment identifiers, not assumed model names. Do not assume image deployment/region access exists. Implement an offline mock provider first.

## Directories
`apps/web` designer UI; `apps/api` FastAPI; `packages/domain` DGT and contracts; `packages/harness` runtime controls; `packages/agents` specialized domain agents; `packages/integrations` Azure/web search/suppliers; `packages/evaluation` curated evaluation data; `infra` deployment manifests; `docs/` design records and execution history.

## Commands
Use `.claude/skills/phase-implementation/SKILL.md` for build phases, `.claude/skills/azure-openai/SKILL.md` for model adapter work and `.claude/skills/verification-gates/SKILL.md` for acceptance. Project hook scripts are not a security boundary; enforce authorization in application code and trusted environment policy.
