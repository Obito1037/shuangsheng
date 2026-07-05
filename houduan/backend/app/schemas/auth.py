from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, model_validator

from app.schemas.token import TokenPair
from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    phone: str | None = None


class LoginRequest(BaseModel):
    login_type: str = "password"
    account: str | None = None
    email: EmailStr | None = None
    password: str
    device: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_account(self) -> LoginRequest:
        if self.login_type != "password":
            raise ValueError("Only password login is supported in this local backend phase")
        if not self.account and not self.email:
            raise ValueError("account or email is required")
        return self

    @property
    def resolved_account(self) -> str:
        return self.account or str(self.email)


class LogoutRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair
