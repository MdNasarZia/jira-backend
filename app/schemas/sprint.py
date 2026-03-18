from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SprintStatus


class SprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class SprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    goal: str | None
    status: SprintStatus
    start_date: date | None
    end_date: date | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
