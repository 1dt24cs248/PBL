from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLES = ("student", "teaching_faculty", "hod", "admin", "maintenance")
ROOM_STATUSES = (
    "available", "occupied", "reserved", "under_maintenance", "temporarily_unavailable",
)
CATEGORY_OF_ROLE = {
    "student": "Student", "teaching_faculty": "Faculty", "hod": "Faculty",
    "admin": "Management", "maintenance": "Management",
}


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(30))
    department: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")


class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    floors: Mapped[int] = mapped_column(Integer, default=1)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")
    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("building_id", "number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    room_type: Mapped[str] = mapped_column(String(100), default="classroom")
    facilities: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(30), default="available")
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(120), default="")
    department: Mapped[str] = mapped_column(String(50), default="Shared")
    estimated_connected_load_kw: Mapped[float] = mapped_column(Float, default=0)
    timetable_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")
    notes: Mapped[str] = mapped_column(String(300), default="")
    x: Mapped[float] = mapped_column(Float, default=0)
    y: Mapped[float] = mapped_column(Float, default=0)
    w: Mapped[float] = mapped_column(Float, default=0)
    h: Mapped[float] = mapped_column(Float, default=0)
    building: Mapped[Building] = relationship(back_populates="rooms")
    aliases: Mapped[list["RoomAlias"]] = relationship(back_populates="room", cascade="all, delete-orphan")

    @property
    def real_label(self) -> str:
        return self.name or self.number

    @property
    def alias_values(self) -> list[str]:
        return sorted(alias.alias for alias in self.aliases)

    @property
    def data_status(self) -> str:
        return self.provenance

    @property
    def capacity_effective(self) -> int:
        return 0 if self.status in {"under_maintenance", "temporarily_unavailable"} else self.capacity


class RoomAlias(Base):
    __tablename__ = "room_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(60), unique=True)
    provenance: Mapped[str] = mapped_column(String(20), default="INFERRED")
    room: Mapped[Room] = relationship(back_populates="aliases")


class Equipment(Base):
    __tablename__ = "equipment"
    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_code: Mapped[str] = mapped_column(String(20), unique=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    quantity: Mapped[int] = mapped_column(Integer)
    watts_each: Mapped[float] = mapped_column(Float)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")


class EnergyBaseline(Base):
    __tablename__ = "energy_baselines"
    id: Mapped[int] = mapped_column(primary_key=True)
    baseline_code: Mapped[str] = mapped_column(String(20), unique=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), unique=True)
    connected_load_kw: Mapped[float] = mapped_column(Float)
    hours_per_day: Mapped[float] = mapped_column(Float, default=6)
    days_per_week: Mapped[int] = mapped_column(Integer, default=5)
    tariff_per_kwh: Mapped[float] = mapped_column(Float, default=8.5)
    daily_kwh: Mapped[float] = mapped_column(Float)
    weekly_kwh: Mapped[float] = mapped_column(Float)
    weekly_cost: Mapped[float] = mapped_column(Float)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("usn"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    usn: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    source_identifier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160))
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lab_batch: Mapped[str | None] = mapped_column(String(10), nullable=True)
    division_code: Mapped[str] = mapped_column(String(10), default="", index=True)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class Section(Base):
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    home_room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    declared_student_count: Mapped[int] = mapped_column(Integer)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class DivisionSectionMap(Base):
    __tablename__ = "division_section_map"
    id: Mapped[int] = mapped_column(primary_key=True)
    division_code: Mapped[str] = mapped_column(String(10), unique=True)
    section_letter: Mapped[str] = mapped_column(String(5))
    data_status: Mapped[str] = mapped_column(String(20), default="INFERRED")
    admin_editable: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance: Mapped[str] = mapped_column(String(20), default="INFERRED")


class Holiday(Base):
    __tablename__ = "holidays"
    id: Mapped[int] = mapped_column(primary_key=True)
    holiday_date: Mapped[object] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(100))
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    academic_year: Mapped[str] = mapped_column(String(20))
    semester: Mapped[int] = mapped_column(Integer)
    term_kind: Mapped[str] = mapped_column(String(10))
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class TimetableSubject(Base):
    __tablename__ = "timetable_subjects"
    __table_args__ = (UniqueConstraint("term_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("academic_terms.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class Faculty(Base):
    __tablename__ = "faculty"
    __table_args__ = (UniqueConstraint("term_id", "initials"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("academic_terms.id", ondelete="CASCADE"), index=True)
    initials: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provenance: Mapped[str] = mapped_column(String(20), default="INFERRED")


class TimetableSection(Base):
    __tablename__ = "timetable_sections"
    __table_args__ = (UniqueConstraint("term_id", "code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("academic_terms.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    division_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    home_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class TimetableSession(Base):
    __tablename__ = "timetable_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("academic_terms.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("timetable_sections.id", ondelete="CASCADE"), index=True)
    batch: Mapped[str] = mapped_column(String(5), default="ALL")
    day: Mapped[str] = mapped_column(String(3))
    start_period: Mapped[int] = mapped_column(Integer)
    end_period: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_subjects.id"), nullable=True)
    faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True, index=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True, index=True)
    room_required: Mapped[bool] = mapped_column(Boolean, default=True)
    room_inferred: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_label: Mapped[str] = mapped_column(String(500))
    block_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")
    version: Mapped[int] = mapped_column(Integer, default=1)


class TimetableSessionFaculty(Base):
    __tablename__ = "timetable_session_faculty"
    __table_args__ = (UniqueConstraint("session_id", "faculty_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("timetable_sessions.id", ondelete="CASCADE"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id", ondelete="CASCADE"), index=True)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")


class OptimizerProposal(Base):
    __tablename__ = "optimizer_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("academic_terms.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")


class NavNode(Base):
    __tablename__ = "nav_nodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    node_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer, index=True)
    node_type: Mapped[str] = mapped_column(String(30))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    room_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")


class NavEdge(Base):
    __tablename__ = "nav_edges"
    __table_args__ = (UniqueConstraint("from_node_id", "to_node_id", "mode"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    from_node_id: Mapped[int] = mapped_column(ForeignKey("nav_nodes.id", ondelete="CASCADE"), index=True)
    to_node_id: Mapped[int] = mapped_column(ForeignKey("nav_nodes.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    distance_m: Mapped[float] = mapped_column(Float, default=0)
    floor_delta: Mapped[int] = mapped_column(Integer, default=0)
    wait_seconds: Mapped[float] = mapped_column(Float, default=0)
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance: Mapped[str] = mapped_column(String(20), default="SYNTHETIC")
