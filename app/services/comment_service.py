import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ForbiddenError, GoneError, NotFoundError
from app.models.enums import ProjectRole, SystemRole
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.issue_repository import IssueRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.common import PaginatedResponse


class CommentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.comment_repo = CommentRepository(db)
        self.issue_repo = IssueRepository(db)
        self.project_repo = ProjectRepository(db)

    async def _get_active_project(self, project_id: UUID) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")

    async def _get_issue(self, project_id: UUID, issue_id: UUID) -> "Issue":
        issue = await self.issue_repo.get_by_id(issue_id)
        if issue is None or issue.project_id != project_id:
            raise NotFoundError("Issue not found", {"issue_id": str(issue_id)})
        return issue

    async def create_comment(
        self,
        project_id: UUID,
        issue_id: UUID,
        data: CommentCreate,
        current_user: User,
    ) -> "Comment":
        await self._get_active_project(project_id)
        await self._get_issue(project_id, issue_id)
        return await self.comment_repo.create(
            {
                "issue_id": issue_id,
                "author_id": current_user.id,
                "body": data.body,
            }
        )

    async def list_comments(
        self,
        project_id: UUID,
        issue_id: UUID,
        page: int,
        limit: int,
    ) -> PaginatedResponse[CommentResponse]:
        await self._get_issue(project_id, issue_id)
        offset = (page - 1) * limit
        items, total = await self.comment_repo.list_by_issue(issue_id, offset, limit)
        return PaginatedResponse(
            items=[CommentResponse.model_validate(c) for c in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def update_comment(
        self,
        project_id: UUID,
        issue_id: UUID,
        comment_id: UUID,
        data: CommentUpdate,
        current_user: User,
    ) -> "Comment":
        await self._get_active_project(project_id)
        await self._get_issue(project_id, issue_id)
        comment = await self.comment_repo.get_by_id(comment_id)
        if comment is None or comment.issue_id != issue_id:
            raise NotFoundError("Comment not found", {"comment_id": str(comment_id)})
        if comment.author_id != current_user.id:
            raise ForbiddenError("Only the author can edit this comment")
        return await self.comment_repo.update(comment, {"body": data.body, "is_edited": True})

    async def delete_comment(
        self,
        project_id: UUID,
        issue_id: UUID,
        comment_id: UUID,
        current_user: User,
        project_member: ProjectMember | None,
    ) -> None:
        await self._get_active_project(project_id)
        await self._get_issue(project_id, issue_id)
        comment = await self.comment_repo.get_by_id(comment_id)
        if comment is None or comment.issue_id != issue_id:
            raise NotFoundError("Comment not found", {"comment_id": str(comment_id)})

        is_author = comment.author_id == current_user.id
        is_admin = current_user.system_role == SystemRole.admin
        is_pm = (
            project_member is not None
            and project_member.project_role == ProjectRole.project_manager
        )

        if not (is_author or is_admin or is_pm):
            raise ForbiddenError("Not allowed to delete this comment")

        await self.comment_repo.delete(comment)
