from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserRead, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, current_user.id)
    if user is None:
        return current_user
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.avatar_data_url is not None:
        user.avatar_data_url = payload.avatar_data_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
