from datetime import datetime

from pydantic import BaseModel, Field


class AuthUser(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    company_id: int | None = None
    full_name: str | None = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    role: str
    company_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=10, max_length=64)
    is_active: bool = True


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    role: str | None = None
    company_id: int | None = None
    is_active: bool | None = None


class UserPasswordUpdate(BaseModel):
    new_password: str = Field(min_length=10, max_length=64)


class UserBlockUpdate(BaseModel):
    block: bool
    duration_minutes: int = Field(default=15, ge=1, le=1440)


class UserListItem(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    failed_attempts: int
    locked_until: datetime | None = None
    company_id: int | None = None
    full_name: str | None = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    failed_attempts: int
    locked_until: datetime | None = None
    company_id: int | None = None
    full_name: str | None = None

    class Config:
        from_attributes = True