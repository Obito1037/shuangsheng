from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uuid_str() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


def import_models() -> None:
    from app.db.models import (  # noqa: F401
        conversation,
        device,
        document,
        document_chunk,
        email_verification,
        file,
        knowledge_base,
        learning_record,
        learning_twin,
        message,
        rag_reference,
        rag_run,
        refresh_token,
        twin_brain,
        usage_record,
        user,
    )
