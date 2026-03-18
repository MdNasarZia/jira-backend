from uuid import UUID

from sqlalchemy import func, select

from app.models.epic import Epic
from app.repositories.base import BaseRepository


class EpicRepository(BaseRepository[Epic]):
    model = Epic

    async def list_by_project(
        self, project_id: UUID, offset: int = 0, limit: int = 25
    ) -> tuple[list[Epic], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Epic).where(Epic.project_id == project_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Epic)
            .where(Epic.project_id == project_id)
            .offset(offset)
            .limit(limit)
            .order_by(Epic.created_at.desc())
        )
        items = list(result.scalars().all())
        return items, total
