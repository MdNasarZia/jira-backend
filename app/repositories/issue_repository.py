from uuid import UUID

from sqlalchemy import func, select, update

from app.models.issue import Issue
from app.repositories.base import BaseRepository


class IssueRepository(BaseRepository[Issue]):
    model = Issue

    async def list_by_project(
        self,
        project_id: UUID,
        filters: dict,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[Issue], int]:
        query = select(Issue).where(Issue.project_id == project_id)
        count_query = select(func.count()).select_from(Issue).where(Issue.project_id == project_id)

        filterable_fields = [
            "type",
            "status",
            "priority",
            "assignee_id",
            "epic_id",
            "sprint_id",
        ]
        for field in filterable_fields:
            value = filters.get(field)
            if value is not None:
                query = query.where(getattr(Issue, field) == value)
                count_query = count_query.where(getattr(Issue, field) == value)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(
            query.offset(offset).limit(limit).order_by(Issue.created_at.desc())
        )
        items = list(result.scalars().all())
        return items, total

    async def list_backlog(self, project_id: UUID) -> list[Issue]:
        result = await self.db.execute(
            select(Issue)
            .where(
                Issue.project_id == project_id,
                Issue.sprint_id.is_(None),
            )
            .order_by(Issue.backlog_rank.asc())
        )
        return list(result.scalars().all())

    async def list_backlog_paginated(
        self, project_id: UUID, offset: int = 0, limit: int = 25
    ) -> tuple[list[Issue], int]:
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.project_id == project_id,
                Issue.sprint_id.is_(None),
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Issue)
            .where(
                Issue.project_id == project_id,
                Issue.sprint_id.is_(None),
            )
            .order_by(Issue.backlog_rank.asc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_max_backlog_rank(self, project_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(Issue.backlog_rank), 0)).where(
                Issue.project_id == project_id
            )
        )
        return result.scalar_one()

    async def bulk_update_sprint(self, sprint_id: UUID | None, issue_ids: list[UUID]) -> None:
        if not issue_ids:
            return
        await self.db.execute(
            update(Issue).where(Issue.id.in_(issue_ids)).values(sprint_id=sprint_id)
        )
        await self.db.flush()

    async def bulk_update_backlog_rank(self, updates: list[tuple[UUID, int]]) -> None:
        for issue_id, rank in updates:
            await self.db.execute(
                update(Issue).where(Issue.id == issue_id).values(backlog_rank=rank)
            )
        await self.db.flush()

    async def bulk_update_status(self, status: "IssueStatus", issue_ids: list[UUID]) -> None:
        if not issue_ids:
            return

        await self.db.execute(update(Issue).where(Issue.id.in_(issue_ids)).values(status=status))
        await self.db.flush()

    async def get_unfinished_by_sprint(self, sprint_id: UUID) -> list[Issue]:
        from app.models.enums import IssueStatus

        result = await self.db.execute(
            select(Issue).where(
                Issue.sprint_id == sprint_id,
                Issue.status != IssueStatus.done,
            )
        )
        return list(result.scalars().all())
