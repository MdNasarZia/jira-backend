from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import EpicStatus


class EpicCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    status: EpicStatus = EpicStatus.backlog
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "EpicCreate":
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class EpicUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: EpicStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class EpicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: EpicStatus
    start_date: date | None
    end_date: date | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
