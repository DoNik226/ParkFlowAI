from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from back.app.api.deps import get_audit_logger, get_auth_service, get_current_active_user
from back.app.api.stub_utils import not_implemented_response
from back.app.logger import AuditLogger
from back.app.core.exceptions import AccountLockedError, AuthenticationError
from back.app.models.enums import UserRole
from back.app.models.user import User
from back.app.schemas.auth import LoginRequest, TokenResponse
from back.app.schemas.stubs import ForgotPasswordRequest, MessageResponse
from back.app.schemas.users import AuthUser
from back.app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    audit_logger: Annotated[AuditLogger, Depends(get_audit_logger)],
):
    client_ip = request.client.host if request.client else None
    try:
        token_payload = await auth_service.login(data.login, data.password, client_ip=client_ip)
        entity_type = (
            UserRole.ADMIN.value
            if token_payload["role"] == UserRole.ADMIN.value
            else UserRole.USER.value
        )
        audit_logger.log_user_login(token_payload["user_id"], entity_type=entity_type)
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
        entity_type = (
            UserRole.ADMIN.value
            if token_payload["role"] == UserRole.ADMIN.value
            else UserRole.USER.value
        )
        audit_logger.log_user_login(token_payload["user_id"], entity_type=entity_type)
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
    entity_type = UserRole.ADMIN.value if current_user.role == UserRole.ADMIN.value else UserRole.USER.value
    audit_logger.log_user_logout(current_user.id, entity_type=entity_type)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest):
    return not_implemented_response(
        method="POST",
        path="/auth/forgot-password",
        contract="Reset password flow and send a new password to the user's email",
    )


@router.get("/me", response_model=AuthUser)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user
