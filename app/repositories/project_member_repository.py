from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.project import ProjectMember
from app.repositories.base import BaseRepository


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    model = ProjectMember

    async def get_with_user(self, member_id: UUID) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .where(ProjectMember.id == member_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_project(
        self, user_id: UUID, project_id: UUID
    ) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_by_project(self, project_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        return result.scalar_one()

    async def list_by_project(
        self, project_id: UUID, offset: int = 0, limit: int = 25
    ) -> tuple[list[ProjectMember], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(ProjectMember)
            .options(joinedload(ProjectMember.user))
            .where(ProjectMember.project_id == project_id)
            .offset(offset)
            .limit(limit)
            .order_by(ProjectMember.joined_at.asc())
        )
        items = list(result.scalars().all())
        return items, total
