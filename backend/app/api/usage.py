from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.usage import UsageSummary
from app.services.usage_service import UsageService

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/me", response_model=UsageSummary)
def usage_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UsageSummary:
    return UsageService(db).summary(current_user.id)

