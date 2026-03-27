from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from services.auth_service import AuthService
from schemas.auth import LoginRequest

from typing import Annotated

security = HTTPBasic()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/login")
async def login(data: LoginRequest, auth_service: AuthService = Depends()):
    try:
        return await auth_service.login(data.login, data.password)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Неверный логин или пароль"
        )
