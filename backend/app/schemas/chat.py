from __future__ import annotations

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatMessageResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    answer: str
    provider: str
    model: str

