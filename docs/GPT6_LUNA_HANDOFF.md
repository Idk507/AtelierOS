# AtelierOS: implementation handoff to GPT-6 Luna

Prepared: 2026-11-11. This is a continuation guide, not architecture approval or evidence that the current working tree passes tests.

## 1. Assignment and starting state

Continue the existing designer-controlled fashion development workspace. Finish the unfinished P07 technical handoff and sampling work first. Prepare P08 only after the P07 engineering evidence is complete and its review gate is resolved. Preserve the P00–P08 sequence in `docs/BUILD_PLAN.md`; P09 is separately gated expansion.

Workspace: `C:\Users\dhanu\Downloads\AtelierOS`. Observed branch: `codex/p00-contracts`. The project has its own Git repository, but its files are still untracked and there are no implementation commits. Recheck this at session start. An empty tracked diff does not mean there is no existing work. Never use `git clean`, reset, checkout replacement files, or regenerate the application to establish a baseline.

Implementation was paused specifically to prepare this handoff. Do not assume the latest files were verified. In particular, the last recorded green checks preceded the partial P07 edits.

### Document authority

1. Current user instructions define authorized scope.
2. `CLAUDE.md` contains the repository operating contract; it applies to a successor coding agent too.
3. `docs/product/AtelierOS_3_0_Complete_Solution_Proposal.md` is product vision.
4. `docs/BUILD_PLAN.md` defines engineering sequence; `docs/phases/P00.md` through `P08.md` define gates.
5. `docs/STATUS.md` records executed evidence chronologically, with newest entries first. Older embedded status sections are historical.
6. Contracts, ADRs, code and tests must be reconciled when they disagree. Do not silently pick the most convenient interpretation.

The six existing ADRs remain proposed until reviewed. `docs/phases/P07.md` currently says NOT STARTED although partial P07 code exists. The newest status entry is P06 and does not describe the unfinished P07 edits. Reconcile these records when actual implementation/check results are available; do not retroactively invent passing evidence.

## 2. Product and invariants

The initial audience is boutique occasionwear designers, supported by client reviewers, patternmakers and production staff. The three core journeys are **research-to-design**, **material-substitution**, and **sample-feedback**.

The Digital Garment Twin is canonical state. It carries stable garment/component identities, immutable revisions, locks, materials, provenance, approvals and dependent artifacts. Preserve these rules throughout every change:

- Derive organization scope from authenticated context and authoritative database membership/project grants. Never trust a payload's organization or role as authorization.
- A model output is a proposal. Proposal generation, preview, draft acceptance and purpose-specific human approval are different operations.
- State-changing commands require the established base-revision and idempotency contracts. Replays must reauthorize; conflicting reuse must fail.
- Commit a new immutable revision with concurrency control. Do not overwrite an approved revision or silently move an approval to a child.
- Locks survive edits and substitutions, including ancestor effects. An edit cannot implicitly unlock a component. Keep the authorized separate unlock workflow.
- Bind approvals to human actor, organization, role, revision hash and purpose. Aesthetic, technical and handoff decisions are distinct.
- Scope provenance, uploads, findings, exports and audit data to their garment and organization. Return safe errors without leaking another tenant's existence.
- Use exact decimal costing. Unknown evidence, incompatible properties and currency mismatches must remain visible and must not become eligible by default.
- Invalidate dependent artifacts when their inputs change. Historical packages remain identifiable as historical; stale exports must never appear current.
- Synthetic fixtures, studio attestations, simulated provider responses, live provider results and professional review are separate evidence categories.
- Technical documents remain drafts until the specified human gate. Generated flats do not establish physical fit, validated patterns or manufacturability.

## 3. What exists and what remains

The table describes recorded local verification, not a fresh execution on this handoff date.

| Area | Existing implementation/evidence | Remaining work |
| --- | --- | --- |
| P00 | Scope/contracts, synthetic fixtures, six proposed ADRs, scaffold/contract validators | Independent architecture acceptance remains separate |
| P01 | PostgreSQL tenant access, immutable revisions, locks, approvals, audit/outbox, idempotency and restricted-role tests | Production operational evidence and external review |
| P02 | Next.js authenticated studio, semantic tldraw editing, history, preview/accept, reload, locks and aesthetic approval | Real IdP verification and production canvas license |
| P03 | Cited text research, rights-aware JPEG moodboards, opt-in bounded Tavily capture adapter | Live Tavily compatibility/egress verification |
| P04 | Deterministic multimodal fixtures and opt-in Azure REST adapters | Real deployment compatibility, image editing and live studio integration |
| P05 | Two-node local LangGraph workflow and application-owned durable human-review checkpoint | Native graph interruption, scoped memory and live worker recovery/budgets |
| P06 | Studio offers/CSV import, immutable comparisons, compatible substitution, exact cost and artifact impact | Live supplier discovery/inventory verification |
| P07 | Existing JSON handoff drafts; new incomplete sampling/release code | Integrate and test backend, sample UI, PDF/document export and professional review |
| P08 | Proposed phase contract and some existing security foundations | Pilot hardening, measured operations, staging/release evidence |

Latest recorded broad result: **51 backend tests**, both browser journeys, frontend lint and production build passed during P06. Focused material tests also passed after estimate provenance was added. These results do not validate the subsequent P07 working tree. No live provider calls, production deployment or customer pilot has been verified. Remote CI is defined but has not been demonstrated running.

## 4. Read in this order

Keep context small. Read the following, then only the files needed for the current slice:

1. `CLAUDE.md`, this guide, latest entries in `docs/STATUS.md`.
2. `docs/BUILD_PLAN.md`, `docs/phases/P07.md`, `docs/P00_CONTRACTS.md`.
3. `.claude/skills/phase-implementation/SKILL.md` and `.claude/skills/verification-gates/SKILL.md`.
4. `docs/SECURITY.md`, `docs/P00_SECURITY_MATRIX.md`, `docs/EVALS.md` and relevant ADRs.
5. `apps/api/handoff.py`, `apps/api/samples.py`, `apps/api/models.py`, `migrations/versions/0006_sampling.py`.
6. Relevant portions of `apps/api/main.py`, `service.py`, `dto.py`, `infra/p01_runtime_permissions.sql`, and existing handoff tests.
7. For UI/export work: `apps/web/src/components/HandoffDrafts.tsx`, `Studio.tsx`, `apps/web/src/lib/api.ts`, `types.ts`, and `apps/web/src/app/api/backend/[...path]/route.ts`.

Do not read `.env`, dump process environment, print tokens, or paste private configuration into the chat. Use `.env.example` for variable names. Application configuration reads process variables; do not silently add automatic `.env` loading.

### Code map

| Path | Responsibility |
| --- | --- |
| `packages/domain/design.py` | Pure canonical design validation, patches and content hashes |
| `apps/api/auth.py`, `config.py`, `main.py` | Identity, configuration, HTTP routing and request boundary |
| `apps/api/service.py`, `models.py`, `dto.py` | Transactional domain commands, records and strict contracts |
| `apps/api/recovery.py` | Outbox/attempt recovery primitives |
| `apps/api/research.py`, `web_research.py`, `research_images.py` | Research evidence, bounded retrieval and sanitized images |
| `apps/api/materials.py` | Offers, comparisons, deterministic estimates and substitution |
| `apps/api/multimodal.py`, `workflows.py` | Provider adapters and bounded local review workflow |
| `apps/api/handoff.py`, `samples.py` | Handoff packages and unfinished sample feedback/release work |
| `migrations/versions`, `infra/p01_runtime_permissions.sql` | Schema history and runtime database privileges |
| `apps/web/src/components`, `apps/web/src/lib` | Studio interfaces and typed API clients |
| `tests`, `scripts/e2e.py` | Backend/permission tests and synthetic full-browser journeys |
| `docs/P01_RUNBOOK.md`, `apps/web/README.md` | Local backend and studio operation |

## 5. First session: establish the real baseline

1. Confirm workspace and Git root/branch/status. Preserve existing files, including untracked ones.
2. Inspect relevant code and document the current P07 boundary before edits.
3. Sync locked dependencies; start the dedicated synthetic test PostgreSQL instance.
4. Run focused existing tests and static checks. Record failures caused by the incomplete work. Fix causes; do not suppress checks or weaken expectations.
5. State one bounded slice and its acceptance tests. Complete it before expanding scope.

PowerShell from the repository root:

```powershell
Get-Location
git rev-parse --show-toplevel
git branch --show-current
git status --short
uv sync --frozen --no-build
.\scripts\start-test-postgres.ps1
uv run --frozen pytest -q tests/test_materials.py tests/test_recovery.py tests/test_runtime_permissions.py
uv run --frozen ruff check apps/api packages/domain tests migrations scripts/azure_smoke.py
uv run --frozen mypy
```

Python is 3.12, managed by uv and `uv.lock`. Node was available at `C:\Program Files\nodejs\node.exe`; use the repository's package lock. Do not opportunistically upgrade frameworks.

The disposable PostgreSQL 18 cluster lives under `.local/postgres-test`, listens on loopback port 55439 and uses database/user `atelier_test`. It is trust-authenticated for synthetic local testing only. Tests create isolated schemas and reject non-test database names. Never run destructive test/schema commands against a user's existing database, substitute SQLite for transaction tests, or expose this cluster on the network. `ATELIER_TEST_DATABASE_URL` can select an approved disposable test instance.

## 6. P07: exact continuation sequence

### Slice A — integrate and verify the partial backend

Current unfinished changes to inspect:

- `0006_sampling.py` adds append-only `sample_feedback` and nullable `artifacts.review_payload`.
- `models.py` adds the artifact snapshot field.
- `samples.py` defines strict measurements, normalized photo annotations, rights declarations, findings and resolution records. Finding creation is intended for designer/patternmaker/production; resolution is intended for patternmaker. Treat this as proposed policy requiring contract/test agreement.
- `handoff.py` freezes sample evidence, builds measurement/BOM fields and adds a production release operation with current approval/evidence checks.
- ReportLab is newly added; pypdf, PyMuPDF and ReportLab types were added to development dependencies. These additions have not yet passed the full dependency/static/runtime checks.

Known integration gaps as observed at handoff:

1. `main.py` has not registered the sample router.
2. Readiness still expects migration `0005`; inspect `tests/test_recovery.py` for the same literal and align both with the actual head `0006`.
3. Runtime-role SQL has not been extended for sample records. Do not solve this by granting unrestricted writes or using the owner role in application tests.
4. No dedicated sample tests or sample UI exist yet.
5. No PDF renderer, PDF route or browser PDF forwarding exists yet.
6. New P07 code has not been formatted, type-checked or functionally verified.

Implement contract tests before wiring behavior. Review these correctness questions explicitly:

- Do feedback creation, resolution and release serialize on the same garment scope so a concurrent finding cannot race past a release check?
- Is an approval bound to the exact evidence/package being released? Timestamp ordering alone must not be accepted as proof if it permits a race or stale evidence.
- Does any new finding/resolution invalidate the release status without rewriting the historical package?
- Is a single measurement sufficient for the declared purpose? Define required points of measure/open questions; do not label a technically incomplete pack production-ready.
- Are reviewer roles, distinct-actor rules and handoff purpose enforced on every write and replay?
- Are historical pre-0006 packages readable without changing their established digest? Nullable legacy evidence must not qualify for a new release by default.
- Are images, lists, encoded payloads and PDF generation bounded? Never retain original EXIF/location metadata.

Acceptance evidence for this slice:

| Case | Expected result |
| --- | --- |
| Authorized finding on current revision | Immutable finding with provenance and audit |
| Foreign tenant/project, service actor or unauthorized role | Denied with no side effect |
| Stale base revision or wrong component | Rejected |
| Conflicting idempotency reuse | Rejected; identical authorized replay has one effect |
| Photo without rights, malformed JPEG, excessive size or invalid annotation | Rejected |
| Authorized finding resolution | Append-only resolution; original finding unchanged |
| Release with missing/stale approvals or unresolved blocking finding | Rejected |
| Release with wrong digest, stale revision or changed evidence | Rejected |
| Concurrent release and new feedback | One consistent serialized outcome; no falsely current release |
| New evidence after release | Prior package remains historical; active release requires review |
| Restricted runtime database role | All supported operations work; forbidden direct updates fail |

Verify migration upgrade and supported downgrade behavior only in disposable schemas. Never edit an already deployed historical migration to hide incompatibility. Update phase/status records only with executed results.

### Slice B — sample-feedback interface

1. Add strict TypeScript request/response types matching actual backend DTOs.
2. Build a revision-aware sample panel using existing API/session/error patterns.
3. Support sample label, component selection, observation, severity, measured value/unit/source, optional rights-confirmed JPEG and normalized annotation.
4. Show author, revision, measurement provenance, open findings and resolution history. Only show allowed actions; backend remains authoritative.
5. Handle pending, validation, forbidden and stale-revision states accessibly. Refresh dependent handoff status after mutations.
6. Extend the synthetic browser journey through finding creation, reload, authorized resolution and handoff invalidation. Check desktop and mobile layouts and keyboard operation.

Do not infer measurements from an image or silently carry old-revision feedback into a new revision as current evidence. Any carry-forward needs an explicit attributed review contract.

### Slice C — deterministic technical export

1. Define an export manifest linking garment, organization, revision ID/hash, artifact ID, canonical package digest, evidence snapshot and review status. Define any binary digest without a self-referential hash.
2. Render the actual semantic front geometry. Render a back flat only when backed by explicit data; otherwise show a missing-view/open-question placeholder.
3. Include attributed measurements, BOM/material evidence, deterministic cost when available, sample findings, unresolved questions and purpose-specific approvals.
4. Clearly mark draft, stale/review-required and released states. Do not present a stale historical artifact as the current garment specification.
5. Escape all user text before ReportLab markup processing; bound text, images, rows, pages and output bytes. No external font/image fetches during rendering. Choose and test a licensed font strategy for supported scripts or expose unsupported character handling explicitly.
6. Add an authenticated PDF endpoint reusing canonical package assembly. Keep JSON exports compatible. Use safe filenames, correct content type and private/no-store behavior appropriate to sensitive documents.
7. Extend the Next.js BFF's current JSON-only response handling narrowly for the authorized PDF route. Preserve session, tenant, size and error controls; do not create a general-purpose binary proxy.
8. Add the UI download action and revision/status context.
9. Read the available PDF skill before authoring an actual PDF artifact and follow its marker/render/inspection requirements. At handoff, no PDF marker had been run and no PDF artifact had been generated.

Test JSON digest stability, legacy package reads, PDF text/status/manifest contents, malformed markup, Unicode, long text, page breaks, photo limits, tenant denial, stale exports and deterministic semantic content. Byte-for-byte PDF equality requires controlling timestamps/metadata; document the intended guarantee. Render every representative page to images and inspect legibility, clipping and layout. A successful HTTP response alone is insufficient.

`pdftoppm` was not found on PATH previously; confirm available render tools. PyMuPDF was newly installed but its rendering API and dependency footprint remain unverified.

### Slice D — close the P07 engineering gate

Run the full checks below, review security-sensitive changes, update contracts and phase records, and save synthetic example exports/screenshots with provenance. Check whether the phase's document-export requirement needs a separate DOCX artifact; do not silently mark it delivered by a PDF alone. Record any agreed scope deferral explicitly.

Prepare a professional review package: input revision/hash, views and missing views, measurement sources, BOM unknowns, findings/resolutions, approval chain, stale-export demonstration and limitations. A patternmaker/production professional must assess technical adequacy. Do not impersonate that reviewer or mark the professional gate accepted from automated tests.

## 7. P08 and earlier unfinished capabilities

After P07 review, use bounded slices in this order. The exact implementation should follow measured findings and the existing contracts.

1. **Release-gap inventory:** reconcile P00–P07 requirements against code/test evidence; retain deferred live-provider and orchestration gaps as explicit blockers where required.
2. **Identity and authorization:** verify the existing OIDC/PKCE flow with the chosen real IdP in an approved environment; test role revocation, cookie/origin controls, logout, tenant boundaries and restricted DB privileges. Never enable a development auth bypass.
3. **Data lifecycle:** decide retention/deletion for photos, source snapshots, exports, identity and audit records. Reconcile deletion obligations with append-only evidence using an approved design; do not casually delete audit history or promise complete deletion without proof.
4. **Work and cost bounds:** enforce appropriate per-user/organization quotas across processes, bounded payload/output sizes, provider timeouts, cancellation and durable attempt accounting. Unknown provider cost is unknown, not zero.
5. **Recovery:** connect external effects to the durable attempt journal. Test crash/restart, duplicate delivery and ambiguous provider outcomes; reconcile pending effects rather than blindly retrying them. Existing local review persistence is not proof of native LangGraph interruption or live-worker recovery.
6. **Observability:** structured redacted logs, correlation/job/revision identifiers, operational health and actionable metrics. Do not log tokens, raw private prompts/photos or provider error bodies containing secrets.
7. **Operational rehearsals:** backup/restore with isolated synthetic data, migration/rollback rehearsal, secret rotation procedure, incident response, dependency/license inventory and reproducible locked builds.
8. **Evaluation:** all three journeys; cross-tenant denial; concurrent edits with one winner; stale approvals; idempotent replay; preserved locks; exact costing; stale exports; prompt injection; SSRF; interrupted-job recovery. Add measured performance thresholds based on the pilot workload and document results.
9. **Staging preparation:** prepare deployment manifests/runbooks against the selected environment, TLS/egress/storage settings, monitoring and rollback. Production tldraw usage requires the appropriate license; do not remove its watermark to bypass licensing.
10. **Pilot/release gate:** consented users/data, designer acceptance, professional evidence, security findings addressed and explicit deployment approval. Deployment is not authorized merely by a request for local continuation.

Earlier unfinished work must not disappear from reporting:

- **P03:** real Tavily smoke/egress behavior is unverified.
- **P04:** Azure chat/vision/image/embedding adapters were tested with simulated responses. Actual deployment identifiers, capabilities, region access and live image editing remain unverified. `scripts/azure_smoke.py` has an offline mode; live calls require explicit charge authorization, and live image generation has a separate switch.
- **P05:** current LangGraph flow is two bounded local steps with an application-owned PostgreSQL review checkpoint. Native graph interrupt/checkpoint behavior, scoped retrieval memory and live tool worker enforcement need separate implementation/evidence.
- **P06:** offers are synthetic fixtures or studio attestations, not verified real-time supplier inventory. Live supplier discovery is open.

Do not implement P09 collections, messaging, CAD, textile repeats or sustainability claims opportunistically.

## 8. Verification commands

Run focused tests during each slice. Before declaring an engineering increment green, run the relevant full gate and report actual results. These commands are instructions for future execution; they were not rerun while writing this document.

```powershell
# Backend: repository root, dedicated test PostgreSQL running
uv run --frozen pytest -q
uv run --frozen ruff check apps/api packages/domain tests migrations scripts/azure_smoke.py
uv run --frozen ruff format --check apps/api packages/domain tests migrations
uv run --frozen mypy
uv run --frozen python scripts/validate_p00.py
uv run --frozen python .claude/hooks/validate_scaffold.py
& 'C:\Program Files\nodejs\node.exe' scripts/verify-hashes.mjs
uv run --frozen pip-audit

# Frontend
$env:PATH = 'C:\Program Files\nodejs;' + $env:PATH
npm.cmd --prefix apps/web ci --ignore-scripts
npm.cmd --prefix apps/web run assets
npm.cmd --prefix apps/web run lint
npm.cmd --prefix apps/web run typecheck
$env:NEXT_TELEMETRY_DISABLED = '1'
npm.cmd --prefix apps/web run build
npm.cmd --prefix apps/web audit

# Integrated synthetic browser journeys
uv run --frozen python -m scripts.e2e
```

The E2E harness starts an isolated schema, real API, synthetic OIDC issuer and browser-backed studio, then cleans up its processes/schema. It is synthetic evidence, not a real IdP or customer pilot. Screenshots are stored under `.local/ui`. See `apps/web/README.md` for demo mode and prerequisites; `--serve` keeps a synthetic workspace alive until interrupted and is not production hosting.

If a prerequisite is absent, report SKIPPED/BLOCKED with the reason. Do not replace PostgreSQL/browser tests with mocks and report the original gate as passed. If a check fails, preserve the failure, fix the cause and rerun the relevant scope. Do not lower strict typing, remove negative assertions or add broad ignores to obtain green output.

## 9. Working protocol for a smaller-context model

For each slice:

1. Read current state and only relevant contracts/files.
2. State the behavior to implement, affected files and meaningful tests.
3. Write correctness-critical tests; implement the smallest complete vertical slice using existing helpers.
4. Review authorization, transaction boundaries, concurrency, provenance and resource bounds.
5. Run focused checks, then the appropriate full gate when the slice is ready.
6. Update `docs/STATUS.md` and the current phase with factual results, unresolved risks and one exact next task.
7. At context limits, leave a checkpoint listing modified files, commands/results, remaining failures and the next operation. Never restart the project from scratch after compaction.

Routine reversible local implementation and verification are already authorized. Continue those autonomously. For an actual external permission, professional/architecture gate, paid call, deployment or non-disposable migration, prepare the concrete reviewable result first, then identify the exact outstanding approval. Missing live credentials must not block unrelated offline work.

Do not publish/push, send supplier messages, introduce cloud spending, read private secrets, rewrite the stack, delete existing work or assert an unobserved success. Do not create additional agents/chats unless the user explicitly requests them. Keep proposed ADRs proposed until accepted by the responsible reviewer.

Use this completion format:

```text
Completed: <specific behavior and user outcome>
Changed: <important files/contracts>
Verified: <commands and PASS/FAIL/SKIPPED; synthetic/mock/live separated>
Open gate: <professional/architecture/operational blocker and owner, if known>
Next task: <one bounded action>
```

Never label the entire project production-ready because one slice passed.

## 10. Starting prompt

Use the companion [GPT6_LUNA_START_PROMPT.md](GPT6_LUNA_START_PROMPT.md) as the first message in the successor chat. Attach/open this repository as its workspace. The files and fresh checks, not prior chat memory, are the continuation source.
