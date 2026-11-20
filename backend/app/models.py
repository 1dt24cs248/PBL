from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

ROLES = ("student", "teaching_faculty", "hod", "admin", "maintenance")
ROOM_STATUSES = (
    "available",
    "occupied",
    "reserved",
    "under_maintenance",
    "temporarily_unavailable",
)
CATEGORY_OF_ROLE = {
    "student": "Student",
    "teaching_faculty": "Faculty",
    "hod": "Faculty",
    "admin": "Management",
    "maintenance": "Management",
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


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    floors: Mapped[int] = mapped_column(Integer, default=1)

    rooms: Mapped[list["Room"]] = relationship(back_populates="building")


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("building_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"))
    number: Mapped[str] = mapped_column(String(20))
    floor: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    room_type: Mapped[str] = mapped_column(String(20), default="classroom")
    facilities: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(30), default="available")
    version: Mapped[int] = mapped_column(Integer, default=1)

    building: Mapped[Building] = relationship(back_populates="rooms")