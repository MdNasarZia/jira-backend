from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProjectRole


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=2, max_length=10, pattern=r"^[A-Z]+$")
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    key: str
    description: str | None
    is_archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    member_count: int = 0


class MemberAddRequest(BaseModel):
    user_id: UUID
    project_role: ProjectRole

    @field_validator("project_role")
    @classmethod
    def role_must_not_be_administrator(cls, v: ProjectRole) -> ProjectRole:
        if v == ProjectRole.administrator:
            raise ValueError("Cannot assign the administrator role directly")
        return v


class MemberUpdateRequest(BaseModel):
    project_role: ProjectRole

    @field_validator("project_role")
    @classmethod
    def role_must_not_be_administrator(cls, v: ProjectRole) -> ProjectRole:
        if v == ProjectRole.administrator:
            raise ValueError("Cannot assign the administrator role directly")
        return v


class MemberUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    project_role: ProjectRole
    joined_at: datetime
    user: MemberUserInfo
