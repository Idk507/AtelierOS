# ADR-005: Transactional outbox and attempt journal
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: In-process fire-and-forget or Redis-only queue. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
Persist revision, audit and outbox atomically; journal external intent with stable request digest before invocation.
Durable recovery without mandatory additional infrastructure; delivery is at least once, not exactly once.

## Security, cost and operational impact
Reauthorize before execution; duplicate event delivery cannot duplicate business transitions.
Polling/cleanup and attempt reconciliation require operational care.

## Rollback and acceptance evidence
Pause consumers, drain/reconcile durable intents, replace delivery adapter without deleting ledger.
Required evidence: P01 atomic writes; P05 crash before/after side effect, replay and ambiguous-result reconciliation.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
