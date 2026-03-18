from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import SystemRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    system_role: SystemRole
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class UpdateRoleRequest(BaseModel):
    system_role: SystemRole
