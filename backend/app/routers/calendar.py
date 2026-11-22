from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AcademicTerm, Holiday, User

router = APIRouter(tags=["calendar"])


def _holiday_rows(db: Session) -> list[dict]:
    return [{"date": row.holiday_date.isoformat(), "name": row.name, "source": row.source}
            for row in db.scalars(select(Holiday).order_by(Holiday.holiday_date))]


@router.get("/calendar/holidays")
def list_holidays(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return _holiday_rows(db)


@router.get("/calendar/summary")
def calendar_summary(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    terms = [{"term_code": term.code, "start_date": None, "end_date": None}
             for term in db.scalars(select(AcademicTerm).order_by(AcademicTerm.code))]
    return {"holidays": _holiday_rows(db), "terms": terms,
            "note": "Term start and end dates are not known."}
