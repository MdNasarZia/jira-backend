import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ForbiddenError, GoneError, NotFoundError, ValidationError
from app.models.enums import ALLOWED_TRANSITIONS, IssueStatus, IssueType, ProjectRole, SystemRole
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.epic_repository import EpicRepository
from app.repositories.issue_repository import IssueRepository
from app.repositories.issue_status_history_repository import IssueStatusHistoryRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.sprint_repository import SprintRepository
from app.schemas.common import PaginatedResponse
from app.schemas.issue import (
    IssueCreate,
    IssueResponse,
    IssueStatusHistoryResponse,
    IssueUpdate,
    StatusChangeRequest,
)


class IssueService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.issue_repo = IssueRepository(db)
        self.project_repo = ProjectRepository(db)
        self.epic_repo = EpicRepository(db)
        self.sprint_repo = SprintRepository(db)
        self.history_repo = IssueStatusHistoryRepository(db)

    async def _get_active_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")

    def _check_developer_ownership(
        self,
        current_user: User,
        project_member: ProjectMember | None,
        issue: "Issue",
    ) -> None:
        if current_user.system_role == SystemRole.admin:
            return
        if project_member is None:
            return
        if project_member.project_role == ProjectRole.developer:
            if issue.assignee_id != current_user.id:
                raise ForbiddenError("Developers can only update their own issues")

    async def create_issue(
        self,
        project_id: UUID,
        data: IssueCreate,
        current_user: User,
    ) -> "Issue":
        await self._get_active_project(project_id)

        if data.epic_id is not None:
            if data.type != IssueType.story:
                raise ValidationError(
                    "Only stories can be linked to an epic",
                    {"type": data.type.value},
                )
            epic = await self.epic_repo.get_by_id(data.epic_id)
            if epic is None or epic.project_id != project_id:
                raise NotFoundError("Epic not found", {"epic_id": str(data.epic_id)})

        if data.parent_id is not None:
            if data.type == IssueType.story:
                raise ValidationError(
                    "Stories cannot have a parent issue",
                    {"type": data.type.value},
                )
            parent = await self.issue_repo.get_by_id(data.parent_id)
            if parent is None or parent.project_id != project_id:
                raise NotFoundError(
                    "Parent issue not found",
                    {"parent_id": str(data.parent_id)},
                )

        if data.sprint_id is not None:
            sprint = await self.sprint_repo.get_by_id(data.sprint_id)
            if sprint is None or sprint.project_id != project_id:
                raise NotFoundError(
                    "Sprint not found",
                    {"sprint_id": str(data.sprint_id)},
                )

        max_rank = await self.issue_repo.get_max_backlog_rank(project_id)

        issue = await self.issue_repo.create(
            {
                "project_id": project_id,
                "title": data.title,
                "type": data.type,
                "priority": data.priority,
                "description": data.description,
                "epic_id": data.epic_id,
                "parent_id": data.parent_id,
                "sprint_id": data.sprint_id,
                "story_points": data.story_points,
                "assignee_id": data.assignee_id,
                "reporter_id": current_user.id,
                "status": IssueStatus.backlog,
                "backlog_rank": max_rank + 1,
            }
        )

        await self.history_repo.create(
            {
                "issue_id": issue.id,
                "changed_by": current_user.id,
                "from_status": None,
                "to_status": IssueStatus.backlog,
            }
        )

        return issue

    async def list_issues(
        self,
        project_id: UUID,
        filters: dict,
        page: int,
        limit: int,
    ) -> PaginatedResponse[IssueResponse]:
        offset = (page - 1) * limit
        items, total = await self.issue_repo.list_by_project(project_id, filters, offset, limit)
        return PaginatedResponse(
            items=[IssueResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def get_issue(self, project_id: UUID, issue_id: UUID) -> "Issue":
        issue = await self.issue_repo.get_by_id(issue_id)
        if issue is None or issue.project_id != project_id:
            raise NotFoundError("Issue not found", {"issue_id": str(issue_id)})
        return issue

    async def update_issue(
        self,
        project_id: UUID,
        issue_id: UUID,
        data: IssueUpdate,
        current_user: User,
        project_member: ProjectMember | None,
    ) -> "Issue":
        await self._get_active_project(project_id)
        issue = await self.get_issue(project_id, issue_id)
        self._check_developer_ownership(current_user, project_member, issue)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return issue

        if "epic_id" in update_data and update_data["epic_id"] is not None:
            if issue.type != IssueType.story:
                raise ValidationError(
                    "Only stories can be linked to epics",
                    {"type": issue.type.value},
                )
            epic = await self.epic_repo.get_by_id(update_data["epic_id"])
            if epic is None or epic.project_id != project_id:
                raise NotFoundError(
                    "Epic not found",
                    {"epic_id": str(update_data["epic_id"])},
                )

        if "sprint_id" in update_data and update_data["sprint_id"] is not None:
            sprint = await self.sprint_repo.get_by_id(update_data["sprint_id"])
            if sprint is None or sprint.project_id != project_id:
                raise NotFoundError(
                    "Sprint not found",
                    {"sprint_id": str(update_data["sprint_id"])},
                )

        return await self.issue_repo.update(issue, update_data)

    async def change_status(
        self,
        project_id: UUID,
        issue_id: UUID,
        data: StatusChangeRequest,
        current_user: User,
        project_member: ProjectMember | None,
    ) -> "Issue":
        await self._get_active_project(project_id)
        issue = await self.get_issue(project_id, issue_id)
        self._check_developer_ownership(current_user, project_member, issue)

        allowed = ALLOWED_TRANSITIONS.get(issue.status, [])
        if data.status not in allowed:
            raise ValidationError(
                f"Cannot transition from {issue.status.value} " f"to {data.status.value}",
                {
                    "current_status": issue.status.value,
                    "requested_status": data.status.value,
                    "allowed": [s.value for s in allowed],
                },
            )

        old_status = issue.status
        issue_id = issue.id
        issue = await self.issue_repo.update(issue, {"status": data.status})

        await self.history_repo.create(
            {
                "issue_id": issue_id,
                "changed_by": current_user.id,
                "from_status": old_status,
                "to_status": data.status,
            }
        )

        return issue

    async def delete_issue(
        self,
        project_id: UUID,
        issue_id: UUID,
        current_user: User,
    ) -> None:
        await self._get_active_project(project_id)
        issue = await self.get_issue(project_id, issue_id)
        await self.issue_repo.delete(issue)

    async def get_issue_history(
        self, project_id: UUID, issue_id: UUID
    ) -> list[IssueStatusHistoryResponse]:
        await self.get_issue(project_id, issue_id)
        items = await self.history_repo.list_by_issue(issue_id)
        return [IssueStatusHistoryResponse.model_validate(h) for h in items]
