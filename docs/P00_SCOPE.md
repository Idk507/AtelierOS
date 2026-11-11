# P00 scope and traceability
Status: PROPOSED — architecture owner review required. Date: 2026-11-05.

## Document authority
The product proposal is the vision; BUILD_PLAN.md governs execution; STATUS.md records evidence. P00_CONTRACTS.md is the consolidated proposed interface contract and supersedes conflicting illustrative route, event and field examples in the proposal and older contracts. The proposal is preserved as a source document, including its historical journey letters. Use stable journey names below in new work. Both proposal timelines are historical estimates, not commitments.

## Users and product boundary
Primary user: boutique occasionwear designer. Buyer hypothesis: studio owner. Supporting roles: client-reviewer, patternmaker, production and org-admin. Start with one garment and preserve intent through research, manual sketch edits, material substitution and reviewed technical handoff. No fit certification, production patterns, autonomous supplier contact, purchases or sustainability certification.

## Traceability
| Journey | Phases | Acceptance | Required evidence |
|---|---|---|---|
| research-to-design | P01–P05, P07–P08 | cited claims; editable IDs; reversible patches; human approval | research-to-design.json; injection/SSRF tests; canvas reload recording; designer assessment |
| material-substitution | P01–P02, P04–P08 | locks preserved; evidence-based candidates; exact cost; stale artifacts flagged | material-substitution.json; PostgreSQL race/replay tests; cost oracle; reviewed export |
| sample-feedback | P01–P02, P05, P07–P08 | observations linked to revision; no invented measurements; patternmaker review | sample-feedback.json; annotation/revision tests; professional assessment |

## Discovery backlog (not completed evidence)
Interview 15–25 designers and technical stakeholders; seek 3–5 consented pilot studios. Validate recurring revision cost, willingness to pay, chosen garment category and representative data availability. Ask who approves aesthetics, construction and spending; how fabric shortages are handled; which technical fields must block export; what data may leave the studio. Record measured manual baseline and consent/license terms before using real customer assets.

## Hypotheses versus requirements
Boutique occasionwear fit, pricing, time savings, aesthetic quality thresholds and multi-agent value are hypotheses. Tenant isolation, immutable revisions, authorization, provenance, locks and explicit approvals are engineering requirements. No interview, pilot or provider readiness is asserted by these documents.
