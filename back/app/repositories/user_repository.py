from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

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
        return (
            self.db.query(User)
            .filter(or_(User.username == login, User.email == login))
            .first()
        )

    def username_exists(self, username: str, exclude_user_id: int | None = None) -> bool:
        query = self.db.query(User).filter(User.username == username)

        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)

        return self.db.query(query.exists()).scalar()

    def email_exists(self, email: str, exclude_user_id: int | None = None) -> bool:
        query = self.db.query(User).filter(User.email == email)

        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)

        return self.db.query(query.exists()).scalar()

    def list_all(self) -> list[User]:
        return self.db.query(User).order_by(User.id.asc()).all()

    def list_by_company(self, company_id: int) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.company_id == company_id)
            .order_by(User.id.asc())
            .all()
        )

    def get_by_id_and_company(self, user_id: int, company_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.id == user_id)
            .filter(User.company_id == company_id)
            .first()
        )

    def update_failed_attempts(self, user_id: int, attempts: int) -> Optional[User]:
        return self.update(user_id, failed_attempts=attempts)

    def increment_failed_attempts(self, user: User) -> User:
        user.failed_attempts += 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def lock_user_until(self, user: User, locked_until: datetime) -> User:
        user.locked_until = locked_until
        self.db.commit()
        self.db.refresh(user)
        return user

    def reset_login_state(self, user: User) -> User:
        user.failed_attempts = 0
        user.locked_until = None
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_active_users(self, skip: int = 0, limit: int = 100):
        return (
            self.db.query(User)
            .filter(User.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )