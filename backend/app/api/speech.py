from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services.spoken_english_service import SpokenEnglishService

router = APIRouter(prefix="/api/speech", tags=["speech"])


@router.post("/english/{file_id}")
def analyze_spoken_english(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return SpokenEnglishService().analyze(user_id=current_user.id, file_id=file_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
