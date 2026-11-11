"""Store append-only sample evidence and freeze handoff evidence snapshots."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sample_feedback (
            id varchar(100) PRIMARY KEY,
            organization_id varchar(100) NOT NULL REFERENCES organizations(id),
            garment_id varchar(100) NOT NULL,
            revision_id varchar(100) NOT NULL,
            created_by varchar(200) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            payload jsonb NOT NULL,
            FOREIGN KEY (organization_id, garment_id, revision_id)
                REFERENCES revisions(organization_id, garment_id, id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_sample_feedback_scope
        ON sample_feedback (organization_id, garment_id, revision_id)
    """)
    op.execute("""
        CREATE TRIGGER sample_feedback_immutable BEFORE UPDATE OR DELETE ON sample_feedback
        FOR EACH ROW EXECUTE FUNCTION reject_history_mutation()
    """)
    op.execute("ALTER TABLE artifacts ADD COLUMN review_payload jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE artifacts DROP COLUMN review_payload")
    op.execute("DROP TABLE sample_feedback")
