from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from back.app.core.exceptions import AuthorizationError
from back.app.core.security import decode_access_token
from back.app.database import get_db
from back.app.models.enums import UserRole
from back.app.models.user import User
from back.app.logger import AuditLogger, EventLogger
from back.app.repositories.camera_repository import CameraRepository
from back.app.repositories.event_log_repository import EventLogRepository
from back.app.repositories.parking_repository import ParkingRepository
from back.app.repositories.user_repository import UserRepository
from back.app.services.auth_service import AuthService
from back.app.services.event_service import EventService
from back.app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_user_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repository)


def get_parking_repository(
    db: Annotated[Session, Depends(get_db)],
) -> ParkingRepository:
    return ParkingRepository(db)


def get_camera_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CameraRepository:
    return CameraRepository(db)


def get_event_log_repository(
    db: Annotated[Session, Depends(get_db)],
) -> EventLogRepository:
    return EventLogRepository(db)


def get_event_service(
    event_log_repository: Annotated[EventLogRepository, Depends(get_event_log_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    camera_repository: Annotated[CameraRepository, Depends(get_camera_repository)],
    parking_repository: Annotated[ParkingRepository, Depends(get_parking_repository)],
) -> EventService:
    return EventService(
        event_log_repository=event_log_repository,
        user_repository=user_repository,
        camera_repository=camera_repository,
        parking_repository=parking_repository,
    )


def get_event_logger(
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> EventLogger:
    return EventLogger(event_service)


def get_audit_logger(
    event_service: Annotated[EventService, Depends(get_event_service)],
) -> AuditLogger:
    return AuditLogger(event_service)


def get_user_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(user_repository)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user = user_repository.get_by_id(int(user_id))
    except ValueError:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(AuthorizationError("Admin role required")),
        )
    return current_user
