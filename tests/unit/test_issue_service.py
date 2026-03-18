import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions.app_exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.enums import IssuePriority, IssueStatus, IssueType, ProjectRole, SystemRole
from app.models.issue import Issue
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.issue import IssueCreate, IssueUpdate, StatusChangeRequest
from app.services.issue_service import IssueService


def _make_user(
    role: SystemRole = SystemRole.developer,
    user_id: uuid.UUID | None = None,
) -> User:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.system_role = role
    user.is_active = True
    return user


def _make_project(
    project_id: uuid.UUID | None = None,
    is_archived: bool = False,
) -> Project:
    project = MagicMock(spec=Project)
    project.id = project_id or uuid.uuid4()
    project.is_archived = is_archived
    return project


def _make_issue(
    project_id: uuid.UUID,
    status: IssueStatus = IssueStatus.backlog,
    assignee_id: uuid.UUID | None = None,
    issue_type: IssueType = IssueType.task,
) -> Issue:
    issue = MagicMock(spec=Issue)
    issue.id = uuid.uuid4()
    issue.project_id = project_id
    issue.status = status
    issue.type = issue_type
    issue.assignee_id = assignee_id
    issue.title = "Test Issue"
    issue.priority = IssuePriority.medium
    issue.backlog_rank = 1
    return issue


def _make_member(
    user_id: uuid.UUID,
    role: ProjectRole = ProjectRole.developer,
) -> ProjectMember:
    member = MagicMock(spec=ProjectMember)
    member.id = uuid.uuid4()
    member.user_id = user_id
    member.project_role = role
    return member


def _build_service() -> tuple[IssueService, AsyncMock, AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    db = AsyncMock()
    service = IssueService(db)
    service.issue_repo = AsyncMock()
    service.project_repo = AsyncMock()
    service.epic_repo = AsyncMock()
    service.sprint_repo = AsyncMock()
    service.history_repo = AsyncMock()
    return (
        service,
        service.issue_repo,
        service.project_repo,
        service.epic_repo,
        service.sprint_repo,
        service.history_repo,
    )


# ---------------------------------------------------------------------------
# change_status: valid transitions
# ---------------------------------------------------------------------------


async def test_change_status_valid_transition_backlog_to_todo():
    service, issue_repo, project_repo, _, _, history_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.backlog)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, status=IssueStatus.todo)
    issue_repo.update.return_value = updated_issue
    history_repo.create.return_value = MagicMock()

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.todo)

    result = await service.change_status(project.id, issue.id, data, admin, None)

    assert result == updated_issue
    issue_repo.update.assert_called_once_with(issue, {"status": IssueStatus.todo})


async def test_change_status_valid_transition_in_progress_to_review():
    service, issue_repo, project_repo, _, _, history_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.in_progress)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, status=IssueStatus.review)
    issue_repo.update.return_value = updated_issue
    history_repo.create.return_value = MagicMock()

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.review)

    result = await service.change_status(project.id, issue.id, data, admin, None)

    assert result == updated_issue


async def test_change_status_valid_transition_review_to_done():
    service, issue_repo, project_repo, _, _, history_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.review)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, status=IssueStatus.done)
    issue_repo.update.return_value = updated_issue
    history_repo.create.return_value = MagicMock()

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.done)

    result = await service.change_status(project.id, issue.id, data, admin, None)

    assert result == updated_issue


# ---------------------------------------------------------------------------
# change_status: invalid transitions
# ---------------------------------------------------------------------------


async def test_change_status_invalid_transition_backlog_to_done():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.backlog)
    issue_repo.get_by_id.return_value = issue

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.done)

    with pytest.raises(ValidationError):
        await service.change_status(project.id, issue.id, data, admin, None)


async def test_change_status_invalid_transition_todo_to_review():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.todo)
    issue_repo.get_by_id.return_value = issue

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.review)

    with pytest.raises(ValidationError):
        await service.change_status(project.id, issue.id, data, admin, None)


async def test_change_status_invalid_transition_done_to_todo():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.done)
    issue_repo.get_by_id.return_value = issue

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.todo)

    with pytest.raises(ValidationError):
        await service.change_status(project.id, issue.id, data, admin, None)


# ---------------------------------------------------------------------------
# change_status: history recording
# ---------------------------------------------------------------------------


async def test_change_status_records_history():
    service, issue_repo, project_repo, _, _, history_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project
    issue = _make_issue(project.id, status=IssueStatus.backlog)
    issue_repo.get_by_id.return_value = issue
    updated = _make_issue(project.id, status=IssueStatus.todo)
    issue_repo.update.return_value = updated
    history_repo.create.return_value = MagicMock()

    admin = _make_user(role=SystemRole.admin)
    data = StatusChangeRequest(status=IssueStatus.todo)

    await service.change_status(project.id, issue.id, data, admin, None)

    history_repo.create.assert_called_once()
    history_data = history_repo.create.call_args[0][0]
    assert history_data["from_status"] == IssueStatus.backlog
    assert history_data["to_status"] == IssueStatus.todo
    assert history_data["changed_by"] == admin.id
    assert history_data["issue_id"] == issue.id


# ---------------------------------------------------------------------------
# update_issue: developer ownership checks
# ---------------------------------------------------------------------------


async def test_developer_cannot_update_unassigned_issue():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    dev = _make_user(role=SystemRole.developer)
    other_user_id = uuid.uuid4()
    issue = _make_issue(project.id, assignee_id=other_user_id)
    issue_repo.get_by_id.return_value = issue

    member = _make_member(dev.id, ProjectRole.developer)
    data = IssueUpdate(title="Hacked")

    with pytest.raises(ForbiddenError):
        await service.update_issue(project.id, issue.id, data, dev, member)


async def test_developer_can_update_own_issue():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    dev = _make_user(role=SystemRole.developer)
    issue = _make_issue(project.id, assignee_id=dev.id)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, assignee_id=dev.id)
    issue_repo.update.return_value = updated_issue

    member = _make_member(dev.id, ProjectRole.developer)
    data = IssueUpdate(title="My Update")

    result = await service.update_issue(project.id, issue.id, data, dev, member)

    assert result == updated_issue
    issue_repo.update.assert_called_once()


async def test_admin_can_update_any_issue():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    admin = _make_user(role=SystemRole.admin)
    other_user_id = uuid.uuid4()
    issue = _make_issue(project.id, assignee_id=other_user_id)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, assignee_id=other_user_id)
    issue_repo.update.return_value = updated_issue

    data = IssueUpdate(title="Admin Override")

    result = await service.update_issue(project.id, issue.id, data, admin, None)

    assert result == updated_issue
    issue_repo.update.assert_called_once()


async def test_pm_can_update_any_issue_in_project():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    pm = _make_user(role=SystemRole.developer)
    other_user_id = uuid.uuid4()
    issue = _make_issue(project.id, assignee_id=other_user_id)
    issue_repo.get_by_id.return_value = issue
    updated_issue = _make_issue(project.id, assignee_id=other_user_id)
    issue_repo.update.return_value = updated_issue

    member = _make_member(pm.id, ProjectRole.project_manager)
    data = IssueUpdate(title="PM Override")

    result = await service.update_issue(project.id, issue.id, data, pm, member)

    assert result == updated_issue


# ---------------------------------------------------------------------------
# create_issue: validation rules
# ---------------------------------------------------------------------------


async def test_create_issue_only_stories_can_link_to_epics():
    service, issue_repo, project_repo, epic_repo, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    admin = _make_user(role=SystemRole.admin)
    data = IssueCreate(
        title="A Task",
        type=IssueType.task,
        epic_id=uuid.uuid4(),
    )

    with pytest.raises(ValidationError, match="Only stories"):
        await service.create_issue(project.id, data, admin)


async def test_create_issue_stories_cannot_have_parent():
    service, issue_repo, project_repo, _, _, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    admin = _make_user(role=SystemRole.admin)
    data = IssueCreate(
        title="A Story",
        type=IssueType.story,
        parent_id=uuid.uuid4(),
    )

    with pytest.raises(ValidationError, match="Stories cannot"):
        await service.create_issue(project.id, data, admin)


async def test_get_issue_raises_not_found_for_wrong_project():
    service, issue_repo, _, _, _, _ = _build_service()

    project_a_id = uuid.uuid4()
    project_b_id = uuid.uuid4()
    issue = _make_issue(project_a_id)
    issue_repo.get_by_id.return_value = issue

    with pytest.raises(NotFoundError):
        await service.get_issue(project_b_id, issue.id)


async def test_get_issue_raises_not_found_for_missing_issue():
    service, issue_repo, _, _, _, _ = _build_service()

    issue_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        await service.get_issue(uuid.uuid4(), uuid.uuid4())
