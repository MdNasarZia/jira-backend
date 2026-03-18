import math
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.app_exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.user import UpdateRoleRequest, UserResponse, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found", {"user_id": str(user_id)})
        return user

    async def list_users(self, page: int, limit: int) -> PaginatedResponse[UserResponse]:
        offset = (page - 1) * limit
        items, total = await self.user_repo.get_active_users(offset, limit)
        return PaginatedResponse(
            items=[UserResponse.model_validate(u) for u in items],
            total=total,
            page=page,
            limit=limit,
            pages=math.ceil(total / limit) if limit else 0,
        )

    async def update_user(self, user_id: UUID, data: UserUpdate, current_user: User) -> User:
        user = await self.get_user(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user
        return await self.user_repo.update(user, update_data)

    async def update_role(self, user_id: UUID, data: UpdateRoleRequest, current_user: User) -> User:
        if current_user.id == user_id:
            raise ConflictError("Cannot change your own role")
        user = await self.get_user(user_id)
        return await self.user_repo.update(user, {"system_role": data.system_role})
