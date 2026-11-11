# System architecture and contracts

> P00 reconciliation: P00_CONTRACTS.md governs proposed route, field, event and lifecycle semantics; P00_SCOPE.md supplies stable journey names. Older examples below are historical where inconsistent.


## Runtime boundary
Browser UI → FastAPI BFF → domain services + orchestration worker → (Azure OpenAI adapter, research adapter, catalog adapter, object storage). PostgreSQL is authoritative for tenants, DGT, revisions, approvals and outbox. Redis and Docker are not compulsory. External APIs are off by default and require outbound allowlisting and explicit credentials.

## Core entity model
Organization, User, Membership(role), Project, GarmentTwin, Component, CanvasDocument, DesignRevision, Constraint, Asset, MaterialCatalogItem, MaterialOffer, BOMLine, ResearchSource, ResearchClaim, AgentRun, ToolInvocation, Approval, SpecDraft, Sample, SampleFeedback, AuditEvent, OutboxEvent. Every mutable row includes organization_id where relevant. DGT has `approved_revision_id`, `draft_revision_id` with concurrency guard and immutable revision payload hash.

## DGT invariants
A revision is immutable after being committed; new edits produce a child revision and diff. Locked component modifications are rejected unless a permitted override is separately approved. Approval binds actor, role, organization, revision id, exact content hash and purpose. An outdated revision cannot be silently approved. Supplied catalog facts have source ID, retrieval timestamp, currency, units and confidence. Unsupported claims remain UNKNOWN. Images are preview assets, not CAD/pattern specs. User-provided measurements require explicit origin and consent.

## Required API routes (proposed, not implemented)
`POST /v1/projects`, `POST /v1/garments`, `GET /v1/garments/{id}`, `POST /v1/garments/{id}/revisions`, `POST /v1/garments/{id}/constraints`, `POST /v1/canvas/{id}/patches`, `POST /v1/research/jobs`, `POST /v1/visuals/jobs`, `POST /v1/materials/compare`, `POST /v1/approvals`, `GET /v1/jobs/{id}`, `GET /v1/garments/{id}/audit`, `POST /v1/techpacks/drafts`, `POST /v1/samples/{id}/feedback`.

## Patch contract
`{tenant_id, project_id, garment_id, base_revision, idempotency_key, operations: [{op, target_component_id, payload}], justification, requested_by}`. Validate operation schema, authorization, revision head, locks and derived downstream impacts before persist. Atomically create revision and outbox event; never mutate prior approved revision. Return `{new_revision, diff, invalidated_artifacts, approval_status}`.

## Domain events
`research.completed`, `canvas.patch.proposed`, `design.revision.created`, `material.alternative.proposed`, `cost.estimate.updated`, `spec.draft.created`, `approval.requested`, `approval.decided`, `sample.feedback.submitted`. Each event carries event_id, org_id, aggregate_id, revision_id, schema_version, causation_id and occurred_at. Consumers are idempotent; replay must not resend supplier communication.

## Harness vs orchestration
LangGraph models the workflow state machine, checkpoints, fan-out and human interrupts. `packages/harness` provides tool broker, authorization context, scoped skill executor, budget limiter, attempt ledger, provenance, safe artifact writer, trace collector and independent validators. Specialist agents (research, vision, sketch, concept, material, costing, spec, reviewer) are task modules routed by the graph; never all activated unconditionally.

## Web research
Query planning → provider search → domain policy → safe fetch/extraction → dated snapshots → claim-to-source mapping → sourced research brief → optional cited moodboard. No credentialed browser sessions or scraped copyrighted image reuse by default. Unknown citation provenance blocks publication. Live web research gated by `RESEARCH_ENABLE_LIVE`.

## Drawing representations
Canvas source format: semantic editable component IDs + tldraw primitives and paths. Generated raster images are separate linked layers. Revisions store component patches with selection geometry and preconditions. Do not make LLM directly edit database rows; use validated patch tool. Technical flats remain 2D draft assets until expert approval; sewing patterns and fabric simulation are later adapters.

## Agent failure model
Every tool call has a stable idempotency key and bounded timeout. Model output goes through Pydantic validators. Retry only rate limits, transient networking and explicitly retryable errors with backoff/jitter; never retry authorization or validation failures. Interrupt at irreversible/high-cost actions. Persist recovery checkpoints before external side effects. The independent reviewer reports findings but never grants approval.
