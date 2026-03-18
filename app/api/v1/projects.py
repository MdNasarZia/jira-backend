from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db,
    get_project_member,
    require_admin,
    require_project_role,
)
from app.models.enums import ProjectRole
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.project import (
    MemberAddRequest,
    MemberUpdateRequest,
    ProjectCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return await service.create_project(body, current_user)


@router.get(
    "",
    response_model=PaginatedResponse[ProjectResponse],
    status_code=status.HTTP_200_OK,
)
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectResponse]:
    service = ProjectService(db)
    return await service.list_projects(page, limit, current_user)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return await service.get_project(project_id, current_user)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return await service.update_project(project_id, body, current_user)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = ProjectService(db)
    await service.delete_project(project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/archive",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return await service.archive_project(project_id, current_user)


@router.get(
    "/{project_id}/members",
    response_model=PaginatedResponse[ProjectMemberResponse],
    status_code=status.HTTP_200_OK,
)
async def list_members(
    project_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectMemberResponse]:
    service = ProjectService(db)
    return await service.list_members(project_id, page, limit)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    project_id: UUID,
    body: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    service = ProjectService(db)
    member = await service.add_member(project_id, body, current_user)
    return ProjectMemberResponse.model_validate(member)


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_200_OK,
)
async def update_member_role(
    project_id: UUID,
    user_id: UUID,
    body: MemberUpdateRequest,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    service = ProjectService(db)
    member = await service.update_member_role(project_id, user_id, body, current_user)
    return ProjectMemberResponse.model_validate(member)


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = ProjectService(db)
    await service.remove_member(project_id, user_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
