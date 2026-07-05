from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.twin import (
    BlackboardRequest,
    BlackboardResponse,
    LearningOutputRead,
    LearningTwinRead,
    RouteSimulationResponse,
    TwinCreateRequest,
    TwinSyncResponse,
    TwinUpdateRequest,
    WeakPointRead,
)
from app.services.twin_service import TwinService

router = APIRouter(prefix="/api/twins", tags=["learning twins"])


@router.get("", response_model=list[LearningTwinRead])
def list_twins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LearningTwinRead]:
    return TwinService(db).list_twins(current_user.id)


@router.post("", response_model=LearningTwinRead)
def create_twin(
    payload: TwinCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningTwinRead:
    return TwinService(db).create_twin(
        user_id=current_user.id,
        name=payload.name,
        subject=payload.subject,
        goal=payload.goal,
        stage=payload.stage,
    )


@router.get("/{twin_id}", response_model=LearningTwinRead)
def get_twin(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningTwinRead:
    try:
        return TwinService(db).get_twin(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{twin_id}", response_model=LearningTwinRead)
def update_twin(
    twin_id: str,
    payload: TwinUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningTwinRead:
    try:
        return TwinService(db).update_twin(user_id=current_user.id, twin_id=twin_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{twin_id}")
def delete_twin(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    try:
        TwinService(db).delete_twin(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"ok": True}


@router.post("/{twin_id}/sync", response_model=TwinSyncResponse)
def sync_twin(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TwinSyncResponse:
    try:
        return TwinService(db).sync_twin(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{twin_id}/simulate", response_model=RouteSimulationResponse)
def simulate_routes(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RouteSimulationResponse:
    try:
        return TwinService(db).simulate_routes(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{twin_id}/outputs", response_model=list[LearningOutputRead])
def list_outputs(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LearningOutputRead]:
    try:
        return TwinService(db).list_outputs(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{twin_id}/outputs", response_model=list[LearningOutputRead])
def generate_outputs(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LearningOutputRead]:
    try:
        return TwinService(db).generate_outputs(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{twin_id}/weak-points", response_model=list[WeakPointRead])
def weak_points(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeakPointRead]:
    try:
        return TwinService(db).weak_points(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{twin_id}/blackboard", response_model=BlackboardResponse)
def blackboard(
    twin_id: str,
    payload: BlackboardRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BlackboardResponse:
    try:
        return TwinService(db).blackboard(user_id=current_user.id, twin_id=twin_id, topic=payload.topic if payload else None)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
