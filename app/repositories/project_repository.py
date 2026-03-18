from uuid import UUID

from sqlalchemy import func, select

from app.models.project import Project, ProjectMember
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_by_key(self, key: str) -> Project | None:
        result = await self.db.execute(select(Project).where(Project.key == key))
        return result.scalar_one_or_none()

    async def get_by_id_with_count(self, project_id: UUID) -> tuple[Project, int] | None:
        member_count_subq = (
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
            .label("member_count")
        )
        result = await self.db.execute(
            select(Project, member_count_subq).where(Project.id == project_id)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    async def list_active(
        self, offset: int = 0, limit: int = 25
    ) -> tuple[list[tuple[Project, int]], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Project).where(Project.is_archived.is_(False))
        )
        total = count_result.scalar_one()

        member_count_subq = (
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
            .label("member_count")
        )
        result = await self.db.execute(
            select(Project, member_count_subq)
            .where(Project.is_archived.is_(False))
            .offset(offset)
            .limit(limit)
            .order_by(Project.created_at.desc())
        )
        items = [(row[0], row[1]) for row in result.all()]
        return items, total
