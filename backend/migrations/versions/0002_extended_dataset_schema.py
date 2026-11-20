"""Add provenance-aware room, roster, equipment and energy seed schema."""
from alembic import op
import sqlalchemy as sa

revision = "0002_extended_dataset_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"))
    op.add_column("buildings", sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"))
    for column, typ, default in (
        ("name", sa.String(120), ""), ("department", sa.String(50), "Shared"),
        ("estimated_connected_load_kw", sa.Float(), "0"), ("timetable_eligible", sa.Boolean(), "0"),
        ("provenance", sa.String(20), "SYNTHETIC"), ("notes", sa.String(300), ""),
    ):
        op.add_column("rooms", sa.Column(column, typ, nullable=False, server_default=default))
    with op.batch_alter_table("rooms") as batch:
        batch.alter_column("room_type", type_=sa.String(100), existing_type=sa.String(20))
    op.create_table("room_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(60), nullable=False, unique=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="INFERRED"),
    )
    op.create_index("ix_room_aliases_room_id", "room_aliases", ["room_id"])
    op.create_table("equipment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_code", sa.String(20), nullable=False, unique=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("watts_each", sa.Float(), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"),
    )
    op.create_index("ix_equipment_room_id", "equipment", ["room_id"])
    op.create_table("energy_baselines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("baseline_code", sa.String(20), nullable=False, unique=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("connected_load_kw", sa.Float(), nullable=False),
        sa.Column("hours_per_day", sa.Float(), nullable=False, server_default="6"),
        sa.Column("days_per_week", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("tariff_per_kwh", sa.Float(), nullable=False, server_default="8.5"),
        sa.Column("daily_kwh", sa.Float(), nullable=False),
        sa.Column("weekly_kwh", sa.Float(), nullable=False),
        sa.Column("weekly_cost", sa.Float(), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="SYNTHETIC"),
    )
    op.create_table("students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usn", sa.String(20), nullable=True, unique=True),
        sa.Column("source_identifier", sa.String(40), nullable=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("lab_batch", sa.String(10), nullable=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
    )
    op.create_index("ix_students_usn", "students", ["usn"])
    op.create_table("sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("home_room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("declared_student_count", sa.Integer(), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
    )
    op.create_table("division_section_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.UniqueConstraint("student_id", "section_id"),
    )
    op.create_index("ix_division_section_map_student_id", "division_section_map", ["student_id"])
    op.create_index("ix_division_section_map_section_id", "division_section_map", ["section_id"])
    op.create_table("holidays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("holiday_date", sa.Date(), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
    )


def downgrade() -> None:
    op.drop_table("holidays")
    op.drop_index("ix_division_section_map_section_id", table_name="division_section_map")
    op.drop_index("ix_division_section_map_student_id", table_name="division_section_map")
    op.drop_table("division_section_map")
    op.drop_table("sections")
    op.drop_index("ix_students_usn", table_name="students")
    op.drop_table("students")
    op.drop_table("energy_baselines")
    op.drop_index("ix_equipment_room_id", table_name="equipment")
    op.drop_table("equipment")
    op.drop_index("ix_room_aliases_room_id", table_name="room_aliases")
    op.drop_table("room_aliases")
    with op.batch_alter_table("rooms") as batch:
        for column in ("notes", "provenance", "timetable_eligible", "estimated_connected_load_kw", "department", "name"):
            batch.drop_column(column)
        batch.alter_column("room_type", type_=sa.String(20), existing_type=sa.String(100))
    op.drop_column("buildings", "provenance")
    op.drop_column("users", "provenance")
