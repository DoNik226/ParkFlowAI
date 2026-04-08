from datetime import datetime, timedelta, timezone

from back.app.core.exceptions import AccountLockedError, AuthenticationError
from back.app.core.security import create_access_token, verify_password
from back.app.repositories.user_repository import UserRepository

MAX_FAILED_ATTEMPTS = 5
ACCOUNT_LOCK_MINUTES = 15


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def login(self, login: str, password: str, client_ip: str | None = None):
        # TODO: Persist and enforce client_ip-based rate limiting via login_attempts table.
        user = self.user_repo.get_by_username_or_email(login)

        if not user:
            raise AuthenticationError("Invalid login or password")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        now = datetime.now(timezone.utc)
        if user.locked_until and user.locked_until > now:
            raise AccountLockedError(
                "Account is temporarily locked",
                locked_until=user.locked_until,
            )

        if not verify_password(password, user.password_hash):
            user = self.user_repo.increment_failed_attempts(user)
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                locked_until = now + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
                self.user_repo.lock_user_until(user, locked_until)
                raise AccountLockedError(
                    "Account is temporarily locked",
                    locked_until=locked_until,
                )
            raise AuthenticationError("Invalid login or password")

        if user.failed_attempts or user.locked_until:
            user = self.user_repo.reset_login_state(user)

        access_token = create_access_token({
            "sub": str(user.id),
            "role": user.role,
        })

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role,
            "user_id": user.id,
        }
