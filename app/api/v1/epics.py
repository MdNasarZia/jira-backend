from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_project_member, require_project_role
from app.models.enums import ProjectRole
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.epic import EpicCreate, EpicResponse, EpicUpdate
from app.services.epic_service import EpicService

router = APIRouter()


@router.post(
    "/{project_id}/epics",
    response_model=EpicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_epic(
    project_id: UUID,
    body: EpicCreate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> EpicResponse:
    service = EpicService(db)
    epic = await service.create_epic(project_id, body, current_user)
    return EpicResponse.model_validate(epic)


@router.get(
    "/{project_id}/epics",
    response_model=PaginatedResponse[EpicResponse],
    status_code=status.HTTP_200_OK,
)
async def list_epics(
    project_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[EpicResponse]:
    service = EpicService(db)
    return await service.list_epics(project_id, page, limit)


@router.get(
    "/{project_id}/epics/{epic_id}",
    response_model=EpicResponse,
    status_code=status.HTTP_200_OK,
)
async def get_epic(
    project_id: UUID,
    epic_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> EpicResponse:
    service = EpicService(db)
    epic = await service.get_epic(project_id, epic_id)
    return EpicResponse.model_validate(epic)


@router.patch(
    "/{project_id}/epics/{epic_id}",
    response_model=EpicResponse,
    status_code=status.HTTP_200_OK,
)
async def update_epic(
    project_id: UUID,
    epic_id: UUID,
    body: EpicUpdate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> EpicResponse:
    service = EpicService(db)
    epic = await service.update_epic(project_id, epic_id, body, current_user)
    return EpicResponse.model_validate(epic)


@router.delete(
    "/{project_id}/epics/{epic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_epic(
    project_id: UUID,
    epic_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = EpicService(db)
    await service.delete_epic(project_id, epic_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
