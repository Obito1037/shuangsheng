from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class LearningTwin(IdMixin, TimestampMixin, Base):
    __tablename__ = "learning_twins"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    stage: Mapped[str] = mapped_column(String(200), nullable=False, default="同步资料中")
    status: Mapped[str] = mapped_column(String(120), nullable=False, default="等待同步")
    sync_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    memories_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    route_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    outputs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
