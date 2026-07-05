from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_provider_registry
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.integrations.registry import ProviderRegistry
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
from app.schemas.memory_map import MemoryMapResponse
from app.schemas.twin_brain import DiagnoseResponse, QuestionRead, ReviewQueueItemRead, StudyPlanResponse, TwinProfileResponse
from app.services.twin_service import TwinService
from app.services.twin_brain.memory_map_service import MemoryMapService
from app.services.twin_brain.profile_service import TwinProfileService
from app.services.twin_brain.scheduler_service import ReviewSchedulerService
from app.services.twin_brain.selector_service import QuestionSelectorService
from app.services.twin_brain.simulator_service import SimulatorService

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


@router.get("/{twin_id}/profile", response_model=TwinProfileResponse)
def twin_profile(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TwinProfileResponse:
    try:
        return TwinProfileService(db).get_profile(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{twin_id}/memory-map", response_model=MemoryMapResponse)
def twin_memory_map(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemoryMapResponse:
    """分身记忆可视化：RAG 文本向量的 2D 投影 + 知识点图谱。"""
    try:
        return MemoryMapService(db).get_map(user_id=current_user.id, twin_id=twin_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{twin_id}/questions", response_model=list[QuestionRead])
def twin_questions(
    twin_id: str,
    mode: str = Query(default="practice", pattern="^(practice|diagnostic|explore)$"),
    limit: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[QuestionRead]:
    try:
        return QuestionSelectorService(db).list_questions(user_id=current_user.id, twin_id=twin_id, mode=mode, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{twin_id}/diagnose", response_model=DiagnoseResponse)
def diagnose_twin(
    twin_id: str,
    limit: int = Query(default=8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnoseResponse:
    try:
        return QuestionSelectorService(db).diagnose(user_id=current_user.id, twin_id=twin_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{twin_id}/review-queue", response_model=list[ReviewQueueItemRead])
def review_queue(
    twin_id: str,
    limit: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReviewQueueItemRead]:
    try:
        return ReviewSchedulerService(db).review_queue(user_id=current_user.id, twin_id=twin_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{twin_id}/plans", response_model=StudyPlanResponse)
def create_plan(
    twin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanResponse:
    try:
        return SimulatorService(db).create_plan(user_id=current_user.id, twin_id=twin_id)
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
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> BlackboardResponse:
    try:
        return TwinService(db, registry=registry).blackboard(user_id=current_user.id, twin_id=twin_id, topic=payload.topic if payload else None)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
