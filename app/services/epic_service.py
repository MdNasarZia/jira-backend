import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ConflictError, GoneError, NotFoundError
from app.models.user import User
from app.repositories.epic_repository import EpicRepository
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import PaginatedResponse
from app.schemas.epic import EpicCreate, EpicResponse, EpicUpdate


class EpicService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.epic_repo = EpicRepository(db)
        self.project_repo = ProjectRepository(db)
        self.issue_repo = IssueRepository(db)

    async def _get_active_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")

    async def create_epic(self, project_id: UUID, data: EpicCreate, current_user: User) -> "Epic":
        await self._get_active_project(project_id)
        return await self.epic_repo.create(
            {
                "project_id": project_id,
                "title": data.title,
                "description": data.description,
                "status": data.status,
                "start_date": data.start_date,
                "end_date": data.end_date,
                "created_by": current_user.id,
            }
        )

    async def list_epics(
        self, project_id: UUID, page: int, limit: int
    ) -> PaginatedResponse[EpicResponse]:
        offset = (page - 1) * limit
        items, total = await self.epic_repo.list_by_project(project_id, offset, limit)
        return PaginatedResponse(
            items=[EpicResponse.model_validate(e) for e in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def get_epic(self, project_id: UUID, epic_id: UUID) -> "Epic":
        epic = await self.epic_repo.get_by_id(epic_id)
        if epic is None or epic.project_id != project_id:
            raise NotFoundError("Epic not found", {"epic_id": str(epic_id)})
        return epic

    async def update_epic(
        self,
        project_id: UUID,
        epic_id: UUID,
        data: EpicUpdate,
        current_user: User,
    ) -> "Epic":
        await self._get_active_project(project_id)
        epic = await self.get_epic(project_id, epic_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return epic
        return await self.epic_repo.update(epic, update_data)

    async def delete_epic(self, project_id: UUID, epic_id: UUID, current_user: User) -> None:
        await self._get_active_project(project_id)
        epic = await self.get_epic(project_id, epic_id)

        issues, count = await self.issue_repo.list_by_project(
            project_id, {"epic_id": epic_id}, offset=0, limit=1
        )
        if count > 0:
            raise ConflictError(
                "Cannot delete epic with linked issues",
                {"epic_id": str(epic_id), "issue_count": count},
            )
        await self.epic_repo.delete(epic)
