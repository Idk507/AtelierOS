"""Persist workflow review checkpoints against exact garment revisions."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE workflow_runs (
            id varchar(100) PRIMARY KEY,
            organization_id varchar(100) NOT NULL REFERENCES organizations(id),
            garment_id varchar(100) NOT NULL,
            revision_id varchar(100) NOT NULL,
            created_by varchar(200) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            payload jsonb NOT NULL,
            status varchar(30) NOT NULL CHECK (status IN
                ('awaiting_review', 'approved', 'rejected', 'cancelled')),
            decided_by varchar(200),
            proposal_id varchar(100) REFERENCES proposals(id),
            FOREIGN KEY (organization_id, garment_id, revision_id)
                REFERENCES revisions(organization_id, garment_id, id)
        )
    """)
    op.execute("CREATE INDEX ix_workflow_runs_scope ON workflow_runs (organization_id, garment_id)")


def downgrade() -> None:
    op.execute("DROP TABLE workflow_runs")
