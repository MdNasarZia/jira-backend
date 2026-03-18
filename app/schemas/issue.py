from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IssuePriority, IssueStatus, IssueType


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    type: IssueType
    priority: IssuePriority = IssuePriority.medium
    description: str | None = None
    epic_id: UUID | None = None
    parent_id: UUID | None = None
    sprint_id: UUID | None = None
    story_points: int | None = Field(None, ge=0, le=100)
    assignee_id: UUID | None = None


class IssueUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: IssuePriority | None = None
    story_points: int | None = Field(None, ge=0, le=100)
    assignee_id: UUID | None = None
    epic_id: UUID | None = None
    sprint_id: UUID | None = None


class StatusChangeRequest(BaseModel):
    status: IssueStatus


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    epic_id: UUID | None
    parent_id: UUID | None
    sprint_id: UUID | None
    type: IssueType
    title: str
    description: str | None
    status: IssueStatus
    priority: IssuePriority
    story_points: int | None
    assignee_id: UUID | None
    reporter_id: UUID
    backlog_rank: int
    created_at: datetime
    updated_at: datetime


class IssueStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_id: UUID
    changed_by: UUID
    from_status: IssueStatus | None
    to_status: IssueStatus
    changed_at: datetime
