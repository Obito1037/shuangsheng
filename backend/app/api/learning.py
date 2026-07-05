from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.learning import LearningRecordRead
from app.services.learning_service import LearningService

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("", response_model=list[LearningRecordRead])
def list_learning(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return LearningService(db).list(current_user.id)

