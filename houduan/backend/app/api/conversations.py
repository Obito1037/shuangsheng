from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationRead
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ConversationService(db).list(current_user.id)


@router.post("", response_model=ConversationRead)
def create_conversation(payload: ConversationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ConversationService(db).create(user_id=current_user.id, title=payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation, messages = ConversationService(db).detail(user_id=current_user.id, conversation_id=conversation_id)
    return ConversationDetail(conversation=conversation, messages=messages)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ConversationService(db).delete(user_id=current_user.id, conversation_id=conversation_id)
    return {"ok": True}

