# Evaluation strategy

> P00 reconciliation: P00_CONTRACTS.md governs proposed route, field, event and lifecycle semantics; P00_SCOPE.md supplies stable journey names. Older examples below are historical where inconsistent.


Datasets: licensed/user-supplied benchmark sketches, semantic edits, curated fabric offers, sampled supplier responses and deliberate prompt-injection payloads. No scraped proprietary collection images in permanent fixtures without rights. Use blinded human raters for visual preservation and construction issues.

## Core metrics and gates
Research citation validity: every substantive external claim resolves to source snippet and retrieval date. Constraint preservation: no hard-lock changes committed. Revision consistency: 100% of artifact revision pointers match committed DGT head or are explicitly marked stale. Approval integrity: stale, unsigned and wrong-role approvals rejected. Costing reference cases: exact deterministic calculation within documented rounding. Cross-tenant leakage: zero allowed. Web source injection: zero unauthorized tool executions. Agent-call budgets and latency measured with p50/p95, model costs and retry count. Rendering quality is evaluated separately from technical validity.

## Offline first
Mock Azure, fake search results, controlled catalog offers and filesystem object store for deterministic CI. Maintain negative tests. Live Azure smoke tests must be explicitly enabled, low-budget, recorded and skipped by default. Never treat passing mock tests as proof of live provider readiness. A release decision requires minimum design partner review on realistic garment scenarios.

## Harness² optimization
Run offline candidate skill/prompt/harness changes against a frozen test split. Compare cost, regression failures, approved locked-attribute score and compliance; do not train on or inspect held-out final evaluation tasks during tuning. Promote only reviewed artifact version with recorded measurements. No autonomous edits to production policies or approval rules.

## Canonical journeys
research-to-design: research → cited moodboard → sketch → editable revision; material-substitution: material shortage → three catalog alternatives → cost/spec impact → signed approval → correct export; sample-feedback: sample defect image → structured feedback → revision patch → technical review. Maintain traces, expected artifacts and human-grade rubrics per journey.
