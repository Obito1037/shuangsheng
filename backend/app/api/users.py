from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.db.models.user import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

