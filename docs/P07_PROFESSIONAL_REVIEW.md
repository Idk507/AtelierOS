# P07 technical handoff review package

Status: **awaiting independent professional and architecture review**. This document is a review checklist, not evidence of approval.

## Review inputs

Use a consented or clearly synthetic garment and record its organization, garment ID, revision ID and digest, artifact ID and package digest. Attach the generated JSON and PDF, and identify the source and date of each measurement and material offer. The locally generated `.local/ui/synthetic-handoff.pdf` is synthetic demonstration material only.

## Questions for a patternmaker and production reviewer

1. Identify the required points of measure, units, tolerances and missing evidence for this garment. Production release is disabled with `professional_completeness_assessment_required`. A single measurement and revision approval are insufficient. A reviewed assessment contract must bind the exact package digest, required points of measure and tolerances, view/BOM completeness, unresolved questions, professional actor and decision before release can be enabled.
2. Assess whether front and back views are actually identified and sufficiently detailed. The current component model does not establish view attribution.
3. Review material evidence, quantities, cost assumptions, BOM omissions and unresolved sample findings. Mark each unknown and its owner.
4. Examine sample photo rights, measurement provenance, observation, resolution, and revision linkage. Decide whether findings require another sample or design revision.
5. Confirm that aesthetic and technical decisions, handoff decision, actor identities and evidence snapshots refer to the intended revision. Review a historical export after an edit and confirm it is visibly stale.
6. Review PDF legibility, glyph replacement disclosures, pagination and missing data. Confirm the exact document formats needed for production; PDF is currently implemented, while an editable document format remains an open scope decision.
7. Document limitations for fit, sewing patterns and manufacturability. No generated output establishes those properties without independent validation.

## Decision record

Record reviewer name and role, date, examined revision and package digests, findings, corrective actions, owners and due dates. State accepted, rejected or pending for each finding. A named architect must review approval/evidence binding, authorization and rollout implications. Do not fill in approval on behalf of a reviewer.

## Engineering evidence to attach

Link the executed backend and browser results from `STATUS.md`, synthetic PDF render and screenshot paths, PDF download checks, security and retention review, known limitations, and any failed or skipped cases. Distinguish synthetic data, live-provider observations and professional review.
