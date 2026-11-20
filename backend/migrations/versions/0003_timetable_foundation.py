"""Normalize student divisions and inferred division-to-section mapping."""
from alembic import op
import sqlalchemy as sa

revision = "0003_timetable_foundation"
down_revision = "0002_extended_dataset_schema"
branch_labels = None
depends_on = None


DIVISION_LETTERS = [(f"CSE-{number}", chr(ord("A") + number - 1)) for number in range(1, 7)]


def upgrade() -> None:
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("division_code", sa.String(10), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE students
        SET division_code = (
            SELECT sections.code
            FROM division_section_map
            JOIN sections ON sections.id = division_section_map.section_id
            WHERE division_section_map.student_id = students.id
            LIMIT 1
        )
    """))
    with op.batch_alter_table("students") as batch:
        batch.alter_column("division_code", existing_type=sa.String(10), nullable=False)
        batch.create_index("ix_students_division_code", ["division_code"])
    op.drop_table("division_section_map")
    op.create_table("division_section_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("division_code", sa.String(10), nullable=False, unique=True),
        sa.Column("section_letter", sa.String(5), nullable=False),
        sa.Column("data_status", sa.String(20), nullable=False, server_default="INFERRED"),
        sa.Column("admin_editable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="INFERRED"),
    )
    bind.execute(sa.text("""
        INSERT INTO division_section_map (division_code, section_letter, data_status, admin_editable, provenance)
        VALUES (:division_code, :section_letter, 'INFERRED', 1, 'INFERRED')
    """), [{"division_code": division, "section_letter": letter} for division, letter in DIVISION_LETTERS])
    op.create_table("academic_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("academic_year", sa.String(20), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("term_kind", sa.String(10), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
    )
    op.create_table("timetable_subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.UniqueConstraint("term_id", "code"),
    )
    op.create_index("ix_timetable_subjects_term_id", "timetable_subjects", ["term_id"])
    op.create_table("faculty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initials", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="INFERRED"),
        sa.UniqueConstraint("term_id", "initials"),
    )
    op.create_index("ix_faculty_term_id", "faculty", ["term_id"])
    op.create_table("timetable_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("division_code", sa.String(10), nullable=True),
        sa.Column("home_room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.UniqueConstraint("term_id", "code"),
    )
    op.create_index("ix_timetable_sections_term_id", "timetable_sections", ["term_id"])
    op.create_table("timetable_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term_id", sa.Integer(), sa.ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("timetable_sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch", sa.String(5), nullable=False, server_default="ALL"),
        sa.Column("day", sa.String(3), nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("end_period", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("timetable_subjects.id"), nullable=True),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id"), nullable=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id"), nullable=True),
        sa.Column("room_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("raw_label", sa.String(500), nullable=False),
        sa.Column("block_id", sa.String(80), nullable=True),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    for column in ("term_id", "section_id", "faculty_id", "room_id", "block_id"):
        op.create_index(f"ix_timetable_sessions_{column}", "timetable_sessions", [column])
    op.create_table("timetable_session_faculty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("timetable_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_id", sa.Integer(), sa.ForeignKey("faculty.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.UniqueConstraint("session_id", "faculty_id"),
    )
    op.create_index("ix_timetable_session_faculty_session_id", "timetable_session_faculty", ["session_id"])
    op.create_index("ix_timetable_session_faculty_faculty_id", "timetable_session_faculty", ["faculty_id"])


def downgrade() -> None:
    op.drop_index("ix_timetable_session_faculty_faculty_id", table_name="timetable_session_faculty")
    op.drop_index("ix_timetable_session_faculty_session_id", table_name="timetable_session_faculty")
    op.drop_table("timetable_session_faculty")
    for column in ("block_id", "room_id", "faculty_id", "section_id", "term_id"):
        op.drop_index(f"ix_timetable_sessions_{column}", table_name="timetable_sessions")
    op.drop_table("timetable_sessions")
    op.drop_index("ix_timetable_sections_term_id", table_name="timetable_sections")
    op.drop_table("timetable_sections")
    op.drop_index("ix_faculty_term_id", table_name="faculty")
    op.drop_table("faculty")
    op.drop_index("ix_timetable_subjects_term_id", table_name="timetable_subjects")
    op.drop_table("timetable_subjects")
    op.drop_table("academic_terms")
    op.drop_table("division_section_map")
    op.create_table("division_section_map",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.Integer(), sa.ForeignKey("sections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provenance", sa.String(20), nullable=False, server_default="REAL_DSATM_PDF"),
        sa.UniqueConstraint("student_id", "section_id"),
    )
    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO division_section_map (student_id, section_id, provenance)
        SELECT students.id, sections.id, students.provenance
        FROM students JOIN sections ON sections.code = students.division_code
    """))
    with op.batch_alter_table("students") as batch:
        batch.drop_index("ix_students_division_code")
        batch.drop_column("division_code")
