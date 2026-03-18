import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import IssuePriority, IssueStatus, IssueType, ProjectRole, SystemRole
from tests.conftest import create_issue, create_project, create_project_member, create_user


def _url(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/issues"


def _detail_url(project_id: uuid.UUID, issue_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/issues/{issue_id}"


def _status_url(project_id: uuid.UUID, issue_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/issues/{issue_id}/status"


def _history_url(project_id: uuid.UUID, issue_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/issues/{issue_id}/history"


def _auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


# ---------------------------------------------------------------------------
# POST  create issue
# ---------------------------------------------------------------------------


async def test_create_issue_returns_201(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)

    payload = {
        "title": "Implement login",
        "type": "task",
        "priority": "high",
    }
    resp = await client.post(_url(project.id), json=payload, headers=_auth(admin.id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Implement login"
    assert body["type"] == "task"
    assert body["priority"] == "high"
    assert body["status"] == "backlog"
    assert body["project_id"] == str(project.id)
    uuid.UUID(body["id"])


async def test_create_issue_returns_401_without_token(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    payload = {"title": "No auth", "type": "task"}
    resp = await client.post(_url(project.id), json=payload)
    assert resp.status_code == 401


async def test_create_issue_returns_403_for_non_member(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    outsider = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)

    payload = {"title": "Sneaky", "type": "task"}
    resp = await client.post(_url(project.id), json=payload, headers=_auth(outsider.id))
    assert resp.status_code == 403


async def test_create_issue_returns_422_on_missing_title(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    payload = {"type": "task"}
    resp = await client.post(_url(project.id), json=payload, headers=_auth(admin.id))
    assert resp.status_code == 422


async def test_create_issue_returns_404_for_nonexistent_project(
    client: AsyncClient, db: AsyncSession
):
    admin = await create_user(db, system_role=SystemRole.admin)
    fake_project_id = uuid.uuid4()
    payload = {"title": "Ghost project", "type": "task"}
    resp = await client.post(_url(fake_project_id), json=payload, headers=_auth(admin.id))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET  list issues with filters
# ---------------------------------------------------------------------------


async def test_list_issues_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_issue(db, project, admin, type=IssueType.task)
    await create_issue(db, project, admin, type=IssueType.bug)

    resp = await client.get(_url(project.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


async def test_list_issues_filter_by_type(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_issue(db, project, admin, type=IssueType.task)
    await create_issue(db, project, admin, type=IssueType.bug)

    resp = await client.get(_url(project.id), params={"type": "bug"}, headers=_auth(admin.id))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["type"] == "bug"


async def test_list_issues_filter_by_status(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_issue(db, project, admin, type=IssueType.task, status=IssueStatus.todo)
    await create_issue(db, project, admin, type=IssueType.task, status=IssueStatus.backlog)

    resp = await client.get(_url(project.id), params={"status": "todo"}, headers=_auth(admin.id))
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "todo"


async def test_list_issues_filter_by_priority(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_issue(db, project, admin, priority=IssuePriority.highest)
    await create_issue(db, project, admin, priority=IssuePriority.low)

    resp = await client.get(
        _url(project.id),
        params={"priority": "highest"},
        headers=_auth(admin.id),
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["priority"] == "highest"


# ---------------------------------------------------------------------------
# GET  single issue
# ---------------------------------------------------------------------------


async def test_get_issue_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin)

    resp = await client.get(_detail_url(project.id, issue.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(issue.id)


async def test_get_issue_returns_404_wrong_project(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project_a = await create_project(db, admin.id)
    project_b = await create_project(db, admin.id)
    issue = await create_issue(db, project_a, admin)

    # Issue belongs to project_a, but we query project_b
    resp = await client.get(_detail_url(project_b.id, issue.id), headers=_auth(admin.id))
    assert resp.status_code == 404


async def test_get_issue_returns_404_nonexistent(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)

    resp = await client.get(_detail_url(project.id, uuid.uuid4()), headers=_auth(admin.id))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH  update issue
# ---------------------------------------------------------------------------


async def test_update_issue_pm_can_update_any(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    pm = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, pm.id, ProjectRole.project_manager)
    issue = await create_issue(db, project, admin)

    payload = {"title": "Updated by PM"}
    resp = await client.patch(
        _detail_url(project.id, issue.id),
        json=payload,
        headers=_auth(pm.id),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated by PM"


async def test_update_issue_developer_can_update_own(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)
    issue = await create_issue(db, project, admin, assignee_id=dev.id)

    payload = {"title": "Dev updated own"}
    resp = await client.patch(
        _detail_url(project.id, issue.id),
        json=payload,
        headers=_auth(dev.id),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dev updated own"


async def test_update_issue_developer_cannot_update_unassigned(
    client: AsyncClient, db: AsyncSession
):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)
    issue = await create_issue(db, project, admin)  # not assigned to dev

    payload = {"title": "Should fail"}
    resp = await client.patch(
        _detail_url(project.id, issue.id),
        json=payload,
        headers=_auth(dev.id),
    )
    assert resp.status_code == 403


async def test_update_issue_admin_can_update_any(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)
    issue = await create_issue(db, project, dev, assignee_id=dev.id)

    payload = {"priority": "highest"}
    resp = await client.patch(
        _detail_url(project.id, issue.id),
        json=payload,
        headers=_auth(admin.id),
    )
    assert resp.status_code == 200
    assert resp.json()["priority"] == "highest"


# ---------------------------------------------------------------------------
# PATCH  change status
# ---------------------------------------------------------------------------


async def test_change_status_valid_transition(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin, status=IssueStatus.backlog)

    # backlog -> todo is valid
    resp = await client.patch(
        _status_url(project.id, issue.id),
        json={"status": "todo"},
        headers=_auth(admin.id),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "todo"


async def test_change_status_invalid_transition_returns_422(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin, status=IssueStatus.backlog)

    # backlog -> done is NOT valid
    resp = await client.patch(
        _status_url(project.id, issue.id),
        json={"status": "done"},
        headers=_auth(admin.id),
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_change_status_backlog_to_in_progress_invalid(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin, status=IssueStatus.backlog)

    resp = await client.patch(
        _status_url(project.id, issue.id),
        json={"status": "in_progress"},
        headers=_auth(admin.id),
    )
    assert resp.status_code == 422


async def test_change_status_todo_to_done_invalid(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin, status=IssueStatus.todo)

    resp = await client.patch(
        _status_url(project.id, issue.id),
        json={"status": "done"},
        headers=_auth(admin.id),
    )
    assert resp.status_code == 422


async def test_change_status_records_history(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin, status=IssueStatus.backlog)

    # Transition backlog -> todo
    await client.patch(
        _status_url(project.id, issue.id),
        json={"status": "todo"},
        headers=_auth(admin.id),
    )

    resp = await client.get(_history_url(project.id, issue.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    # Find the transition record
    transition = [h for h in history if h["from_status"] == "backlog" and h["to_status"] == "todo"]
    assert len(transition) == 1


# ---------------------------------------------------------------------------
# DELETE  issue
# ---------------------------------------------------------------------------


async def test_delete_issue_pm_returns_204(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    pm = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, pm.id, ProjectRole.project_manager)
    issue = await create_issue(db, project, admin)

    resp = await client.delete(_detail_url(project.id, issue.id), headers=_auth(pm.id))
    assert resp.status_code == 204


async def test_delete_issue_developer_returns_403(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)
    issue = await create_issue(db, project, admin)

    resp = await client.delete(_detail_url(project.id, issue.id), headers=_auth(dev.id))
    assert resp.status_code == 403


async def test_delete_issue_admin_returns_204(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin)

    resp = await client.delete(_detail_url(project.id, issue.id), headers=_auth(admin.id))
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(_detail_url(project.id, issue.id), headers=_auth(admin.id))
    assert resp.status_code == 404


async def test_delete_issue_returns_401_without_token(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    issue = await create_issue(db, project, admin)

    resp = await client.delete(_detail_url(project.id, issue.id))
    assert resp.status_code == 401
