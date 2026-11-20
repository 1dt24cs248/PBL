from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import CATEGORY_OF_ROLE, User
from ..schemas import LoginRequest, TokenOut, UserOut
from ..security import create_access_token, verify_password

router = APIRouter(tags=["auth"])


def _user_out(user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.category = CATEGORY_OF_ROLE.get(user.role)
    return out


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not user.is_active or not verify_password(
        body.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return TokenOut(
        access_token=create_access_token(user.id, user.role), user=_user_out(user)
    )


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get(
    "/admin/users",
    response_model=list[UserOut],
    dependencies=[Depends(require_roles("admin"))],
)
def list_users(db: Session = Depends(get_db)):
    return [_user_out(u) for u in db.scalars(select(User).order_by(User.id))]