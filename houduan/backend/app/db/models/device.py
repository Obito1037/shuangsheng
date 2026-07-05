from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Device(IdMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="unknown")
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

