from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
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


def _sse(events: Iterator[dict]) -> Iterator[str]:
    for item in events:
        event = item.get("event", "message")
        data = json.dumps(item.get("data", {}), ensure_ascii=False)
        yield f"event: {event}\ndata: {data}\n\n"


@router.post("/stream")
def chat_stream(
    payload: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> StreamingResponse:
    events = ChatService(db, registry).stream_message_events(
        user_id=current_user.id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        twin_id=payload.twin_id,
        mode=payload.mode,
    )
    return StreamingResponse(
        _sse(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
