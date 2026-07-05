from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.user import UserRead
from app.services.email_code_service import EmailCodeService
from app.services.token_service import TokenService


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenService(db)

    def register(self, payload: RegisterRequest) -> AuthResponse:
        if self.users.get_by_email(payload.email):
            raise ValueError("Email already registered")
        EmailCodeService(self.db).consume_for_registration(
            email=str(payload.email),
            code=payload.email_code,
            verified_token=payload.verified_token,
        )
        display_name = payload.display_name or payload.email.split("@", 1)[0]
        user = self.users.create(email=payload.email, password_hash=hash_password(payload.password), display_name=display_name)
        return AuthResponse(user=UserRead.model_validate(user), tokens=self.tokens.issue_tokens(user.id))

    def login(self, payload: LoginRequest) -> AuthResponse:
        account = payload.resolved_account.strip()
        if "@" not in account:
            raise ValueError("Only email account login is supported in this local backend phase")
        user = self.users.get_by_email(account)
        if not user or not verify_password(payload.password, user.password_hash):
            raise ValueError("Invalid email or password")
        return AuthResponse(user=UserRead.model_validate(user), tokens=self.tokens.issue_tokens(user.id))

    def logout(self, refresh_token: str) -> None:
        self.tokens.revoke(refresh_token)

    def current_user(self, user: User) -> User:
        return user
