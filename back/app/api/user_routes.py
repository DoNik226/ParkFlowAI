from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from back.app.api.deps import get_user_service, require_admin
from back.app.core.exceptions import UserAlreadyExistsError, UserNotFoundError
from back.app.models.user import User
from back.app.schemas.users import (
    UserBlockUpdate,
    UserCreate,
    UserListItem,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)
from back.app.services.user_service import UserService

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def _raise_user_http_error(exc: Exception) -> None:
    if isinstance(exc, UserNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    if isinstance(exc, UserAlreadyExistsError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    raise exc


@router.get("", response_model=list[UserListItem])
async def list_users(
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return user_service.list_users(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        return user_service.get_user(user_id, current_user=current_user)
    except Exception as exc:
        _raise_user_http_error(exc)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        return user_service.create_user(data, current_user=current_user)
    except Exception as exc:
        _raise_user_http_error(exc)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        return user_service.update_user(user_id, data, current_user=current_user)
    except Exception as exc:
        _raise_user_http_error(exc)


@router.put("/{user_id}/password", response_model=UserResponse)
async def update_user_password(
    user_id: int,
    data: UserPasswordUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        return user_service.update_password(
            user_id,
            data.new_password,
            current_user=current_user,
        )
    except Exception as exc:
        _raise_user_http_error(exc)


@router.put("/{user_id}/block", response_model=UserResponse)
async def block_or_unblock_user(
    user_id: int,
    data: UserBlockUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        return user_service.set_block_status(
            user_id,
            data,
            current_user=current_user,
        )
    except Exception as exc:
        _raise_user_http_error(exc)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    try:
        user_service.delete_user(user_id, current_user=current_user)
    except Exception as exc:
        _raise_user_http_error(exc)