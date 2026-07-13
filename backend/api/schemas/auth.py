from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    browser_session_id: str | None = Field(default=None, min_length=1)


class AuthUserResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    roles: list[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    auth_session_id: str
    user: AuthUserResponse
