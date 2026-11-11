# ADR-004: LangGraph plus independent harness
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: Single unrestricted agent or graph-only permission prompts. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
LangGraph manages checkpoints and routing; harness enforces tools, scope, budgets and approval boundaries.
Explicit separation makes permissions testable independently of model behavior.

## Security, cost and operational impact
Agents cannot grant approvals; untrusted tool results cannot enlarge capability sets.
Additional workflow complexity is justified only against single-model baseline measurements.

## Rollback and acceptance evidence
Run deterministic tools directly while preserving domain commands and audit trail.
Required evidence: P05 interrupted runs, corrupt checkpoints, injection, cancellation and budget tests.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
