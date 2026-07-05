from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def get_user(self, user_id: str) -> User | None:
        return self.users.get_by_id(user_id)

