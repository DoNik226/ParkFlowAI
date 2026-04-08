from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str = Field(min_length=10, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
