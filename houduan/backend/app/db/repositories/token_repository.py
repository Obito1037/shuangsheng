from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.refresh_token import RefreshToken


class TokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_refresh_token(self, *, user_id: str, token_hash: str, expires_at: datetime, device_id: str | None = None) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at, device_id=device_id)
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(UTC)
        return self.db.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )

    def revoke(self, token: RefreshToken) -> RefreshToken:
        token.revoked_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(token)
        return token

