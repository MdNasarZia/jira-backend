import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import IssueStatus, IssueType, ProjectRole, SprintStatus, SystemRole
from tests.conftest import (
    create_issue,
    create_project,
    create_project_member,
    create_sprint,
    create_user,
)


def _url(project_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/sprints"


def _detail_url(project_id: uuid.UUID, sprint_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/sprints/{sprint_id}"


def _start_url(project_id: uuid.UUID, sprint_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/sprints/{sprint_id}/start"


def _complete_url(project_id: uuid.UUID, sprint_id: uuid.UUID) -> str:
    return f"/api/v1/projects/{project_id}/sprints/{sprint_id}/complete"


def _auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


# ---------------------------------------------------------------------------
# POST  create sprint
# ---------------------------------------------------------------------------


async def test_create_sprint_returns_201_for_pm(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    pm = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, pm.id, ProjectRole.project_manager)

    payload = {"name": "Sprint 1", "goal": "Complete onboarding"}
    resp = await client.post(_url(project.id), json=payload, headers=_auth(pm.id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Sprint 1"
    assert body["status"] == "planned"
    assert body["goal"] == "Complete onboarding"
    uuid.UUID(body["id"])


async def test_create_sprint_returns_403_for_developer(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {"name": "Sneaky Sprint"}
    resp = await client.post(_url(project.id), json=payload, headers=_auth(dev.id))
    assert resp.status_code == 403


async def test_create_sprint_returns_401_without_token(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    payload = {"name": "No Auth Sprint"}
    resp = await client.post(_url(project.id), json=payload)
    assert resp.status_code == 401


async def test_create_sprint_returns_422_missing_name(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    resp = await client.post(_url(project.id), json={}, headers=_auth(admin.id))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET  list sprints
# ---------------------------------------------------------------------------


async def test_list_sprints_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_sprint(db, project, admin)
    await create_sprint(db, project, admin)

    resp = await client.get(_url(project.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2


# ---------------------------------------------------------------------------
# GET  single sprint
# ---------------------------------------------------------------------------


async def test_get_sprint_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin)

    resp = await client.get(_detail_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(sprint.id)


async def test_get_sprint_returns_404_wrong_project(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project_a = await create_project(db, admin.id)
    project_b = await create_project(db, admin.id)
    sprint = await create_sprint(db, project_a, admin)

    resp = await client.get(_detail_url(project_b.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH  update sprint
# ---------------------------------------------------------------------------


async def test_update_sprint_in_planned_status(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin)

    payload = {"name": "Renamed Sprint"}
    resp = await client.patch(
        _detail_url(project.id, sprint.id),
        json=payload,
        headers=_auth(admin.id),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed Sprint"


async def test_update_sprint_returns_409_when_not_planned(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin, status=SprintStatus.active)

    payload = {"name": "Should Fail"}
    resp = await client.patch(
        _detail_url(project.id, sprint.id),
        json=payload,
        headers=_auth(admin.id),
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST  start sprint
# ---------------------------------------------------------------------------


async def test_start_sprint_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin)

    resp = await client.post(_start_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "active"
    assert body["started_at"] is not None


async def test_start_sprint_returns_409_when_another_active(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    await create_sprint(db, project, admin, status=SprintStatus.active)
    sprint2 = await create_sprint(db, project, admin)

    resp = await client.post(_start_url(project.id, sprint2.id), headers=_auth(admin.id))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_start_sprint_returns_409_when_not_planned(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin, status=SprintStatus.completed)

    resp = await client.post(_start_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST  complete sprint
# ---------------------------------------------------------------------------


async def test_complete_sprint_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin, status=SprintStatus.active)

    resp = await client.post(_complete_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


async def test_complete_sprint_returns_409_when_not_active(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin)  # planned status

    resp = await client.post(_complete_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 409


async def test_complete_sprint_moves_unfinished_issues_to_backlog(
    client: AsyncClient, db: AsyncSession
):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin, status=SprintStatus.active)

    # Create an unfinished issue in the sprint
    unfinished = await create_issue(
        db,
        project,
        admin,
        type=IssueType.task,
        status=IssueStatus.in_progress,
        sprint_id=sprint.id,
    )
    # Create a finished issue in the sprint
    _finished = await create_issue(
        db,
        project,
        admin,
        type=IssueType.task,
        status=IssueStatus.done,
        sprint_id=sprint.id,
    )

    resp = await client.post(_complete_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 200

    # Verify unfinished issue moved to backlog (sprint_id = null, status = backlog)
    issue_resp = await client.get(
        f"/api/v1/projects/{project.id}/issues/{unfinished.id}",
        headers=_auth(admin.id),
    )
    assert issue_resp.status_code == 200
    issue_data = issue_resp.json()
    assert issue_data["sprint_id"] is None
    assert issue_data["status"] == "backlog"


# ---------------------------------------------------------------------------
# DELETE  sprint
# ---------------------------------------------------------------------------


async def test_delete_sprint_planned_returns_204(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin)

    resp = await client.delete(_detail_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 204


async def test_delete_sprint_returns_409_when_active(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    sprint = await create_sprint(db, project, admin, status=SprintStatus.active)

    resp = await client.delete(_detail_url(project.id, sprint.id), headers=_auth(admin.id))
    assert resp.status_code == 409


async def test_delete_sprint_returns_403_for_developer(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)
    sprint = await create_sprint(db, project, admin)

    resp = await client.delete(_detail_url(project.id, sprint.id), headers=_auth(dev.id))
    assert resp.status_code == 403


async def test_delete_sprint_returns_404_nonexistent(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)

    resp = await client.delete(_detail_url(project.id, uuid.uuid4()), headers=_auth(admin.id))
    assert resp.status_code == 404
