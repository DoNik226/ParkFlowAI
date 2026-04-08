from back.app.models.login_attempt import LoginAttempt
from back.app.repositories.base_repository import BaseRepository


class LoginAttemptRepository(BaseRepository[LoginAttempt]):
    """Persistence layer for future IP-based login throttling."""

    def __init__(self, db):
        super().__init__(db, LoginAttempt)
