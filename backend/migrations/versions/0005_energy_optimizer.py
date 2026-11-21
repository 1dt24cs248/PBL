"""Persist optimizer drafts and timetable room provenance."""
from alembic import op
import sqlalchemy as sa


revision = "0005_energy_optimizer"
down_revision = "0004_floorplan_navigation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("timetable_sessions") as batch:
        batch.add_column(sa.Column("room_inferred", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "optimizer_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"),
    )
    op.create_index("ix_optimizer_proposals_term_id", "optimizer_proposals", ["term_id"])
    op.create_index("ix_optimizer_proposals_status", "optimizer_proposals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_optimizer_proposals_status", table_name="optimizer_proposals")
    op.drop_index("ix_optimizer_proposals_term_id", table_name="optimizer_proposals")
    op.drop_table("optimizer_proposals")
    with op.batch_alter_table("timetable_sessions") as batch:
        batch.drop_column("room_inferred")
