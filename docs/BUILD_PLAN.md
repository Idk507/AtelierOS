# Stage-gated implementation plan

This roadmap is a dependency graph, not an instruction to implement all phases in one session. Each `docs/phases/Pxx.md` specifies scope, tests, evidence, and exit checks.

| Phase | Primary outcome | Dependencies | Gate |
|---|---|---|---|
| P00 | architecture, DGT schema, API contracts, threat model, eval fixtures | none | ADR review |
| P01 | tenant-aware DGT, revisions, locking, audit events, PostgreSQL tests | P00 | consistency and authorization |
| P02 | editable tldraw canvas with semantic garment components | P01 | reversible geometry edits |
| P03 | cited web research, safe retrieval, moodboards | P01–P02 | citation and prompt injection checks |
| P04 | Azure multimodal understanding and image proposal adapters | P01–P03 | offline fixtures and opt-in live smoke |
| P05 | LangGraph + runtime harness with approval checkpoints | P01–P04 | failure recovery and permissions |
| P06 | material substitution, costing, dependency propagation | P05 | flagship workflow |
| P07 | draft technical flats/BOM/tech packs, sample feedback | P06 | expert-review artifacts |
| P08 | pilot workspace, security, telemetry, e2e tests | P07 | local demo and release audit |
| P09+ | collection planning, supplier RFQs, textile repeat, CAD, sustainability, post-launch learning | validated demand | separately gated |

## Cross-phase definition of done
Feature documented; typed contract; positive and negative tests; tenant isolation; no secrets in logs; provenance for claims; idempotent write endpoints; revision safety; trace spans and model-cost accounting where applicable. A creative render is not an engineering validation result. No phase can be claimed PASS from code inspection alone.

## Suggested cadence
Work in short PR-sized increments. Have Claude write a 5-line summary of intent, tests, results, blockers and next action to `docs/STATUS.md` at end of every accepted increment. Keep detailed reasoning in ADRs, not in session memory.

## P00 review package
See P00_SCOPE.md, P00_CONTRACTS.md, P00_SECURITY_MATRIX.md, P00_REVIEW.md and P01_TASKS.md. Six ADRs under adr/ remain PROPOSED. Synthetic scenarios are under ../packages/evaluation/p00/. No gate accepted.
