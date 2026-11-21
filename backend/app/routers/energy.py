from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..energy import calculate_energy, calculate_utilization
from ..models import AcademicTerm, User

router = APIRouter(prefix="/energy", tags=["energy"])
ACTIVE_TERM = "2026-27-ODD"


def _term(db: Session, term_code: str | None) -> AcademicTerm:
    row = db.scalar(select(AcademicTerm).where(AcademicTerm.code == (term_code or ACTIVE_TERM)))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Term not found")
    return row


@router.get("/baseline")
def baseline(term: str | None = None, db: Session = Depends(get_db),
             _user: User = Depends(require_roles("admin", "hod"))):
    return calculate_energy(db, _term(db, term))


@router.get("/utilization")
def utilization(term: str | None = None, db: Session = Depends(get_db),
                _user: User = Depends(require_roles("admin", "hod"))):
    return calculate_utilization(db, _term(db, term))
