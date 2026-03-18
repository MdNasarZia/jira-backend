import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ConflictError, ForbiddenError, GoneError, NotFoundError
from app.models.enums import ProjectRole, SystemRole
from app.models.user import User
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.project import (
    MemberAddRequest,
    MemberUpdateRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.member_repo = ProjectMemberRepository(db)
        self.user_repo = UserRepository(db)

    async def _get_project_orm(self, project_id: UUID) -> "Project":
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is archived")
        return project

    def _to_response(self, project: "Project", member_count: int) -> ProjectResponse:
        response = ProjectResponse.model_validate(project)
        response.member_count = member_count
        return response

    async def _get_project_response(self, project_id: UUID) -> ProjectResponse:
        result = await self.project_repo.get_by_id_with_count(project_id)
        if result is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        project, count = result
        return self._to_response(project, count)

    async def create_project(self, data: ProjectCreate, current_user: User) -> ProjectResponse:
        existing = await self.project_repo.get_by_key(data.key)
        if existing:
            raise ConflictError("Project key already exists", {"key": data.key})
        project = await self.project_repo.create(
            {
                "name": data.name,
                "key": data.key,
                "description": data.description,
                "created_by": current_user.id,
            }
        )
        role = (
            ProjectRole.administrator
            if current_user.system_role == SystemRole.admin
            else ProjectRole.project_manager
        )
        await self.member_repo.create(
            {
                "project_id": project.id,
                "user_id": current_user.id,
                "project_role": role,
            }
        )
        return self._to_response(project, 1)

    async def list_projects(
        self, page: int, limit: int, current_user: User
    ) -> PaginatedResponse[ProjectResponse]:
        offset = (page - 1) * limit
        if current_user.system_role == SystemRole.admin:
            items_with_counts, total = await self.project_repo.list_active(offset, limit)
        else:
            from sqlalchemy import func, select

            from app.models.project import Project, ProjectMember

            member_count_subq = (
                select(func.count())
                .select_from(ProjectMember)
                .where(ProjectMember.project_id == Project.id)
                .correlate(Project)
                .scalar_subquery()
                .label("member_count")
            )
            query = (
                select(Project, member_count_subq)
                .join(ProjectMember, Project.id == ProjectMember.project_id)
                .where(
                    ProjectMember.user_id == current_user.id,
                    Project.is_archived.is_(False),
                )
                .offset(offset)
                .limit(limit)
                .order_by(Project.created_at.desc())
            )
            result = await self.db.execute(query)
            items_with_counts = [(row[0], row[1]) for row in result.all()]

            count_query = (
                select(func.count())
                .select_from(Project)
                .join(ProjectMember, Project.id == ProjectMember.project_id)
                .where(
                    ProjectMember.user_id == current_user.id,
                    Project.is_archived.is_(False),
                )
            )
            count_result = await self.db.execute(count_query)
            total = count_result.scalar_one()

        return PaginatedResponse(
            items=[self._to_response(p, count) for p, count in items_with_counts],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def get_project(self, project_id: UUID, current_user: User) -> ProjectResponse:
        result = await self.project_repo.get_by_id_with_count(project_id)
        if result is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        project, count = result
        if project.is_archived:
            raise GoneError("Project is archived")
        return self._to_response(project, count)

    async def update_project(
        self, project_id: UUID, data: ProjectUpdate, current_user: User
    ) -> ProjectResponse:
        project = await self._get_project_orm(project_id)
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            await self.project_repo.update(project, update_data)
        return await self._get_project_response(project_id)

    async def delete_project(self, project_id: UUID, current_user: User) -> None:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is already archived")
        await self.project_repo.update(project, {"is_archived": True})

    async def archive_project(self, project_id: UUID, current_user: User) -> ProjectResponse:
        project = await self.project_repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found", {"project_id": str(project_id)})
        if project.is_archived:
            raise GoneError("Project is already archived")
        await self.project_repo.update(project, {"is_archived": True})
        return await self._get_project_response(project_id)

    async def add_member(
        self,
        project_id: UUID,
        data: MemberAddRequest,
        current_user: User,
    ) -> "ProjectMember":
        await self._get_project_orm(project_id)
        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise NotFoundError("User not found", {"user_id": str(data.user_id)})
        if data.project_role == ProjectRole.administrator:
            raise ForbiddenError("Cannot assign the administrator role directly")
        existing = await self.member_repo.get_by_user_and_project(data.user_id, project_id)
        if existing:
            raise ConflictError(
                "User is already a member of this project",
                {"user_id": str(data.user_id)},
            )
        member = await self.member_repo.create(
            {
                "project_id": project_id,
                "user_id": data.user_id,
                "project_role": data.project_role,
            }
        )
        return await self.member_repo.get_with_user(member.id)

    async def remove_member(self, project_id: UUID, user_id: UUID, current_user: User) -> None:
        await self._get_project_orm(project_id)
        member = await self.member_repo.get_by_user_and_project(user_id, project_id)
        if member is None:
            raise NotFoundError(
                "Member not found",
                {"user_id": str(user_id), "project_id": str(project_id)},
            )
        await self.member_repo.delete(member)

    async def update_member_role(
        self,
        project_id: UUID,
        user_id: UUID,
        data: MemberUpdateRequest,
        current_user: User,
    ) -> "ProjectMember":
        await self._get_project_orm(project_id)
        member = await self.member_repo.get_by_user_and_project(user_id, project_id)
        if member is None:
            raise NotFoundError(
                "Member not found",
                {"user_id": str(user_id), "project_id": str(project_id)},
            )
        if data.project_role == ProjectRole.administrator:
            raise ForbiddenError("Cannot assign the administrator role directly")
        updated = await self.member_repo.update(member, {"project_role": data.project_role})
        return await self.member_repo.get_with_user(updated.id)

    async def list_members(
        self, project_id: UUID, page: int, limit: int
    ) -> PaginatedResponse[ProjectMemberResponse]:
        offset = (page - 1) * limit
        items, total = await self.member_repo.list_by_project(project_id, offset, limit)
        return PaginatedResponse(
            items=[ProjectMemberResponse.model_validate(m) for m in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )
