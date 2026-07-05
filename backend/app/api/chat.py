from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_provider_registry
from app.core.security import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.integrations.registry import ProviderRegistry
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> ChatMessageResponse:
    return ChatService(db, registry).send_message(
        user_id=current_user.id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        twin_id=payload.twin_id,
        mode=payload.mode,
    )


@router.post("/stream", response_model=ChatMessageResponse)
def chat_stream(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> ChatMessageResponse:
    return ChatService(db, registry).stream_message(
        user_id=current_user.id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        twin_id=payload.twin_id,
        mode=payload.mode,
    )
