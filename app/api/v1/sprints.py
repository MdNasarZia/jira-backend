from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_project_member, require_project_role
from app.models.enums import ProjectRole
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.sprint import SprintCreate, SprintResponse, SprintUpdate
from app.services.sprint_service import SprintService

router = APIRouter()


@router.post(
    "/{project_id}/sprints",
    response_model=SprintResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sprint(
    project_id: UUID,
    body: SprintCreate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> SprintResponse:
    service = SprintService(db)
    sprint = await service.create_sprint(project_id, body, current_user)
    return SprintResponse.model_validate(sprint)


@router.get(
    "/{project_id}/sprints",
    response_model=PaginatedResponse[SprintResponse],
    status_code=status.HTTP_200_OK,
)
async def list_sprints(
    project_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SprintResponse]:
    service = SprintService(db)
    return await service.list_sprints(project_id, page, limit)


@router.get(
    "/{project_id}/sprints/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
)
async def get_sprint(
    project_id: UUID,
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> SprintResponse:
    service = SprintService(db)
    sprint = await service.get_sprint(project_id, sprint_id)
    return SprintResponse.model_validate(sprint)


@router.patch(
    "/{project_id}/sprints/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
)
async def update_sprint(
    project_id: UUID,
    sprint_id: UUID,
    body: SprintUpdate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> SprintResponse:
    service = SprintService(db)
    sprint = await service.update_sprint(project_id, sprint_id, body)
    return SprintResponse.model_validate(sprint)


@router.post(
    "/{project_id}/sprints/{sprint_id}/start",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
)
async def start_sprint(
    project_id: UUID,
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> SprintResponse:
    service = SprintService(db)
    sprint = await service.start_sprint(project_id, sprint_id)
    return SprintResponse.model_validate(sprint)


@router.post(
    "/{project_id}/sprints/{sprint_id}/complete",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
)
async def complete_sprint(
    project_id: UUID,
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> SprintResponse:
    service = SprintService(db)
    sprint = await service.complete_sprint(project_id, sprint_id)
    return SprintResponse.model_validate(sprint)


@router.delete(
    "/{project_id}/sprints/{sprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sprint(
    project_id: UUID,
    sprint_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = SprintService(db)
    await service.delete_sprint(project_id, sprint_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
