from repositories.user_repository import UserRepository
from core.security import verify_password, create_access_token


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def login(self, login: str, password: str):
        user = await self.user_repo.get_by_login(login)

        if not user:
            raise Exception("Invalid login or password")

        if not verify_password(password, user.password_hash):
            raise Exception("Invalid login or password")

        access_token = create_access_token({
            "sub": str(user.id),
            "role": user.role
        })

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role
        }
