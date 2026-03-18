from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_active_users(self, offset: int = 0, limit: int = 25) -> tuple[list[User], int]:
        count_result = await self.db.execute(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(User)
            .where(User.is_active.is_(True))
            .offset(offset)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        items = list(result.scalars().all())
        return items, total
