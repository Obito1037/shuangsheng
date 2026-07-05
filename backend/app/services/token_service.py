from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.db.models.refresh_token import RefreshToken
from app.db.repositories.token_repository import TokenRepository
from app.schemas.token import TokenPair


class TokenService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TokenRepository(db)
        self.settings = load_settings()

    def issue_tokens(self, user_id: str) -> TokenPair:
        refresh_token = create_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_days)
        self.repository.create_refresh_token(user_id=user_id, token_hash=hash_token(refresh_token), expires_at=expires_at)
        return TokenPair(
            access_token=create_access_token(user_id=user_id),
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_minutes * 60,
        )

    def refresh(self, refresh_token: str) -> TokenPair:
        stored = self.validate_refresh_token(refresh_token)
        self.repository.revoke(stored)
        return self.issue_tokens(stored.user_id)

    def validate_refresh_token(self, refresh_token: str) -> RefreshToken:
        stored = self.repository.get_active_by_hash(hash_token(refresh_token))
        if not stored:
            raise ValueError("Invalid refresh token")
        return stored

    def revoke(self, refresh_token: str) -> None:
        stored = self.repository.get_active_by_hash(hash_token(refresh_token))
        if stored:
            self.repository.revoke(stored)
