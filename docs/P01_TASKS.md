# P01 bounded execution backlog
Prerequisite: P00 architecture gate accepted; unresolved entry decisions in P00_REVIEW.md resolved. Runtime remains unimplemented. Use existing apps/api and packages/domain, not the illustrative alternative directory tree in the proposal.

| Slice | Deliverable | Acceptance and verification | Depends on |
|---|---|---|---|
| 1 Project access | Minimal FastAPI service, typed identity context, membership/project models, disposable PostgreSQL migration | create/read own project; cross-tenant and inactive membership denied; pytest against PostgreSQL, Ruff, mypy | reviewed auth design |
| 2 Revision commits | immutable garment snapshots, canonical hash, draft compare-and-swap, scoped idempotency | two concurrent edits produce one winner; old payload unchanged; key replay returns same result and conflicting digest 409; PostgreSQL tests | 1 |
| 3 Locks | typed patch proposal/preview/accept and separately authorized unlock | direct and ancestor lock attacks rejected; accepted sleeve edit preserves neckline; unlock grants no garment approval; focused domain/API tests | 2 |
| 4 Approvals | human purpose-specific decision and head/hash/role transaction checks | stale/hash/role failures; historical approvals retained; aesthetic approval distinct from technical; concurrent approval/edit tests | 3 |
| 5 Recovery | atomic audit/outbox and durable attempt records | crash before/after delivery; duplicate consumers; replay never reissues side effect; migration upgrade/downgrade on disposable PostgreSQL | 4 |

Before each slice define at most five implementation files; split further if necessary. Checkpoint after slices 2 and 4: focused tests, typing/lint and contract review. Final gate: run complete P01 suite against real disposable PostgreSQL; record commands and failures in STATUS.md. No SQLite substitute, external provider calls, frontend or speculative later-phase work. Define reproducible dependency lockfiles and local test commands in slice 1. Do not fabricate commands for a runtime that does not yet exist.
