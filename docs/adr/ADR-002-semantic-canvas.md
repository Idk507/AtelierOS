# ADR-002: Semantic canvas with tldraw adapter
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: Raster-only editor or building a bespoke SVG editor. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
tldraw editor with stable component IDs; backend-validated patches remain canonical.
Existing drawing interactions reduce UI work while vectors preserve local edits.

## Security, cost and operational impact
Untrusted canvas payloads receive schema, bounds, lock and tenant checks.
Assess tldraw license and serialization/version compatibility before P02; performance benchmark on representative sketches.

## Rollback and acceptance evidence
Retain portable semantic geometry and asset export; replace renderer adapter.
Required evidence: P02 undo/reload/lock/selection and migration fixtures; manual designer review.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
