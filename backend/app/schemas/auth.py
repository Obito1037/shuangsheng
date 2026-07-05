from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, model_validator

from app.schemas.token import TokenPair
from app.schemas.user import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    phone: str | None = None
    email_code: str | None = None
    verified_token: str | None = None


class EmailCodeRequest(BaseModel):
    email: EmailStr
    purpose: Literal["register"] = "register"


class EmailCodeVerifyRequest(EmailCodeRequest):
    code: str


class EmailCodeResponse(BaseModel):
    ok: bool
    expires_in_minutes: int


class EmailCodeVerifyResponse(BaseModel):
    ok: bool
    verified_token: str


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
