# ADR-006: Evidence rights and retention
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: Store arbitrary web images indefinitely or trust model-generated citations. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
Claim-level immutable citations and explicit asset rights/consent; unknown rights prohibit reuse.
Rights-aware provenance supports review without representing inspiration as physical evidence.

## Security, cost and operational impact
SSRF-safe retrieval, scoped storage, deletion propagation and redacted logs; retention proposal in P00_SECURITY_MATRIX.md.
Licensed sources may cost money; consent and jurisdiction require owner review before real ingestion.

## Rollback and acceptance evidence
Revoke source, stop reuse and mark dependent outputs needs_review; preserve minimal permitted audit metadata.
Required evidence: P03 missing dates/rights, redirect, injection and citation tests; P08 deletion/retention verification.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
