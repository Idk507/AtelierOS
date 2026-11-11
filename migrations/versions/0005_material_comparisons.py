"""Persist reproducible, immutable material comparisons."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE material_comparisons (
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
        CREATE TRIGGER material_comparisons_immutable
        BEFORE UPDATE OR DELETE ON material_comparisons
        FOR EACH ROW EXECUTE FUNCTION reject_history_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TABLE material_comparisons")
