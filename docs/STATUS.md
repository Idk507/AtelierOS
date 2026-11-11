# Build status

## Feature-first increment — verification deferred by user

- Sample photo preview supports click/tap placement, keyboard arrow movement, numeric coordinates and clearing annotations. Photo changes reset markers and release preview URLs.
- Handoff drafts provide expandable review summaries from export JSON: status, currentness, measurements/provenance, material evidence/cost, findings, open questions and digests, with refresh/loading/error states.
- No tests, lint, typecheck or browser verification run for this increment, as requested. Existing authentication controls remain. These changes are implemented but unverified.

## 2026-11-11 P07 editable export and release correction

- Added authenticated bounded editable HTML snapshot export and scoped BFF/UI download. Escaped UTF-8 content includes canonical package, manifest and status; HTML is not DOCX. Browser download verification remains open.
- Corrected unsafe completeness assumption: production release now fails closed with professional_completeness_assessment_required after existing authorization/evidence checks. A single measurement cannot establish completeness. Review contract requirements are recorded in P07_PROFESSIONAL_REVIEW.md.
- PASS: 67 PostgreSQL backend tests, Ruff, strict mypy; focused HTML tests and frontend lint/typecheck. No professional acceptance or production release claimed.

## 2026-11-11 P07 review preparation

- PDF now labels component view as unspecified; the domain does not identify front/back. Added long-text, Unicode disclosure and historical export coverage.
- PASS: 65 backend tests, Ruff and mypy. Both synthetic browser journeys passed, including authenticated PDF download, headers and denial after sign-out.
- Professional review checklist: docs/P07_PROFESSIONAL_REVIEW.md. Current release gate requires one measurement but does not establish completeness; acceptable points of measure and tolerances require professional determination. Editable document format, broader visual PDF review and independent architecture/professional acceptance remain open. No live provider or deployment used.

## 2026-11-11 P07 export and browser increment

- Added authenticated PDF draft export and narrowly scoped BFF forwarding with 2 MiB limits. PDF displays revision/package digests, current status, front geometry, evidence and an explicit missing back view. Helvetica output discloses replacement for characters outside Latin-1.
- Synthetic PDF rendered and visually inspected: .local/ui/synthetic-handoff.pdf and synthetic-handoff-1.png/2.png. PDF content/authorization tests pass; proxy download browser check and broader long-text/Unicode layout cases remain open.
- PASS: 64 backend tests, Ruff, mypy, frontend lint/typecheck/build. Two synthetic browser journeys pass, including new sample creation, measurement, reload, patternmaker resolution and mobile overflow check. The synthetic identity has designer and patternmaker roles.
- P07 remains in progress: PDF proxy browser test, completeness criteria, document export scope, professional review and explicit phase gate remain open. No live provider, deployment or professional acceptance claimed.

## 2026-11-11 P07 sampling and release increment

- Implemented Samples studio tab with measurements/provenance, optional rights-confirmed bounded JPEG, normalized coordinate annotation and patternmaker resolutions. Scoped capabilities endpoint controls UI actions; writes retain backend authorization.
- Technical approval audit now binds the exact sample snapshot digest. Release requires that digest plus current revision, independent production actor and fresh purpose approvals. Historical draft packages remain frozen after new findings.
- PASS: full backend suite 63 tests; Ruff; strict mypy; frontend lint/typecheck/build; both existing synthetic browser journeys. Twelve focused sample/release tests cover permission/replay/stale-evidence/blocker/digest cases and concurrent feedback/release.
- Existing browser journeys do not exercise the new Samples panel; dedicated sample interaction/visual checks remain open. Annotation entry uses numeric coordinates. PDF/document export, full technical completeness criteria and professional review remain open. No live provider, deployment or professional acceptance claimed.
- Next exact task: extend the synthetic browser journey for sample creation/resolution and inspect responsive panel, then implement bounded deterministic technical export and its manifest.

## 2026-11-11 P07 backend checkpoint

- Registered sampling routes, aligned readiness and migration tests with schema 0006, and granted SELECT/INSERT on sample_feedback to the runtime role. Formatted unfinished sampling/handoff modules.
- PASS: full backend suite, 58 tests against disposable PostgreSQL. Seven new sample tests cover replay/conflict, permissions, tenant isolation, provenance, stale revision, resolution and invalid evidence. PASS: Ruff and strict mypy before new tests.
- In progress: dedicated release tests and sample-feedback UI. PDF/document export and professional review remain open. No live provider or deployment evidence.

## P06 materials increment

- Imported studio supplier CSVs atomically with dated evidence, currency and measured fabric fields. Added versioned offers, immutable comparisons and a substitution endpoint that accepts only compatible, priced candidates from the current revision.
- The review shows directly and transitively affected artifacts. Commit rechecks offer availability and supersession, preserves locked geometry, and creates an unapproved revision. A fresh JSON handoff draft can include the comparison criteria and estimate after aesthetic approval.
- Verified the INR 2,940.00 reference estimate, a superseded offer rejection, cycle-safe propagation that excludes unrelated artifacts, and an INR 3,006.00 refreshed estimate in the new handoff. Passed 51 backend tests, both browser journeys, frontend lint and production build. Focused materials tests also passed after adding handoff estimate provenance.
- Catalog evidence comes from studio entries and imported files. Live supplier discovery, sample feedback, PDF export and production release remain open. See [materials workflow](MATERIAL_WORKFLOW.md).

## 2026-11-06 multimodal and workflow increment

- P04. Implemented deterministic multimodal fixtures and opt-in Azure REST adapters for chat, vision, image generation and embeddings. The CLI exposes a synthetic smoke test with explicit live charge and image-generation switches. The browser uses the local concept fixture. Real Azure compatibility, image editing and live studio integration remain open.
- P05. Added a two-step local LangGraph workflow, a revision-bound PostgreSQL review checkpoint and a Reviews panel. A different human reviewer can approve a request. Geometry approval creates a patch proposal for separate designer acceptance. Cancellation, tamper rejection, tenant isolation and replay were exercised. Native graph interrupts, scoped memory retrieval and live worker reconciliation remain open.
- Verified the workflow survives a new API instance before review. Both browser journeys passed, including fixture creation, reload and cancellation. Frontend lint, TypeScript and the production build passed. Ruff, mypy and dependency audit passed. Provider verification used simulated responses.
- Operator references are [Azure configuration](AZURE_OPENAI.md) and the [harness contract](HARNESS_CONTRACT.md). No live provider, deployment or customer data was used.

## 2026-11-06 research increment

- Added opt-in Tavily search and capture from operator-approved HTTPS hosts. Search filters duplicate and unsafe links. Capture pins public IPv4 addresses, rejects redirects and stores a revision-bound, reference-only excerpt with a digest and retrieval timestamp.
- Added studio moodboard cards for owned or licensed JPEGs. The board stores resized thumbnails with metadata removed and links the designer's caption to the source.
- Backend verification passed with 41 tests, Ruff, mypy, the P00 validator and the Python dependency audit. Both browser journeys passed, including thumbnail upload and rendering. Frontend lint and TypeScript checks passed. An initial browser run found an ambiguous test selector for the two reuse-rights controls. The test now selects the exact label. The external-provider tests use simulated data. Real Tavily credentials, live smoke testing and production egress review remain open.
- P04 multimodal adapters are the next roadmap phase. P05 orchestration and production release work remain open.

Current milestone is a locally verified studio covering sketch revisions, source-based research, material substitution and JSON review drafts. The production release gate remains open.

## 2026-11-06 studio increment

- P02. The Next.js studio connects the tldraw editor to PostgreSQL through the authenticated FastAPI API. Semantic IDs, hard locks, drawing undo and redo, save and reload, restoration, and revision-specific approval passed browser tests. Synthetic OIDC and same-origin sign-out were verified. Commercial canvas deployment requires a configured tldraw license.
- P03 partial. Designer-supplied text sources and their reuse declarations are stored with immutable digests. A local brief ranks selected excerpts and includes source IDs and digests. Reference-only excerpts cannot be included. Live search, fetching and image moodboards remain open.
- P06 partial. Studio-attested material offers preserve source notes and timestamps. Comparison distinguishes compatible, incompatible and unknown candidates and uses exact decimal costing. An accepted substitution creates an unapproved child. The previous approval, component locks and earlier review package remain linked to their revisions. Automated provider sourcing and a full dependency graph remain open.
- P07 partial. A current aesthetically approved revision can produce a JSON package containing design, material evidence, hash and review status. Changes mark earlier packages as requiring review. Sample feedback, PDF export and production handoff approval remain open.
- P04, P05 and P08 remain open. Multimodal providers, LangGraph orchestration and production operations require separate implementation and verification. No real identity provider, customer data, live provider or deployment was exercised.

Backend checks passed on disposable PostgreSQL with 35 tests, strict mypy and Ruff. Frontend lint, TypeScript and the production build passed. npm audit reports zero known vulnerabilities after applying the compatible patched minimatch version to the lint dependency. P00 and scaffold validators and cross-language hash vectors passed. An interrupted first rerun timed out while PostgreSQL was stopped. A browser run reproduced a sign-out 403, which passed after changing the request to a same-origin fetch. The P00 validator now limits its scan to project contracts and fixtures because dependencies can contain JSON with comments.

The [local studio guide](../apps/web/README.md) documents the synthetic workspace and browser verification. The backend runbook remains in P01_RUNBOOK.md.

`uv run python -m scripts.e2e` passed both browser journeys. The desktop journey verified sketching, locks, reload and restoration, aesthetic approval, cited research, the INR 2,940.00 estimate, and an earlier handoff draft becoming stale after substitution. The responsive journey checked mobile, tablet and wide layouts, cross-origin write rejection and sign-out. Captures are in `.local/ui`.

## Previous status

# Build status (source of truth for continuation)

Current phase: **P01 — backend implemented and locally verified; P02 preparation**
State: **P01 ENGINEERING CHECKS PASS; formal architecture/release review pending**
Application: FastAPI/PostgreSQL canonical-state backend. No designer frontend yet.
Live provider calls: disabled; none made. No deployment or customer data.

## 2026-11-05 — P01 implementation
User directed autonomous continuation. This authorizes implementation against proposed P00 contracts; it does not fabricate independent architecture or professional approval.

Implemented strict Pydantic domain/HTTP commands, fixed RS256 issuer/audience/time validation, database membership/project grants, immutable hashed revisions, selected patch proposals/preview/accept/reject, new hard locks, distinct-admin unlock, purpose-specific human approvals, artifact invalidation metadata, audit/outbox, transactional idempotency, recovery primitives, frozen Alembic migration, operator provisioning, restricted-role SQL template, pinned uv.lock, CI definition and P01_RUNBOOK.md.

PASS: uv run --frozen pytest -q — 32 tests against isolated real PostgreSQL 18 schemas, including an actual Uvicorn loopback process. PASS: Ruff check/format and strict mypy (11 modules). PASS: P00/scaffold validators. PASS: Node cross-language hashing, 3 vectors. PASS: pip-audit — 71 installed packages, zero known vulnerabilities. CI is defined but has not run remotely. One upstream Starlette/httpx test-client deprecation warning remains visible.

Tests-first failures retained in history: missing domain/API/recovery modules; absent hash-vector fixture; project replay returned a revoked create response (fixed with replay reauthorization); restricted-role row locks initially lacked required column privilege (fixed with immutable-ID-only grants and triggers); hard-lock creation endpoint initially absent (implemented). Ruff/mypy setup issues fixed without ignoring checks. An initial pip-audit invocation used an invalid --disable-pip combination; corrected audit completed successfully.

No production readiness claim: real IdP integration, tldraw licensing, browser UX, live providers, P02–P08, independent review and pilot acceptance remain outstanding. Handoff approvals deliberately unavailable until P07.

## Next bounded work
P02 editable designer canvas and persisted semantic patches. User authorized autonomous phase continuation; retain review findings and never mark unverified capability PASS.

## Previous P00 record
# Build status (source of truth for continuation)

Current phase: **P00 — Discovery and architecture contracts**
State: **DESIGN ARTIFACTS PREPARED — AWAITING ARCHITECTURE REVIEW**
Last verified application build: **none**. No operational application exists.
Approved ADRs: none; ADR-001–ADR-006 are PROPOSED.
Last accepted phase gate: none.
Live provider calls: **not authorized; none made**.

## 2026-11-05 — P00 delivery and verification
- Added scope/traceability, consolidated domain/API/event contracts, four JSON schemas and four examples, six proposed ADRs, role/threat supplement, review blockers, P01 bounded slices and task checklist.
- Added three explicitly synthetic scenarios with revision hashes, preserved locks, evidence references, expected approvals and a three-alternative material comparison. Cost oracle: 3.00 m × 1.10 × INR 800.00/m + 200.00 trim + 100.00 other = INR 2940.00; exclusions explicit.
- Updated roadmap navigation, workflow names, phase status, evaluation references and unverified provider capability register. Source proposal copies preserved.
- Established isolated Git root C:/Users/dhanu/Downloads/AtelierOS on codex/p00-contracts; no commits or pushes made. Parent Downloads repository untouched. git check-ignore .env: PASS.
- PASS: python scripts/validate_p00.py — 3 scenarios, 4 API/event examples, 6 proposed ADRs, 8 rejected corruptions. Checks include schemas/formats, hashes, lineage, locked geometry, source links, candidate eligibility and decimal costing. Negative controls are test mutations, not runtime security tests.
- PASS: python .claude/hooks/validate_scaffold.py — scaffold paths, JSON settings and frontmatter.
- PASS: python -m compileall -q scripts — validator syntax.
- NOT VERIFIED: PostgreSQL transactions/authorization, browser interactions, live providers, technical correctness, customer interviews, pilot acceptance and runtime budgets. No network or customer data used.

## Next bounded task and blockers
Human architect reviews P00_REVIEW.md and six ADRs. Product owner confirms purpose-specific roles; security owner resolves runtime identity provider; data owner reviews rights/retention. No named owner sign-off recorded. P01 starts only after the relevant gate and entry decisions are accepted. Live capability uncertainty blocks live integration, not offline fixture work.

## Evidence navigation
- Scope: P00_SCOPE.md; contracts: P00_CONTRACTS.md and contracts/.
- Review: P00_REVIEW.md; security: P00_SECURITY_MATRIX.md; decisions: DECISIONS.md and adr/.
- Scenarios: ../packages/evaluation/p00/; next implementation slices: P01_TASKS.md.

## History
Before this increment: P00 NOT STARTED; no approved ADR, application build or validated gate. Prior scaffold validation passed. Preserve future failed checks and unresolved blockers rather than replacing them with successful claims.
