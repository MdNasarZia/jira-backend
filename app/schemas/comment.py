from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1)


class CommentUpdate(BaseModel):
    body: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    issue_id: UUID
    author_id: UUID
    body: str
    is_edited: bool
    created_at: datetime
    updated_at: datetime
