from collections.abc import AsyncGenerator, Callable
from uuid import UUID

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.exceptions.app_exceptions import ForbiddenError, UnauthorizedError
from app.models.enums import ProjectRole, SystemRole
from app.models.project import ProjectMember
from app.models.user import User
from app.repositories.project_member_repository import ProjectMemberRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        async with session.begin():
            yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authentication token")
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Invalid token payload")
    try:
        parsed_id = UUID(user_id)
    except (ValueError, AttributeError):
        raise UnauthorizedError("Invalid token payload") from None
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(parsed_id)
    if user is None:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("User account is deactivated")
    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.system_role != SystemRole.admin:
        raise ForbiddenError("Admin access required")
    return current_user


async def get_project_member(
    project_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMember | None:
    if current_user.system_role == SystemRole.admin:
        return None
    member_repo = ProjectMemberRepository(db)
    member = await member_repo.get_by_user_and_project(current_user.id, project_id)
    if member is None:
        raise ForbiddenError("Not a member of this project")
    return member


def require_project_role(roles: list[ProjectRole]) -> Callable:
    effective_roles = list(roles)
    if (
        ProjectRole.project_manager in effective_roles
        and ProjectRole.administrator not in effective_roles
    ):
        effective_roles.append(ProjectRole.administrator)

    async def dependency(
        project_member: ProjectMember | None = Depends(get_project_member),
        current_user: User = Depends(get_current_user),
    ) -> ProjectMember | None:
        if current_user.system_role == SystemRole.admin:
            return project_member
        if project_member is None or project_member.project_role not in effective_roles:
            raise ForbiddenError("Insufficient project permissions")
        return project_member

    return dependency
