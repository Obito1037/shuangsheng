from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.twin_brain import AttemptCreateRequest, AttemptResponse
from app.services.twin_brain.attempt_service import AttemptService

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.post("", response_model=AttemptResponse)
def submit_attempt(
    payload: AttemptCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptResponse:
    try:
        return AttemptService(db).submit(user_id=current_user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
