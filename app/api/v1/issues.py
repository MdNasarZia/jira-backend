from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_project_member, require_project_role
from app.models.enums import IssuePriority, IssueStatus, IssueType, ProjectRole
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.issue import (
    IssueCreate,
    IssueResponse,
    IssueStatusHistoryResponse,
    IssueUpdate,
    StatusChangeRequest,
)
from app.services.issue_service import IssueService

router = APIRouter()


@router.post(
    "/{project_id}/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    project_id: UUID,
    body: IssueCreate,
    current_user: User = Depends(get_current_user),
    project_member: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    service = IssueService(db)
    issue = await service.create_issue(project_id, body, current_user)
    return IssueResponse.model_validate(issue)


@router.get(
    "/{project_id}/issues",
    response_model=PaginatedResponse[IssueResponse],
    status_code=status.HTTP_200_OK,
)
async def list_issues(
    project_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    type: IssueType | None = None,
    status_filter: IssueStatus | None = Query(None, alias="status"),
    priority: IssuePriority | None = None,
    assignee_id: UUID | None = None,
    epic_id: UUID | None = None,
    sprint_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[IssueResponse]:
    filters = {
        "type": type,
        "status": status_filter,
        "priority": priority,
        "assignee_id": assignee_id,
        "epic_id": epic_id,
        "sprint_id": sprint_id,
    }
    service = IssueService(db)
    return await service.list_issues(project_id, filters, page, limit)


@router.get(
    "/{project_id}/issues/{issue_id}",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def get_issue(
    project_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    service = IssueService(db)
    issue = await service.get_issue(project_id, issue_id)
    return IssueResponse.model_validate(issue)


@router.patch(
    "/{project_id}/issues/{issue_id}",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def update_issue(
    project_id: UUID,
    issue_id: UUID,
    body: IssueUpdate,
    current_user: User = Depends(get_current_user),
    project_member: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    service = IssueService(db)
    issue = await service.update_issue(project_id, issue_id, body, current_user, project_member)
    return IssueResponse.model_validate(issue)


@router.patch(
    "/{project_id}/issues/{issue_id}/status",
    response_model=IssueResponse,
    status_code=status.HTTP_200_OK,
)
async def change_issue_status(
    project_id: UUID,
    issue_id: UUID,
    body: StatusChangeRequest,
    current_user: User = Depends(get_current_user),
    project_member: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> IssueResponse:
    service = IssueService(db)
    issue = await service.change_status(project_id, issue_id, body, current_user, project_member)
    return IssueResponse.model_validate(issue)


@router.delete(
    "/{project_id}/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_issue(
    project_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = IssueService(db)
    await service.delete_issue(project_id, issue_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/issues/{issue_id}/history",
    response_model=list[IssueStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
)
async def get_issue_history(
    project_id: UUID,
    issue_id: UUID,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> list[IssueStatusHistoryResponse]:
    service = IssueService(db)
    return await service.get_issue_history(project_id, issue_id)
