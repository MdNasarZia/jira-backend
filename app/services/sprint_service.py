import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ConflictError, GoneError, NotFoundError
from app.models.enums import IssueStatus, SprintStatus
from app.models.user import User
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.sprint_repository import SprintRepository
from app.schemas.common import PaginatedResponse
from app.schemas.sprint import SprintCreate, SprintResponse, SprintUpdate


class SprintService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sprint_repo = SprintRepository(db)
        self.project_repo = ProjectRepository(db)
        self.issue_repo = IssueRepository(db)

    async def _get_active_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")

    async def create_sprint(
        self, project_id: UUID, data: SprintCreate, current_user: User
    ) -> "Sprint":
        await self._get_active_project(project_id)
        return await self.sprint_repo.create(
            {
                "project_id": project_id,
                "name": data.name,
                "goal": data.goal,
                "start_date": data.start_date,
                "end_date": data.end_date,
                "status": SprintStatus.planned,
                "created_by": current_user.id,
            }
        )

    async def list_sprints(
        self, project_id: UUID, page: int, limit: int
    ) -> PaginatedResponse[SprintResponse]:
        offset = (page - 1) * limit
        items, total = await self.sprint_repo.list_by_project(project_id, offset, limit)
        return PaginatedResponse(
            items=[SprintResponse.model_validate(s) for s in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def get_sprint(self, project_id: UUID, sprint_id: UUID) -> "Sprint":
        sprint = await self.sprint_repo.get_by_id(sprint_id)
        if sprint is None or sprint.project_id != project_id:
            raise NotFoundError("Sprint not found", {"sprint_id": str(sprint_id)})
        return sprint

    async def update_sprint(
        self, project_id: UUID, sprint_id: UUID, data: SprintUpdate
    ) -> "Sprint":
        await self._get_active_project(project_id)
        sprint = await self.get_sprint(project_id, sprint_id)
        if sprint.status != SprintStatus.planned:
            raise ConflictError(
                "Can only update sprints in planned status",
                {"current_status": sprint.status.value},
            )
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return sprint
        return await self.sprint_repo.update(sprint, update_data)

    async def start_sprint(self, project_id: UUID, sprint_id: UUID) -> "Sprint":
        await self._get_active_project(project_id)
        sprint = await self.get_sprint(project_id, sprint_id)
        if sprint.status != SprintStatus.planned:
            raise ConflictError(
                "Only planned sprints can be started",
                {"current_status": sprint.status.value},
            )
        active = await self.sprint_repo.get_active_sprint(project_id)
        if active is not None:
            raise ConflictError(
                "Another sprint is already active in this project",
                {"active_sprint_id": str(active.id)},
            )
        return await self.sprint_repo.update(
            sprint,
            {
                "status": SprintStatus.active,
                "started_at": datetime.now(UTC),
            },
        )

    async def complete_sprint(self, project_id: UUID, sprint_id: UUID) -> "Sprint":
        await self._get_active_project(project_id)
        sprint = await self.get_sprint(project_id, sprint_id)
        if sprint.status != SprintStatus.active:
            raise ConflictError(
                "Only active sprints can be completed",
                {"current_status": sprint.status.value},
            )

        unfinished = await self.issue_repo.get_unfinished_by_sprint(sprint_id)
        if unfinished:
            max_rank = await self.issue_repo.get_max_backlog_rank(project_id)
            issue_ids = [issue.id for issue in unfinished]
            updates = [(issue.id, max_rank + i + 1) for i, issue in enumerate(unfinished)]
            await self.issue_repo.bulk_update_backlog_rank(updates)
            await self.issue_repo.bulk_update_sprint(None, issue_ids)
            await self.issue_repo.bulk_update_status(IssueStatus.backlog, issue_ids)

        return await self.sprint_repo.update(
            sprint,
            {
                "status": SprintStatus.completed,
                "completed_at": datetime.now(UTC),
            },
        )

    async def delete_sprint(self, project_id: UUID, sprint_id: UUID) -> None:
        await self._get_active_project(project_id)
        sprint = await self.get_sprint(project_id, sprint_id)
        if sprint.status != SprintStatus.planned:
            raise ConflictError(
                "Can only delete sprints in planned status",
                {"current_status": sprint.status.value},
            )
        await self.sprint_repo.delete(sprint)
