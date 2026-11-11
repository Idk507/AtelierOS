-- Operator-reviewed template. Run as migration owner in the selected app schema.
-- These NOLOGIN group roles carry no credentials. Grant to separately managed logins.
-- Never grant schema ownership, SUPERUSER, BYPASSRLS or CREATE to the HTTP login.
CREATE ROLE atelier_api NOLOGIN;
CREATE ROLE atelier_worker NOLOGIN;
GRANT USAGE ON SCHEMA public TO atelier_api, atelier_worker;
GRANT SELECT ON organizations, users, memberships, projects, project_grants,
    garments, revisions, proposals, unlock_requests, approvals, artifacts,
    audit_events, idempotency, outbox, alembic_version TO atelier_api;
GRANT INSERT ON projects, project_grants, garments, revisions, proposals,
    unlock_requests, approvals, audit_events, idempotency, outbox TO atelier_api;
GRANT UPDATE (draft_revision_id, approved_revision_id) ON garments TO atelier_api;
GRANT UPDATE (status) ON proposals, unlock_requests TO atelier_api;
GRANT UPDATE (status) ON artifacts TO atelier_api;
GRANT INSERT ON artifacts TO atelier_api;
GRANT SELECT, INSERT ON research_sources, research_briefs TO atelier_api;
GRANT SELECT, INSERT ON material_offers TO atelier_api;
GRANT SELECT, INSERT ON material_comparisons TO atelier_api;
GRANT SELECT, INSERT ON workflow_runs TO atelier_api;
GRANT SELECT, INSERT ON sample_feedback TO atelier_api;
GRANT UPDATE (status, decided_by, proposal_id) ON workflow_runs TO atelier_api;
-- PostgreSQL row-lock statements require UPDATE permission on at least one column.
-- Identity-update triggers make these columns unwritable, even with that grant;
-- roles, active status and grant scope remain operator-only.
GRANT UPDATE (id) ON memberships, project_grants TO atelier_api;
GRANT SELECT ON outbox, event_receipts, tool_attempts TO atelier_worker;
GRANT INSERT ON event_receipts, tool_attempts TO atelier_worker;
GRANT UPDATE (delivered, attempts) ON outbox TO atelier_worker;
GRANT UPDATE (status) ON tool_attempts TO atelier_worker;
-- Grant consumer-specific internal effect permissions only after its P05 review.
