from datetime import datetime, timedelta, timezone

from back.app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from back.app.core.security import hash_password
from back.app.models.enums import UserRole
from back.app.models.user import User
from back.app.repositories.user_repository import UserRepository
from back.app.schemas.users import UserBlockUpdate, UserCreate, UserUpdate


class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def list_users(self, current_user: User):
        if current_user.role == UserRole.SUPER_ADMIN.value:
            return self.user_repo.list_all()

        if current_user.company_id is None:
            return []

        return self.user_repo.list_by_company(current_user.company_id)

    def get_user(self, user_id: int, current_user: User | None = None):
        user = self.user_repo.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError("User not found")

        if current_user is not None:
            self._ensure_user_access(current_user, user)

        return user

    def create_user(self, data: UserCreate, current_user: User):
        self._validate_role_for_create(data.role, current_user)
        self._ensure_unique_fields(data.username, data.email)

        company_id = self._resolve_company_id_for_new_user(
            current_user=current_user,
            requested_company_id=data.company_id,
        )

        return self.user_repo.create(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            company_id=company_id,
            is_active=data.is_active,
        )

    def update_user(self, user_id: int, data: UserUpdate, current_user: User):
        user = self.get_user(user_id, current_user=current_user)

        update_data = data.model_dump(exclude_unset=True)

        if "role" in update_data and update_data["role"] is not None:
            self._validate_role_for_update(update_data["role"], current_user)

        if "username" in update_data and update_data["username"] is not None:
            self._ensure_unique_username(
                update_data["username"],
                exclude_user_id=user_id,
            )

        if "email" in update_data and update_data["email"] is not None:
            self._ensure_unique_email(
                update_data["email"],
                exclude_user_id=user_id,
            )

        if current_user.role != UserRole.SUPER_ADMIN.value:
            update_data.pop("company_id", None)
        elif "company_id" in update_data and update_data["company_id"] is None:
            raise ValueError("company_id is required")

        return self.user_repo.update(user.id, **update_data)

    def update_password(self, user_id: int, new_password: str, current_user: User):
        user = self.get_user(user_id, current_user=current_user)
        return self.user_repo.set_password_hash(user, hash_password(new_password))

    def set_block_status(self, user_id: int, data: UserBlockUpdate, current_user: User):
        user = self.get_user(user_id, current_user=current_user)

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

    def delete_user(self, user_id: int, current_user: User):
        user = self.get_user(user_id, current_user=current_user)

        if user.id == current_user.id:
            raise ValueError("You cannot delete yourself")

        self.user_repo.delete(user.id)

    def _resolve_company_id_for_new_user(
        self,
        current_user: User,
        requested_company_id: int | None,
    ) -> int:
        if current_user.role == UserRole.SUPER_ADMIN.value:
            if requested_company_id is None:
                raise ValueError("company_id is required")

            return requested_company_id

        if current_user.role == UserRole.ADMIN.value:
            if current_user.company_id is None:
                raise ValueError("Current admin is not assigned to company")

            return current_user.company_id

        raise ValueError("Only admin can create users")

    def _ensure_user_access(self, current_user: User, target_user: User) -> None:
        if current_user.role == UserRole.SUPER_ADMIN.value:
            return

        if current_user.company_id is None:
            raise UserNotFoundError("User not found")

        if target_user.company_id != current_user.company_id:
            raise UserNotFoundError("User not found")

    def _ensure_unique_fields(
        self,
        username: str,
        email: str,
        exclude_user_id: int | None = None,
    ) -> None:
        self._ensure_unique_username(username, exclude_user_id=exclude_user_id)
        self._ensure_unique_email(email, exclude_user_id=exclude_user_id)

    def _ensure_unique_username(
        self,
        username: str,
        exclude_user_id: int | None = None,
    ) -> None:
        if self.user_repo.username_exists(username, exclude_user_id=exclude_user_id):
            raise UserAlreadyExistsError("Username already exists")

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: int | None = None,
    ) -> None:
        if self.user_repo.email_exists(email, exclude_user_id=exclude_user_id):
            raise UserAlreadyExistsError("Email already exists")

    def _validate_role_for_create(self, role: str, current_user: User) -> None:
        allowed_roles = {
            UserRole.USER.value,
            UserRole.ADMIN.value,
        }

        if current_user.role == UserRole.SUPER_ADMIN.value:
            allowed_roles.add(UserRole.SUPER_ADMIN.value)

        if role not in allowed_roles:
            raise ValueError(f"Unsupported role: {role}")

    def _validate_role_for_update(self, role: str, current_user: User) -> None:
        allowed_roles = {
            UserRole.USER.value,
            UserRole.ADMIN.value,
        }

        if current_user.role == UserRole.SUPER_ADMIN.value:
            allowed_roles.add(UserRole.SUPER_ADMIN.value)

        if role not in allowed_roles:
            raise ValueError(f"Unsupported role: {role}")