from __future__ import annotations

import secrets
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.security import hash_token
from app.db.models.email_verification import EmailVerificationCode


class EmailCodeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = load_settings()

    def send_code(self, *, email: str, purpose: str) -> int:
        self._validate_purpose(purpose)
        code = self._generate_code()
        expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.email_code_expire_minutes)
        record = EmailVerificationCode(
            email=email.lower(),
            purpose=purpose,
            code_hash=hash_token(code),
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        if self.settings.email_enabled:
            self._send_email(email=email, code=code, purpose=purpose)
        return self.settings.email_code_expire_minutes

    def verify_code(self, *, email: str, purpose: str, code: str) -> str:
        record = self._latest_active(email=email, purpose=purpose)
        if not record or self._expired(record.expires_at) or not secrets.compare_digest(record.code_hash, hash_token(code.strip())):
            raise ValueError("Invalid or expired email verification code")
        verified_token = secrets.token_urlsafe(32)
        record.consumed_at = datetime.now(UTC)
        record.verified_token_hash = hash_token(verified_token)
        record.verified_token_expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.email_code_expire_minutes)
        self.db.commit()
        return verified_token

    def consume_for_registration(self, *, email: str, code: str | None, verified_token: str | None) -> None:
        if not self.settings.email_enabled and not code and not verified_token:
            return
        if verified_token:
            record = self._latest_verified(email=email, purpose="register")
            if (
                not record
                or not record.verified_token_hash
                or self._expired(record.verified_token_expires_at)
                or not secrets.compare_digest(record.verified_token_hash, hash_token(verified_token.strip()))
            ):
                raise ValueError("Email verification is required")
            record.verified_token_hash = None
            record.verified_token_expires_at = None
            self.db.commit()
            return
        if code:
            self.verify_code(email=email, purpose="register", code=code)
            return
        raise ValueError("Email verification is required")

    def _latest_active(self, *, email: str, purpose: str) -> EmailVerificationCode | None:
        return (
            self.db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == email.lower(),
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(desc(EmailVerificationCode.created_at))
            .first()
        )

    def _latest_verified(self, *, email: str, purpose: str) -> EmailVerificationCode | None:
        return (
            self.db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == email.lower(),
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.verified_token_hash.is_not(None),
            )
            .order_by(desc(EmailVerificationCode.updated_at))
            .first()
        )

    def _send_email(self, *, email: str, code: str, purpose: str) -> None:
        if not self.settings.smtp_host or not self.settings.smtp_username or not self.settings.smtp_password:
            raise ValueError("SMTP configuration is incomplete")
        from_email = self.settings.smtp_from_email or self.settings.smtp_username
        message = EmailMessage()
        message["Subject"] = "双生邮箱验证码"
        message["From"] = f"{self.settings.smtp_from_name} <{from_email}>"
        message["To"] = email
        message.set_content(
            f"你的双生验证码是：{code}\n\n"
            f"用途：{purpose}\n"
            f"有效期：{self.settings.email_code_expire_minutes} 分钟。\n"
            "如果不是你本人操作，请忽略这封邮件。"
        )
        if self.settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
            return
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(message)

    def _generate_code(self) -> str:
        length = max(4, min(self.settings.email_code_length, 12))
        upper = 10**length
        return f"{secrets.randbelow(upper):0{length}d}"

    @staticmethod
    def _validate_purpose(purpose: str) -> None:
        if purpose not in {"register", "login"}:
            raise ValueError("Unsupported email verification purpose")

    @staticmethod
    def _expired(value: datetime | None) -> bool:
        if value is None:
            return True
        selected = value if value.tzinfo else value.replace(tzinfo=UTC)
        return selected <= datetime.now(UTC)
