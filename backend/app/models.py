from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, UniqueConstraint
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
    building: Mapped[Building] = relationship(back_populates="rooms")
    aliases: Mapped[list["RoomAlias"]] = relationship(back_populates="room", cascade="all, delete-orphan")


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
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")
    division_links: Mapped[list["DivisionSectionMap"]] = relationship(back_populates="student", cascade="all, delete-orphan")


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
    __table_args__ = (UniqueConstraint("student_id", "section_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")
    student: Mapped[Student] = relationship(back_populates="division_links")


class Holiday(Base):
    __tablename__ = "holidays"
    id: Mapped[int] = mapped_column(primary_key=True)
    holiday_date: Mapped[object] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(100))
    provenance: Mapped[str] = mapped_column(String(20), default="REAL_DSATM_PDF")
