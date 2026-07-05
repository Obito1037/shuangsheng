from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    AuthResponse,
    EmailCodeRequest,
    EmailCodeResponse,
    EmailCodeVerifyRequest,
    EmailCodeVerifyResponse,
    LoginRequest,
    LogoutRequest,
    RegisterRequest,
)
from app.schemas.token import RefreshTokenRequest, TokenPair
from app.services.auth_service import AuthService
from app.services.email_code_service import EmailCodeService
from app.services.token_service import TokenService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return AuthService(db).register(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/email/send-code", response_model=EmailCodeResponse)
def send_email_code(payload: EmailCodeRequest, db: Session = Depends(get_db)) -> EmailCodeResponse:
    try:
        expires = EmailCodeService(db).send_code(email=str(payload.email), purpose=payload.purpose)
        return EmailCodeResponse(ok=True, expires_in_minutes=expires)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/email/verify-code", response_model=EmailCodeVerifyResponse)
def verify_email_code(payload: EmailCodeVerifyRequest, db: Session = Depends(get_db)) -> EmailCodeVerifyResponse:
    try:
        token = EmailCodeService(db).verify_code(email=str(payload.email), purpose=payload.purpose, code=payload.code)
        return EmailCodeVerifyResponse(ok=True, verified_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return AuthService(db).login(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        return TokenService(db).refresh(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    AuthService(db).logout(payload.refresh_token)
    return {"ok": True}
