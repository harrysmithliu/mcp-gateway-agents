from pydantic import BaseModel, Field


class AdminUserResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    is_active: bool
    roles: list[str]


class CreateAdminUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=12, max_length=256)
    roles: list[str] = Field(..., min_length=1)


class ReplaceAdminUserRolesRequest(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class UpdateAdminUserActivityRequest(BaseModel):
    is_active: bool
