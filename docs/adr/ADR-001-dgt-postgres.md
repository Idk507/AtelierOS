# ADR-001: Canonical PostgreSQL DGT
Status: PROPOSED
Date: 2026-11-05
Decision owner: Human architect (data owner additionally for ADR-006)

## Context and options
Compare the selected approach with: Mutable document store or SQLite-only state. Criteria: correctness, latency, cost, security, changeability, testability and complexity.

## Proposed decision and consequences
PostgreSQL transactions and immutable JSON revision snapshots with normalized membership, approval and event tables.
Single transactional authority prevents cross-record approval races; SQLite cannot establish production locking evidence.

## Security, cost and operational impact
Tenant scope and membership checks are mandatory; least-privilege database roles.
Snapshot storage and migration maintenance cost; one local database, no compulsory Docker.

## Rollback and acceptance evidence
Export immutable snapshots and migrate through a reviewed adapter; never rewrite historical hashes.
Required evidence: PostgreSQL concurrency, isolation, hash and immutable-history tests in P01.
Current evidence: design inspection only; runtime NOT VERIFIED. Owner sign-off required before acceptance.
