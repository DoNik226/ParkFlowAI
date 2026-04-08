from datetime import datetime, timedelta, timezone

from back.app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from back.app.core.security import hash_password
from back.app.models.enums import UserRole
from back.app.repositories.user_repository import UserRepository
from back.app.schemas.users import UserBlockUpdate, UserCreate, UserUpdate


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def list_users(self):
        return self.user_repo.list_all()

    def get_user(self, user_id: int):
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found")
        return user

    def create_user(self, data: UserCreate):
        self._validate_role(data.role)
        self._ensure_unique_fields(data.username, data.email)
        return self.user_repo.create(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active,
        )

    def update_user(self, user_id: int, data: UserUpdate):
        user = self.get_user(user_id)
        self._validate_role(data.role)
        self._ensure_unique_fields(data.username, data.email, exclude_user_id=user_id)
        updated_user = self.user_repo.update(
            user.id,
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active,
        )
        return updated_user

    def update_password(self, user_id: int, new_password: str):
        user = self.get_user(user_id)
        return self.user_repo.set_password_hash(user, hash_password(new_password))

    def set_block_status(self, user_id: int, data: UserBlockUpdate):
        user = self.get_user(user_id)
        if data.block:
            locked_until = datetime.now(timezone.utc) + timedelta(minutes=data.duration_minutes)
            return self.user_repo.update(
                user.id,
                failed_attempts=5,
                locked_until=locked_until,
            )
        return self.user_repo.update(
            user.id,
            failed_attempts=0,
            locked_until=None,
        )

    def delete_user(self, user_id: int):
        user = self.get_user(user_id)
        self.user_repo.delete(user.id)

    def _ensure_unique_fields(
        self,
        username: str,
        email: str,
        exclude_user_id: int | None = None,
    ) -> None:
        if self.user_repo.username_exists(username, exclude_user_id=exclude_user_id):
            raise UserAlreadyExistsError("Username already exists")
        if self.user_repo.email_exists(email, exclude_user_id=exclude_user_id):
            raise UserAlreadyExistsError("Email already exists")

    def _validate_role(self, role: str) -> None:
        allowed_roles = {UserRole.USER.value, UserRole.ADMIN.value}
        if role not in allowed_roles:
            raise ValueError(f"Unsupported role: {role}")
