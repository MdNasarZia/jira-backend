from uuid import UUID

from sqlalchemy import func, select

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_issue(
        self, issue_id: UUID, offset: int = 0, limit: int = 25
    ) -> tuple[list[Comment], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(Comment).where(Comment.issue_id == issue_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Comment)
            .where(Comment.issue_id == issue_id)
            .offset(offset)
            .limit(limit)
            .order_by(Comment.created_at.asc())
        )
        items = list(result.scalars().all())
        return items, total
