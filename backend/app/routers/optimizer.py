from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_roles
from ..models import AcademicTerm, OptimizerProposal, User
from ..optimizer.service import solve_energy
from ..room_resolver import resolve_room

router = APIRouter(tags=["optimizer"])


class EnergyRequest(BaseModel):
    term: str
    movable: Literal["inferred_only", "all", "selected_sections"] = "inferred_only"
    sections: list[str] = Field(default_factory=list)
    max_relocations: int | None = Field(default=None, ge=0)
    lock_labs: bool = True
    forbid_floors: list[int] = Field(default_factory=list)
    forbid_rooms: list[str] = Field(default_factory=list)
    close_floors: list[int] = Field(default_factory=list)
    close_rooms: list[str] = Field(default_factory=list)
    lambda_move: float = Field(default=1.0, ge=0)
    lambda_floor: float = Field(default=0.0, ge=0)
    time_limit_s: int = Field(default=30, gt=0, le=3600)
    seed: int = 0

    @model_validator(mode="after")
    def selected_requires_sections(self):
        if self.movable == "selected_sections" and not self.sections:
            raise ValueError("sections is required when movable is selected_sections")
        return self


@router.post("/optimizer/energy")
def optimize_energy(body: EnergyRequest, db: Session = Depends(get_db),
                    user: User = Depends(require_roles("admin"))):
    term = db.scalar(select(AcademicTerm).where(AcademicTerm.code == body.term))
    if term is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Term not found")
    canonical_rooms = []
    for token in body.forbid_rooms + body.close_rooms:
        canonical = resolve_room(token)
        if canonical is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown A-Block room: {token}")
        canonical_rooms.append(canonical)
    if canonical_rooms:
        body = body.model_copy(update={"forbid_rooms": canonical_rooms[:len(body.forbid_rooms)],
                                       "close_rooms": canonical_rooms[len(body.forbid_rooms):]})
    payload = solve_energy(db, term, body)
    proposal = OptimizerProposal(id=payload["id"], term_id=term.id, status="draft",
                                 payload=payload, created_by=user.id, provenance="SYNTHETIC")
    db.add(proposal)
    db.commit()
    return payload
