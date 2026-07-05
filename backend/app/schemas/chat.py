from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    twin_id: str | None = None
    mode: Literal["twin", "normal"] = "twin"


class ChatMessageResponse(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    answer: str
    provider: str
    model: str
