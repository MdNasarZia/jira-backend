from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_project_member, require_project_role
from app.models.enums import ProjectRole
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.backlog import BacklogReorderRequest, MoveToSprintRequest
from app.schemas.common import PaginatedResponse
from app.schemas.issue import IssueResponse
from app.services.backlog_service import BacklogService

router = APIRouter()


@router.get(
    "/{project_id}/backlog",
    response_model=PaginatedResponse[IssueResponse],
    status_code=status.HTTP_200_OK,
)
async def get_backlog(
    project_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[IssueResponse]:
    service = BacklogService(db)
    return await service.get_backlog(project_id, page, limit)


@router.post(
    "/{project_id}/backlog/reorder",
    response_model=list[IssueResponse],
    status_code=status.HTTP_200_OK,
)
async def reorder_backlog(
    project_id: UUID,
    body: BacklogReorderRequest,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> list[IssueResponse]:
    service = BacklogService(db)
    return await service.reorder_backlog(project_id, body)


@router.post(
    "/{project_id}/backlog/{issue_id}/move-to-sprint",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def move_to_sprint(
    project_id: UUID,
    issue_id: UUID,
    body: MoveToSprintRequest,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    service = BacklogService(db)
    return await service.move_to_sprint(project_id, issue_id, body)
