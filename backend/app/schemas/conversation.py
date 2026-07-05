from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    title: str


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    conversation: ConversationRead
    messages: list[MessageRead]

