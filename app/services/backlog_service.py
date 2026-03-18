import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ConflictError, GoneError, NotFoundError, ValidationError
from app.models.enums import SprintStatus
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.sprint_repository import SprintRepository
from app.schemas.backlog import BacklogReorderRequest, MoveToSprintRequest
from app.schemas.common import PaginatedResponse
from app.schemas.issue import IssueResponse


class BacklogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.issue_repo = IssueRepository(db)
        self.project_repo = ProjectRepository(db)
        self.sprint_repo = SprintRepository(db)

    async def _get_active_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")

    async def get_backlog(
        self, project_id: UUID, page: int, limit: int
    ) -> PaginatedResponse[IssueResponse]:
        offset = (page - 1) * limit
        items, total = await self.issue_repo.list_backlog_paginated(project_id, offset, limit)
        return PaginatedResponse(
            items=[IssueResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def reorder_backlog(
        self, project_id: UUID, data: BacklogReorderRequest
    ) -> list[IssueResponse]:
        await self._get_active_project(project_id)

        updates = []
        for rank, issue_id in enumerate(data.issue_ids, start=1):
            issue = await self.issue_repo.get_by_id(issue_id)
            if issue is None or issue.project_id != project_id:
                raise NotFoundError("Issue not found", {"issue_id": str(issue_id)})
            if issue.sprint_id is not None:
                raise ValidationError(
                    "Issue is assigned to a sprint and not in backlog",
                    {"issue_id": str(issue_id)},
                )
            updates.append((issue_id, rank))

        await self.issue_repo.bulk_update_backlog_rank(updates)

        backlog_items = await self.issue_repo.list_backlog(project_id)
        return [IssueResponse.model_validate(i) for i in backlog_items]

    async def move_to_sprint(
        self,
        project_id: UUID,
        issue_id: UUID,
        data: MoveToSprintRequest,
    ) -> IssueResponse:
        await self._get_active_project(project_id)

        issue = await self.issue_repo.get_by_id(issue_id)
        if issue is None or issue.project_id != project_id:
            raise NotFoundError("Issue not found", {"issue_id": str(issue_id)})

        sprint = await self.sprint_repo.get_by_id(data.sprint_id)
        if sprint is None or sprint.project_id != project_id:
            raise NotFoundError("Sprint not found", {"sprint_id": str(data.sprint_id)})
        if sprint.status == SprintStatus.completed:
            raise ConflictError(
                "Cannot move issues to a completed sprint",
                {"sprint_id": str(data.sprint_id)},
            )

        issue = await self.issue_repo.update(issue, {"sprint_id": data.sprint_id})
        return IssueResponse.model_validate(issue)
