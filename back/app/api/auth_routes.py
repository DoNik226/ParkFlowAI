from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from back.app.api.deps import get_audit_logger, get_auth_service, get_current_active_user
from back.app.core.exceptions import AccountLockedError, AuthenticationError
from back.app.logger import AuditLogger
from back.app.models.enums import EventEntityType, UserRole
from back.app.models.user import User
from back.app.schemas.auth import TokenResponse
from back.app.schemas.users import AuthUser
from back.app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class LoginPayload(BaseModel):
    login: str | None = Field(default=None)
    username: str | None = Field(default=None)
    password: str

    def get_login(self) -> str:
        value = self.login or self.username
        if not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Field 'login' or 'username' is required",
            )
        return value


def _user_entity_type(role: str) -> str:
    if role in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}:
        return EventEntityType.ADMIN.value
    return EventEntityType.USER.value


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginPayload,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    client_ip = request.client.host if request.client else None

    try:
        token_payload = await auth_service.login(
            data.get_login(),
            data.password,
            client_ip=client_ip,
        )
        audit_logger.log_user_login(
            token_payload["user_id"],
            entity_type=_user_entity_type(token_payload["role"]),
        )
        return token_payload
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "message": "Аккаунт временно заблокирован",
                "locked_until": exc.locked_until.isoformat() if exc.locked_until else None,
            },
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    client_ip = request.client.host if request.client else None

    try:
        token_payload = await auth_service.login(
            form_data.username,
            form_data.password,
            client_ip=client_ip,
        )
        audit_logger.log_user_login(
            token_payload["user_id"],
            entity_type=_user_entity_type(token_payload["role"]),
        )
        return token_payload
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={
                "message": "Аккаунт временно заблокирован",
                "locked_until": exc.locked_until.isoformat() if exc.locked_until else None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
) -> Response:
    audit_logger.log_user_logout(
        current_user.id,
        entity_type=_user_entity_type(current_user.role),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=AuthUser)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user
