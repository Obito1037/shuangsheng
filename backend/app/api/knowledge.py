from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseRead
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])


@router.post("", response_model=KnowledgeBaseRead)
def create_knowledge_base(payload: KnowledgeBaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return KnowledgeService(db).create(user_id=current_user.id, name=payload.name, description=payload.description)


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return KnowledgeService(db).list(current_user.id)

