from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.twin_brain import MistakeCreateRequest, MistakeRead, MistakeUpdateRequest, VariantQuestionsResponse
from app.services.twin_brain.mistake_service import MistakeService

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])


@router.get("", response_model=list[MistakeRead])
def list_mistakes(
    twin_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MistakeRead]:
    try:
        return MistakeService(db).list_mistakes(user_id=current_user.id, twin_id=twin_id, status=status_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=MistakeRead)
def create_mistake(
    payload: MistakeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MistakeRead:
    try:
        return MistakeService(db).create_manual(user_id=current_user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{mistake_id}", response_model=MistakeRead)
def update_mistake(
    mistake_id: str,
    payload: MistakeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MistakeRead:
    try:
        return MistakeService(db).update_mistake(user_id=current_user.id, mistake_id=mistake_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{mistake_id}/variants", response_model=VariantQuestionsResponse)
def generate_variants(
    mistake_id: str,
    count: int = Query(default=2, ge=1, le=5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VariantQuestionsResponse:
    try:
        return MistakeService(db).generate_variants(user_id=current_user.id, mistake_id=mistake_id, count=count)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
