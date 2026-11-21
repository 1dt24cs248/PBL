"""Record holiday sources and seed the confirmed ERP holiday."""
from alembic import op
import sqlalchemy as sa


revision = "0006_erp_holiday_source"
down_revision = "0005_energy_optimizer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("holidays") as batch:
        batch.add_column(sa.Column("source", sa.String(length=30), nullable=False,
                                   server_default="UNKNOWN"))
    op.execute(sa.text(
        "UPDATE holidays SET source='M1' WHERE holiday_date='2026-11-10'"
    ))
    op.execute(sa.text(
        "UPDATE holidays SET source='ERP_SCREENSHOT', name='Kanaka Jayanthi', "
        "provenance='REAL_ERP_SCREENSHOT' WHERE holiday_date='2026-11-27'"
    ))
    op.execute(sa.text(
        "INSERT INTO holidays (holiday_date, name, source, provenance) "
        "SELECT '2026-11-27', 'Kanaka Jayanthi', 'ERP_SCREENSHOT', 'REAL_ERP_SCREENSHOT' "
        "WHERE NOT EXISTS (SELECT 1 FROM holidays WHERE holiday_date='2026-11-27')"
    ))
    op.execute(sa.text(
        "UPDATE rooms SET name='Classroom 11', room_type='Classroom', capacity=60, "
        "timetable_eligible=TRUE, provenance='SYNTHETIC', notes='Synthetic M7 room type and capacity.' "
        "WHERE number='A-F2-11'"
    ))
    op.execute(sa.text(
        "UPDATE rooms SET name='Computer Lab 12', room_type='Computer Lab', capacity=30, "
        "timetable_eligible=TRUE, provenance='SYNTHETIC', notes='Synthetic M7 room type and capacity.' "
        "WHERE number='A-F2-12'"
    ))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM holidays WHERE holiday_date='2026-11-27'"))
    op.execute(sa.text(
        "UPDATE rooms SET name='Unspecified room', room_type='Unspecified', capacity=0, "
        "timetable_eligible=FALSE, provenance='INFERRED', "
        "notes='Added per M1; no source specifications were supplied.' "
        "WHERE number IN ('A-F2-11','A-F2-12')"
    ))
    with op.batch_alter_table("holidays") as batch:
        batch.drop_column("source")
