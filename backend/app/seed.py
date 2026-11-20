"""SYNTHETIC development data. Not real DSATM data."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Building, Room, User
from .security import hash_password

DEV_PASSWORD = "Pass@123"  # synthetic dev password only

USERS = [
    ("admin1", "Synthetic Admin", "admin", None),
    ("maint1", "Synthetic Maintenance", "maintenance", None),
    ("hod_cse", "Synthetic HOD CSE", "hod", "CSE"),
    ("fac1", "Synthetic Faculty 1", "teaching_faculty", "CSE"),
    ("stu1", "Synthetic Student 1", "student", "CSE"),
]


def seed(db: Session) -> None:
    for username, name, role, dept in USERS:
        if db.scalar(select(User).where(User.username == username)) is None:
            db.add(
                User(
                    username=username,
                    full_name=name,
                    role=role,
                    department=dept,
                    password_hash=hash_password(DEV_PASSWORD),
                )
            )
    block = db.scalar(select(Building).where(Building.code == "A"))
    if block is None:
        block = Building(code="A", name="A Block (synthetic layout)", floors=3)
        db.add(block)
        db.flush()
    if not db.scalar(select(Room).where(Room.building_id == block.id)):
        for floor in (1, 2, 3):
            for i in range(1, 5):
                db.add(
                    Room(
                        building_id=block.id,
                        number=f"A{floor}0{i}",
                        floor=floor,
                        capacity=60 if i < 4 else 30,
                        room_type="classroom" if i < 4 else "lab",
                        facilities="projector" if i != 2 else "projector,smartboard",
                    )
                )
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    print("Seeded SYNTHETIC data. Dev password for all users:", DEV_PASSWORD)