from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def create(self, *, email: str, password_hash: str, display_name: str) -> User:
        user = User(email=email.lower(), password_hash=password_hash, display_name=display_name)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

