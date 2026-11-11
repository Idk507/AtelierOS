# P00 architecture review checklist and blockers
Status: AWAITING HUMAN REVIEW. No ADR is accepted.

- [ ] Architect accepts domain, API, revision/hash and outbox semantics (ADR-001, ADR-005); blocks P01.
- [ ] Product owner confirms niche, required approval purposes and role assignments; blocks P01 approval implementation.
- [ ] Security owner approves local authentication design before P01: use a test-only injected identity for isolated service tests; runtime must use validated issuer/audience/expiry and project membership, never a client role header. Identity-provider selection remains a P01 entry decision.
- [ ] Architect accepts canvas licensing/serialization assessment (ADR-002); blocks P02.
- [ ] Data owner approves rights, consent and retention defaults (ADR-006); blocks real-data ingestion/P03.
- [ ] Integration owner verifies SDK/deployment capabilities and explicit spend authorization (ADR-003); blocks live P04 only, not mocks.
- [ ] Architect accepts bounded orchestration and recovery (ADR-004); blocks P05.
- [ ] Domain professional reviews technical handoff rubric; blocks P07 acceptance.

## Evidence classification
Scaffold and fixture validation are local static evidence only. PostgreSQL authorization/races, browser behavior, live providers, user interviews and professional review remain NOT VERIFIED. No synthetic scenario is market evidence. Record each decision owner identity and date at review, then change individual ADR status explicitly.
