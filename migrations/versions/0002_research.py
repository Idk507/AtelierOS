"""Add immutable, revision-bound research sources and briefs."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store supplied evidence and generated brief snapshots separately."""
    for table in ("research_sources", "research_briefs"):
        op.execute(f"""
            CREATE TABLE {table} (
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
        op.execute(f"CREATE INDEX ix_{table}_scope ON {table} (organization_id, garment_id)")
        op.execute(f"""
            CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_history_mutation()
        """)


def downgrade() -> None:
    """Remove research tables in an explicitly disposable database."""
    op.execute("DROP TABLE research_briefs")
    op.execute("DROP TABLE research_sources")
