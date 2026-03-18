from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_project_member
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.schemas.common import PaginatedResponse
from app.services.comment_service import CommentService

router = APIRouter()


@router.post(
    "/{project_id}/issues/{issue_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    project_id: UUID,
    issue_id: UUID,
    body: CommentCreate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    service = CommentService(db)
    comment = await service.create_comment(project_id, issue_id, body, current_user)
    return CommentResponse.model_validate(comment)


@router.get(
    "/{project_id}/issues/{issue_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
    status_code=status.HTTP_200_OK,
)
async def list_comments(
    project_id: UUID,
    issue_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CommentResponse]:
    service = CommentService(db)
    return await service.list_comments(project_id, issue_id, page, limit)


@router.patch(
    "/{project_id}/issues/{issue_id}/comments/{comment_id}",
    response_model=CommentResponse,
    status_code=status.HTTP_200_OK,
)
async def update_comment(
    project_id: UUID,
    issue_id: UUID,
    comment_id: UUID,
    body: CommentUpdate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    service = CommentService(db)
    comment = await service.update_comment(project_id, issue_id, comment_id, body, current_user)
    return CommentResponse.model_validate(comment)


@router.delete(
    "/{project_id}/issues/{issue_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    project_id: UUID,
    issue_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    project_member: ProjectMember | None = Depends(get_project_member),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = CommentService(db)
    await service.delete_comment(project_id, issue_id, comment_id, current_user, project_member)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
