from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.twin_brain import PlanTaskUpdateRequest, StudyPlanResponse
from app.services.twin_brain.simulator_service import SimulatorService

router = APIRouter(prefix="/api/plans", tags=["study plans"])


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanResponse:
    try:
        return SimulatorService(db).get_plan(user_id=current_user.id, plan_id=plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{plan_id}/tasks/{task_id}", response_model=StudyPlanResponse)
def update_task(
    plan_id: str,
    task_id: str,
    payload: PlanTaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanResponse:
    try:
        return SimulatorService(db).update_task(user_id=current_user.id, plan_id=plan_id, task_id=task_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
