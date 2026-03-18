import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions.app_exceptions import ConflictError, GoneError, NotFoundError
from app.models.enums import IssuePriority, IssueStatus, IssueType, SprintStatus, SystemRole
from app.models.issue import Issue
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.sprint import SprintCreate, SprintUpdate
from app.services.sprint_service import SprintService


def _make_user(
    role: SystemRole = SystemRole.admin,
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


def _make_sprint(
    project_id: uuid.UUID,
    status: SprintStatus = SprintStatus.planned,
    sprint_id: uuid.UUID | None = None,
) -> Sprint:
    sprint = MagicMock(spec=Sprint)
    sprint.id = sprint_id or uuid.uuid4()
    sprint.project_id = project_id
    sprint.status = status
    sprint.name = "Test Sprint"
    sprint.started_at = None
    sprint.completed_at = None
    return sprint


def _make_issue(
    project_id: uuid.UUID,
    sprint_id: uuid.UUID,
    status: IssueStatus = IssueStatus.in_progress,
) -> Issue:
    issue = MagicMock(spec=Issue)
    issue.id = uuid.uuid4()
    issue.project_id = project_id
    issue.sprint_id = sprint_id
    issue.status = status
    issue.type = IssueType.task
    issue.priority = IssuePriority.medium
    issue.backlog_rank = 1
    return issue


def _build_service() -> tuple[SprintService, AsyncMock, AsyncMock, AsyncMock]:
    db = AsyncMock()
    service = SprintService(db)
    service.sprint_repo = AsyncMock()
    service.project_repo = AsyncMock()
    service.issue_repo = AsyncMock()
    return service, service.sprint_repo, service.project_repo, service.issue_repo


# ---------------------------------------------------------------------------
# start_sprint
# ---------------------------------------------------------------------------


async def test_start_sprint_sets_status_active():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.get_by_id.return_value = sprint
    sprint_repo.get_active_sprint.return_value = None

    started = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.update.return_value = started

    result = await service.start_sprint(project.id, sprint.id)

    assert result == started
    update_call = sprint_repo.update.call_args[0][1]
    assert update_call["status"] == SprintStatus.active
    assert "started_at" in update_call


async def test_start_sprint_raises_if_another_active():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.get_by_id.return_value = sprint

    active_sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_active_sprint.return_value = active_sprint

    with pytest.raises(ConflictError, match="already active"):
        await service.start_sprint(project.id, sprint.id)


async def test_start_sprint_raises_if_not_planned():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.completed)
    sprint_repo.get_by_id.return_value = sprint

    with pytest.raises(ConflictError, match="Only planned"):
        await service.start_sprint(project.id, sprint.id)


# ---------------------------------------------------------------------------
# complete_sprint
# ---------------------------------------------------------------------------


async def test_complete_sprint_sets_status_completed():
    service, sprint_repo, project_repo, issue_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_by_id.return_value = sprint
    issue_repo.get_unfinished_by_sprint.return_value = []

    completed = _make_sprint(project.id, SprintStatus.completed)
    sprint_repo.update.return_value = completed

    result = await service.complete_sprint(project.id, sprint.id)

    assert result == completed
    update_call = sprint_repo.update.call_args[0][1]
    assert update_call["status"] == SprintStatus.completed
    assert "completed_at" in update_call


async def test_complete_sprint_moves_unfinished_to_backlog():
    service, sprint_repo, project_repo, issue_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_by_id.return_value = sprint

    unfinished_1 = _make_issue(project.id, sprint.id, IssueStatus.in_progress)
    unfinished_2 = _make_issue(project.id, sprint.id, IssueStatus.todo)
    issue_repo.get_unfinished_by_sprint.return_value = [unfinished_1, unfinished_2]
    issue_repo.get_max_backlog_rank.return_value = 5

    completed = _make_sprint(project.id, SprintStatus.completed)
    sprint_repo.update.return_value = completed

    await service.complete_sprint(project.id, sprint.id)

    # bulk_update_sprint should be called to set sprint_id = None
    issue_repo.bulk_update_sprint.assert_called_once_with(None, [unfinished_1.id, unfinished_2.id])
    # bulk_update_status should reset to backlog
    issue_repo.bulk_update_status.assert_called_once_with(
        IssueStatus.backlog, [unfinished_1.id, unfinished_2.id]
    )


async def test_complete_sprint_recalculates_backlog_rank():
    service, sprint_repo, project_repo, issue_repo = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_by_id.return_value = sprint

    unfinished = _make_issue(project.id, sprint.id, IssueStatus.in_progress)
    issue_repo.get_unfinished_by_sprint.return_value = [unfinished]
    issue_repo.get_max_backlog_rank.return_value = 10

    completed = _make_sprint(project.id, SprintStatus.completed)
    sprint_repo.update.return_value = completed

    await service.complete_sprint(project.id, sprint.id)

    issue_repo.bulk_update_backlog_rank.assert_called_once()
    rank_updates = issue_repo.bulk_update_backlog_rank.call_args[0][0]
    # Should assign rank max_rank + 1 = 11
    assert rank_updates == [(unfinished.id, 11)]


async def test_complete_sprint_raises_if_not_active():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.get_by_id.return_value = sprint

    with pytest.raises(ConflictError, match="Only active"):
        await service.complete_sprint(project.id, sprint.id)


# ---------------------------------------------------------------------------
# delete_sprint
# ---------------------------------------------------------------------------


async def test_delete_sprint_only_allowed_in_planned_status():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.get_by_id.return_value = sprint

    await service.delete_sprint(project.id, sprint.id)

    sprint_repo.delete.assert_called_once_with(sprint)


async def test_delete_sprint_raises_if_active():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_by_id.return_value = sprint

    with pytest.raises(ConflictError, match="only delete"):
        await service.delete_sprint(project.id, sprint.id)


async def test_delete_sprint_raises_if_completed():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.completed)
    sprint_repo.get_by_id.return_value = sprint

    with pytest.raises(ConflictError):
        await service.delete_sprint(project.id, sprint.id)


# ---------------------------------------------------------------------------
# create_sprint
# ---------------------------------------------------------------------------


async def test_create_sprint_sets_planned_status():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    created = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.create.return_value = created

    user = _make_user()
    data = SprintCreate(name="New Sprint", goal="Ship it")

    result = await service.create_sprint(project.id, data, user)

    assert result == created
    create_data = sprint_repo.create.call_args[0][0]
    assert create_data["status"] == SprintStatus.planned
    assert create_data["name"] == "New Sprint"
    assert create_data["goal"] == "Ship it"


async def test_create_sprint_raises_if_project_not_found():
    service, sprint_repo, project_repo, _ = _build_service()
    project_repo.get_by_id.return_value = None

    user = _make_user()
    data = SprintCreate(name="Ghost Sprint")

    with pytest.raises(NotFoundError):
        await service.create_sprint(uuid.uuid4(), data, user)


async def test_create_sprint_raises_if_project_archived():
    service, sprint_repo, project_repo, _ = _build_service()
    project_repo.get_by_id.return_value = _make_project(is_archived=True)

    user = _make_user()
    data = SprintCreate(name="Archived Sprint")

    with pytest.raises(GoneError):
        await service.create_sprint(uuid.uuid4(), data, user)


# ---------------------------------------------------------------------------
# update_sprint
# ---------------------------------------------------------------------------


async def test_update_sprint_only_when_planned():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.get_by_id.return_value = sprint

    updated = _make_sprint(project.id, SprintStatus.planned)
    sprint_repo.update.return_value = updated

    data = SprintUpdate(name="Renamed")
    result = await service.update_sprint(project.id, sprint.id, data)

    assert result == updated
    sprint_repo.update.assert_called_once()


async def test_update_sprint_raises_if_active():
    service, sprint_repo, project_repo, _ = _build_service()

    project = _make_project()
    project_repo.get_by_id.return_value = project

    sprint = _make_sprint(project.id, SprintStatus.active)
    sprint_repo.get_by_id.return_value = sprint

    data = SprintUpdate(name="Should Fail")
    with pytest.raises(ConflictError, match="only update"):
        await service.update_sprint(project.id, sprint.id, data)


# ---------------------------------------------------------------------------
# get_sprint
# ---------------------------------------------------------------------------


async def test_get_sprint_raises_not_found_for_wrong_project():
    service, sprint_repo, _, _ = _build_service()

    project_a_id = uuid.uuid4()
    project_b_id = uuid.uuid4()
    sprint = _make_sprint(project_a_id)
    sprint_repo.get_by_id.return_value = sprint

    with pytest.raises(NotFoundError):
        await service.get_sprint(project_b_id, sprint.id)


async def test_get_sprint_raises_not_found_for_missing():
    service, sprint_repo, _, _ = _build_service()
    sprint_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError):
        await service.get_sprint(uuid.uuid4(), uuid.uuid4())
