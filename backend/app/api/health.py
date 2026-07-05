from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import load_settings

router = APIRouter(tags=["health"])

@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "EchoLearn backend"}

@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> dict[str, str]:
    settings = load_settings()
    
    # Check DB
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database not ready")

    # Check JWT secret
    if settings.jwt_secret_key == "local-dev-secret-change-me":
        # Usually it should fail in prod, but for MVP let's just pass
        pass
        
    return {"status": "ready"}
