from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class EmailVerificationCode(IdMixin, TimestampMixin, Base):
    __tablename__ = "email_verification_codes"

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_token_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    verified_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
