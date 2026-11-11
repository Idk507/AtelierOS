# ADR-003: Mock-first provider boundary
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: Direct SDK calls from agents or assumed shared deployment capabilities. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
Separate chat, vision, image and embedding protocols with deterministic mocks and explicit live feature switches.
Mocks support repeatability; capability errors remain visible instead of silent substitutions.

## Security, cost and operational impact
No secrets in model context/logs; consent and budget checks before outbound requests.
Live API, region, image support and SDK versions UNVERIFIED; price and latency unknown.

## Rollback and acceptance evidence
Disable live capabilities and retain labeled fixture operation; swap provider adapter.
Required evidence: P04 typed error/output tests; separately authorized low-budget live capability checks.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
