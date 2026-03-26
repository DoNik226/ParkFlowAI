from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from back.app.models.user import User
from back.app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username_or_email(self, login: str) -> Optional[User]:
        return self.db.query(User).filter(
            or_(User.username == login, User.email == login)
        ).first()

    def update_failed_attempts(self, user_id: int, attempts: int) -> Optional[User]:
        return self.update(user_id, failed_attempts=attempts)

    def lock_user(self, user_id: int, locked_until) -> Optional[User]:
        return self.update(user_id, locked_until=locked_until)

    def unlock_user(self, user_id: int) -> Optional[User]:
        return self.update(user_id, failed_attempts=0, locked_until=None)

    def get_active_users(self, skip: int = 0, limit: int = 100):
        return self.db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()