"""Initial immutable DGT schema, frozen at P01; never imports mutable models."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

DDL = [
    """
 CREATE TABLE organizations (         name VARCHAR(200) NOT NULL,          id
VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id) )
    """,
    """
 CREATE TABLE users (         subject VARCHAR(200) NOT NULL,          id VARCHAR(100)
NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          UNIQUE (subject) )
    """,
    """
 CREATE TABLE memberships (         user_id VARCHAR(100) NOT NULL,          roles JSONB
NOT NULL,          active BOOLEAN NOT NULL,          organization_id VARCHAR(100) NOT
NULL,          id VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE
DEFAULT now() NOT NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY
(id),          UNIQUE (organization_id, user_id),          FOREIGN KEY(user_id)
REFERENCES users (id),          FOREIGN KEY(organization_id) REFERENCES organizations
(id) )
    """,
    """
CREATE INDEX ix_memberships_organization_id ON memberships (organization_id)
    """,
    """
 CREATE TABLE projects (         name VARCHAR(200) NOT NULL,          organization_id
VARCHAR(100) NOT NULL,          id VARCHAR(100) NOT NULL,          created_at TIMESTAMP
WITH TIME ZONE DEFAULT now() NOT NULL,          created_by VARCHAR(200) NOT NULL,
PRIMARY KEY (id),          UNIQUE (organization_id, id),          FOREIGN
KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_projects_organization_id ON projects (organization_id)
    """,
    """
 CREATE TABLE audit_events (         aggregate_id VARCHAR(100) NOT NULL,
revision_id VARCHAR(100),          event_type VARCHAR(100) NOT NULL,          detail
JSONB NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id VARCHAR(100)
NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          FOREIGN
KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_audit_events_aggregate_id ON audit_events (aggregate_id)
    """,
    """
CREATE INDEX ix_audit_events_organization_id ON audit_events (organization_id)
    """,
    """
 CREATE TABLE idempotency (         actor_id VARCHAR(100) NOT NULL,          key
VARCHAR(128) NOT NULL,          request_digest VARCHAR(64) NOT NULL,          response
JSONB NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id VARCHAR(100)
NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          UNIQUE
(organization_id, actor_id, key),          FOREIGN KEY(organization_id) REFERENCES
organizations (id) )
    """,
    """
CREATE INDEX ix_idempotency_organization_id ON idempotency (organization_id)
    """,
    """
 CREATE TABLE outbox (         envelope JSONB NOT NULL,          delivered BOOLEAN NOT
NULL,          attempts INTEGER NOT NULL,          organization_id VARCHAR(100) NOT
NULL,          id VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE
DEFAULT now() NOT NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY
(id),          UNIQUE (organization_id, id),          FOREIGN KEY(organization_id)
REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_outbox_organization_id ON outbox (organization_id)
    """,
    """
 CREATE TABLE tool_attempts (         idempotency_key VARCHAR(128) NOT NULL,
request_digest VARCHAR(64) NOT NULL,          status VARCHAR(30) NOT NULL,
organization_id VARCHAR(100) NOT NULL,          id VARCHAR(100) NOT NULL,
created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,          created_by
VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          UNIQUE (organization_id,
idempotency_key),          FOREIGN KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_tool_attempts_organization_id ON tool_attempts (organization_id)
    """,
    """
 CREATE TABLE project_grants (         project_id VARCHAR(100) NOT NULL,
user_id VARCHAR(100) NOT NULL,          organization_id VARCHAR(100) NOT NULL,
id VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),
FOREIGN KEY(organization_id, project_id) REFERENCES projects (organization_id, id),
UNIQUE (organization_id, project_id, user_id),          FOREIGN KEY(user_id) REFERENCES
users (id),          FOREIGN KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_project_grants_organization_id ON project_grants (organization_id)
    """,
    """
 CREATE TABLE garments (         project_id VARCHAR(100) NOT NULL,          name
VARCHAR(200) NOT NULL,          draft_revision_id VARCHAR(100),
approved_revision_id VARCHAR(100),          organization_id VARCHAR(100) NOT NULL,
id VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),
UNIQUE (organization_id, id),          FOREIGN KEY(organization_id, project_id)
REFERENCES projects (organization_id, id),          FOREIGN KEY(organization_id)
REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_garments_organization_id ON garments (organization_id)
    """,
    """
CREATE INDEX ix_garments_project_id ON garments (project_id)
    """,
    """
 CREATE TABLE event_receipts (         consumer VARCHAR(100) NOT NULL,          event_id
VARCHAR(100) NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id
VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),
UNIQUE (organization_id, consumer, event_id),          FOREIGN KEY(organization_id,
event_id) REFERENCES outbox (organization_id, id),          FOREIGN KEY(organization_id)
REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_event_receipts_organization_id ON event_receipts (organization_id)
    """,
    """
 CREATE TABLE revisions (         garment_id VARCHAR(100) NOT NULL,
parent_revision_id VARCHAR(100),          payload JSONB NOT NULL,          content_hash
VARCHAR(64) NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id
VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),
UNIQUE (organization_id, garment_id, id),          FOREIGN KEY(organization_id,
garment_id) REFERENCES garments (organization_id, id),          FOREIGN
KEY(organization_id, garment_id, parent_revision_id) REFERENCES revisions
(organization_id, garment_id, id),          FOREIGN KEY(organization_id) REFERENCES
organizations (id) )
    """,
    """
CREATE INDEX ix_revisions_garment_id ON revisions (garment_id)
    """,
    """
CREATE INDEX ix_revisions_organization_id ON revisions (organization_id)
    """,
    """
 CREATE TABLE proposals (         garment_id VARCHAR(100) NOT NULL,
base_revision VARCHAR(100) NOT NULL,          operations JSONB NOT NULL,
justification VARCHAR(2000) NOT NULL,          preview_hash VARCHAR(64) NOT NULL,
status VARCHAR(30) NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id
VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT
NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),
FOREIGN KEY(organization_id, garment_id, base_revision) REFERENCES revisions
(organization_id, garment_id, id),          FOREIGN KEY(organization_id) REFERENCES
organizations (id) )
    """,
    """
CREATE INDEX ix_proposals_organization_id ON proposals (organization_id)
    """,
    """
CREATE INDEX ix_proposals_garment_id ON proposals (garment_id)
    """,
    """
 CREATE TABLE unlock_requests (         garment_id VARCHAR(100) NOT NULL,
base_revision VARCHAR(100) NOT NULL,          component_id VARCHAR(100) NOT NULL,
reason VARCHAR(2000) NOT NULL,          status VARCHAR(30) NOT NULL,
organization_id VARCHAR(100) NOT NULL,          id VARCHAR(100) NOT NULL,
created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,          created_by
VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          FOREIGN KEY(organization_id,
garment_id, base_revision) REFERENCES revisions (organization_id, garment_id, id),
FOREIGN KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_unlock_requests_organization_id ON unlock_requests (organization_id)
    """,
    """
 CREATE TABLE approvals (         garment_id VARCHAR(100) NOT NULL,          revision_id
VARCHAR(100) NOT NULL,          content_hash VARCHAR(64) NOT NULL,          purpose
VARCHAR(30) NOT NULL,          decision VARCHAR(30) NOT NULL,          role VARCHAR(30)
NOT NULL,          organization_id VARCHAR(100) NOT NULL,          id VARCHAR(100) NOT
NULL,          created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
created_by VARCHAR(200) NOT NULL,          PRIMARY KEY (id),          FOREIGN
KEY(organization_id, garment_id, revision_id) REFERENCES revisions (organization_id,
garment_id, id),          FOREIGN KEY(organization_id) REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_approvals_organization_id ON approvals (organization_id)
    """,
    """
CREATE INDEX ix_approvals_garment_id ON approvals (garment_id)
    """,
    """
 CREATE TABLE artifacts (         garment_id VARCHAR(100) NOT NULL,          revision_id
VARCHAR(100) NOT NULL,          kind VARCHAR(50) NOT NULL,          depends_on JSONB NOT
NULL,          status VARCHAR(30) NOT NULL,          organization_id VARCHAR(100) NOT
NULL,          id VARCHAR(100) NOT NULL,          created_at TIMESTAMP WITH TIME ZONE
DEFAULT now() NOT NULL,          created_by VARCHAR(200) NOT NULL,          PRIMARY KEY
(id),          FOREIGN KEY(organization_id, garment_id, revision_id) REFERENCES
revisions (organization_id, garment_id, id),          FOREIGN KEY(organization_id)
REFERENCES organizations (id) )
    """,
    """
CREATE INDEX ix_artifacts_organization_id ON artifacts (organization_id)
    """,
    """
ALTER TABLE garments ADD CONSTRAINT fk_draft_head FOREIGN KEY(organization_id, id,
draft_revision_id) REFERENCES revisions (organization_id, garment_id, id)
    """,
    """
ALTER TABLE garments ADD CONSTRAINT fk_approved_head FOREIGN KEY(organization_id, id,
approved_revision_id) REFERENCES revisions (organization_id, garment_id, id)
    """,
    """
 CREATE FUNCTION reject_history_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
RAISE EXCEPTION 'immutable_history' USING ERRCODE = '23514'; END; $$
    """,
    """
 CREATE TRIGGER revisions_immutable BEFORE UPDATE OR DELETE ON revisions FOR EACH ROW
EXECUTE FUNCTION reject_history_mutation()
    """,
    """
 CREATE TRIGGER audit_events_immutable BEFORE UPDATE OR DELETE ON audit_events FOR EACH
ROW EXECUTE FUNCTION reject_history_mutation()
    """,
    """
 CREATE TRIGGER approvals_immutable BEFORE UPDATE OR DELETE ON approvals FOR EACH ROW
EXECUTE FUNCTION reject_history_mutation()
    """,
    """
 CREATE TRIGGER event_receipts_immutable BEFORE UPDATE OR DELETE ON event_receipts FOR
EACH ROW EXECUTE FUNCTION reject_history_mutation()
    """,
    """
CREATE TRIGGER membership_identity_immutable BEFORE UPDATE OF id ON memberships
FOR EACH ROW EXECUTE FUNCTION reject_history_mutation()
    """,
    """
CREATE TRIGGER grant_identity_immutable BEFORE UPDATE OF id ON project_grants
FOR EACH ROW EXECUTE FUNCTION reject_history_mutation()
    """,
]


def upgrade() -> None:
    """Create tables, composite tenant constraints and append-only triggers."""
    for statement in DDL:
        op.execute(statement)


def downgrade() -> None:
    """Drop P01 schema only; explicitly destructive, disposable databases only."""
    op.execute("ALTER TABLE garments DROP CONSTRAINT fk_draft_head")
    op.execute("ALTER TABLE garments DROP CONSTRAINT fk_approved_head")
    op.execute("DROP TABLE unlock_requests")
    op.execute("DROP TABLE proposals")
    op.execute("DROP TABLE artifacts")
    op.execute("DROP TABLE approvals")
    op.execute("DROP TABLE revisions")
    op.execute("DROP TABLE project_grants")
    op.execute("DROP TABLE garments")
    op.execute("DROP TABLE event_receipts")
    op.execute("DROP TABLE tool_attempts")
    op.execute("DROP TABLE projects")
    op.execute("DROP TABLE outbox")
    op.execute("DROP TABLE memberships")
    op.execute("DROP TABLE idempotency")
    op.execute("DROP TABLE audit_events")
    op.execute("DROP TABLE users")
    op.execute("DROP TABLE organizations")
    op.execute("DROP FUNCTION reject_history_mutation()")
