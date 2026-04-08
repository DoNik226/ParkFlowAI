class AppError(Exception):
    """Base application error."""


class AuthenticationError(AppError):
    """Authentication failed."""


class AccountLockedError(AppError):
    """Account is temporarily locked."""

    def __init__(self, message: str, locked_until=None):
        super().__init__(message)
        self.locked_until = locked_until


class AuthorizationError(AppError):
    """User does not have enough permissions."""


class UserAlreadyExistsError(AppError):
    """User uniqueness validation failed."""


class UserNotFoundError(AppError):
    """User was not found."""
