from uuid import UUID

from sqlalchemy import select

from app.models.issue_status_history import IssueStatusHistory
from app.repositories.base import BaseRepository


class IssueStatusHistoryRepository(BaseRepository[IssueStatusHistory]):
    model = IssueStatusHistory

    async def list_by_issue(self, issue_id: UUID) -> list[IssueStatusHistory]:
        result = await self.db.execute(
            select(IssueStatusHistory)
            .where(IssueStatusHistory.issue_id == issue_id)
            .order_by(IssueStatusHistory.changed_at.asc())
        )
        return list(result.scalars().all())
