from uuid import UUID

from pydantic import BaseModel


class BacklogReorderRequest(BaseModel):
    issue_ids: list[UUID]


class MoveToSprintRequest(BaseModel):
    sprint_id: UUID
