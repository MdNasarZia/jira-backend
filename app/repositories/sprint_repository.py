from uuid import UUID

from sqlalchemy import func, select

from app.models.enums import SprintStatus
from app.models.sprint import Sprint
from app.repositories.base import BaseRepository


class SprintRepository(BaseRepository[Sprint]):
    model = Sprint

    async def get_active_sprint(self, project_id: UUID) -> Sprint | None:
        result = await self.db.execute(
            select(Sprint).where(
                Sprint.project_id == project_id,
                Sprint.status == SprintStatus.active,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_project(
        self, project_id: UUID, offset: int = 0, limit: int = 25
    ) -> tuple[list[Sprint], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Sprint).where(Sprint.project_id == project_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Sprint)
            .where(Sprint.project_id == project_id)
            .offset(offset)
            .limit(limit)
            .order_by(Sprint.created_at.desc())
        )
        items = list(result.scalars().all())
        return items, total
