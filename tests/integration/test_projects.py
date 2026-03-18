import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import ProjectRole, SystemRole
from tests.conftest import create_project, create_project_member, create_user

API = "/api/v1/projects"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_header(user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/v1/projects  (admin only)
# ---------------------------------------------------------------------------


async def test_create_project_returns_201_for_admin(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    payload = {
        "name": "My Project",
        "key": "MYPR",
        "description": "A test project",
    }
    resp = await client.post(API, json=payload, headers=_auth_header(admin.id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "My Project"
    assert body["key"] == "MYPR"
    assert body["is_archived"] is False
    uuid.UUID(body["id"])


async def test_create_project_returns_403_for_developer(client: AsyncClient, db: AsyncSession):
    dev = await create_user(db, system_role=SystemRole.developer)
    payload = {"name": "Blocked", "key": "BLCK"}
    resp = await client.post(API, json=payload, headers=_auth_header(dev.id))
    assert resp.status_code == 403


async def test_create_project_returns_409_on_duplicate_key(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    await create_project(db, admin.id, key="DUPE")
    payload = {"name": "Another", "key": "DUPE"}
    resp = await client.post(API, json=payload, headers=_auth_header(admin.id))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_create_project_returns_422_on_bad_key_format(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    payload = {"name": "Bad Key", "key": "lower"}
    resp = await client.post(API, json=payload, headers=_auth_header(admin.id))
    assert resp.status_code == 422


async def test_create_project_returns_422_on_key_too_short(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    payload = {"name": "Short Key", "key": "A"}
    resp = await client.post(API, json=payload, headers=_auth_header(admin.id))
    assert resp.status_code == 422


async def test_create_project_returns_401_without_token(client: AsyncClient):
    payload = {"name": "No Auth", "key": "NOAU"}
    resp = await client.post(API, json=payload)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/projects  (list)
# ---------------------------------------------------------------------------


async def test_list_projects_admin_sees_all(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    await create_project(db, admin.id)
    await create_project(db, admin.id)

    resp = await client.get(API, headers=_auth_header(admin.id))
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 2
    assert body["page"] == 1


async def test_list_projects_member_sees_own_only(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)

    project_a = await create_project(db, admin.id)
    project_b = await create_project(db, admin.id)

    await create_project_member(db, project_a.id, dev.id, ProjectRole.developer)
    # dev is NOT a member of project_b

    resp = await client.get(API, headers=_auth_header(dev.id))
    assert resp.status_code == 200
    body = resp.json()
    ids = [item["id"] for item in body["items"]]
    assert str(project_a.id) in ids
    assert str(project_b.id) not in ids


async def test_list_projects_returns_401_without_token(client: AsyncClient):
    resp = await client.get(API)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{id}
# ---------------------------------------------------------------------------


async def test_get_project_returns_200_for_member(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    resp = await client.get(f"{API}/{project.id}", headers=_auth_header(dev.id))
    assert resp.status_code == 200
    assert resp.json()["key"] == project.key


async def test_get_project_returns_403_for_non_member(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    outsider = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)

    resp = await client.get(f"{API}/{project.id}", headers=_auth_header(outsider.id))
    assert resp.status_code == 403


async def test_get_project_returns_404_for_nonexistent(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    fake_id = uuid.uuid4()
    resp = await client.get(f"{API}/{fake_id}", headers=_auth_header(admin.id))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/projects/{id}
# ---------------------------------------------------------------------------


async def test_update_project_returns_200_for_pm(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    pm = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, pm.id, ProjectRole.project_manager)

    payload = {"name": "Updated Name"}
    resp = await client.patch(f"{API}/{project.id}", json=payload, headers=_auth_header(pm.id))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


async def test_update_project_returns_403_for_developer(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {"name": "Hacked Name"}
    resp = await client.patch(f"{API}/{project.id}", json=payload, headers=_auth_header(dev.id))
    assert resp.status_code == 403


async def test_update_project_returns_200_for_admin(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    payload = {"description": "Admin updated"}
    resp = await client.patch(f"{API}/{project.id}", json=payload, headers=_auth_header(admin.id))
    assert resp.status_code == 200
    assert resp.json()["description"] == "Admin updated"


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{id}/archive  (admin only)
# ---------------------------------------------------------------------------


async def test_archive_project_returns_200_for_admin(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)

    resp = await client.post(f"{API}/{project.id}/archive", headers=_auth_header(admin.id))
    assert resp.status_code == 200
    assert resp.json()["is_archived"] is True


async def test_archive_project_returns_403_for_non_admin(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)

    resp = await client.post(f"{API}/{project.id}/archive", headers=_auth_header(dev.id))
    assert resp.status_code == 403


async def test_archive_project_returns_410_if_already_archived(
    client: AsyncClient, db: AsyncSession
):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id, is_archived=True)

    resp = await client.post(f"{API}/{project.id}/archive", headers=_auth_header(admin.id))
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Member management endpoints
# ---------------------------------------------------------------------------


async def test_add_member_returns_201_for_pm(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    pm = await create_user(db, system_role=SystemRole.developer)
    new_dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, pm.id, ProjectRole.project_manager)

    payload = {
        "user_id": str(new_dev.id),
        "project_role": "developer",
    }
    resp = await client.post(
        f"{API}/{project.id}/members",
        json=payload,
        headers=_auth_header(pm.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == str(new_dev.id)
    assert body["project_role"] == "developer"


async def test_add_member_returns_403_for_developer(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    new_user = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {
        "user_id": str(new_user.id),
        "project_role": "developer",
    }
    resp = await client.post(
        f"{API}/{project.id}/members",
        json=payload,
        headers=_auth_header(dev.id),
    )
    assert resp.status_code == 403


async def test_add_member_returns_409_if_already_member(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {
        "user_id": str(dev.id),
        "project_role": "developer",
    }
    resp = await client.post(
        f"{API}/{project.id}/members",
        json=payload,
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 409


async def test_update_member_role_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {"project_role": "project_manager"}
    resp = await client.patch(
        f"{API}/{project.id}/members/{dev.id}",
        json=payload,
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 200
    assert resp.json()["project_role"] == "project_manager"


async def test_remove_member_returns_204(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    resp = await client.delete(
        f"{API}/{project.id}/members/{dev.id}",
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 204


async def test_remove_member_returns_404_if_not_member(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    project = await create_project(db, admin.id)
    fake_user_id = uuid.uuid4()

    resp = await client.delete(
        f"{API}/{project.id}/members/{fake_user_id}",
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 404


async def test_list_members_returns_200(client: AsyncClient, db: AsyncSession):
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    resp = await client.get(
        f"{API}/{project.id}/members",
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] >= 1


# ---------------------------------------------------------------------------
# Feature: Administrator project role
# ---------------------------------------------------------------------------


async def test_admin_creates_project_gets_administrator_role(client: AsyncClient, db: AsyncSession):
    """When a system admin creates a project, they should be automatically
    added as a member with project_role == 'administrator'."""
    admin = await create_user(db, system_role=SystemRole.admin)
    payload = {
        "name": "Admin Role Project",
        "key": f"AR{uuid.uuid4().hex[:4].upper()}"[:6],
    }
    create_resp = await client.post(API, json=payload, headers=_auth_header(admin.id))
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # Fetch the members list for this project
    members_resp = await client.get(
        f"{API}/{project_id}/members",
        headers=_auth_header(admin.id),
    )
    assert members_resp.status_code == 200
    members = members_resp.json()["items"]

    # Find the admin in the members list
    admin_members = [m for m in members if m["user_id"] == str(admin.id)]
    assert len(admin_members) == 1
    assert admin_members[0]["project_role"] == "administrator"


# NOTE: test_non_admin_creates_project_gets_project_manager_role is N/A
# because the POST /projects endpoint is protected by the require_admin
# dependency. Only system admins can create projects, so a non-admin user
# would receive a 403 before the service layer is reached. The project
# creation logic still assigns project_manager for non-admin creators in
# the service, but that code path is unreachable via the API.


async def test_cannot_assign_administrator_role_to_member(client: AsyncClient, db: AsyncSession):
    """Attempting to update a member's role to 'administrator' via PATCH
    must be rejected. The MemberUpdateRequest schema has a field_validator
    that blocks this value, so we expect 422."""
    admin = await create_user(db, system_role=SystemRole.admin)
    dev = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)
    await create_project_member(db, project.id, dev.id, ProjectRole.developer)

    payload = {"project_role": "administrator"}
    resp = await client.patch(
        f"{API}/{project.id}/members/{dev.id}",
        json=payload,
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 422


async def test_cannot_add_member_with_administrator_role(client: AsyncClient, db: AsyncSession):
    """Attempting to add a new member with project_role 'administrator'
    must be rejected at the schema validation level (422)."""
    admin = await create_user(db, system_role=SystemRole.admin)
    new_user = await create_user(db, system_role=SystemRole.developer)
    project = await create_project(db, admin.id)

    payload = {
        "user_id": str(new_user.id),
        "project_role": "administrator",
    }
    resp = await client.post(
        f"{API}/{project.id}/members",
        json=payload,
        headers=_auth_header(admin.id),
    )
    assert resp.status_code == 422


async def test_admin_project_administrator_can_update_project(
    client: AsyncClient, db: AsyncSession
):
    """A system admin who is the project administrator should be able
    to update the project via PATCH."""
    admin = await create_user(db, system_role=SystemRole.admin)

    # Create the project (admin becomes 'administrator' member)
    create_resp = await client.post(
        API,
        json={
            "name": "Updatable Project",
            "key": f"UP{uuid.uuid4().hex[:4].upper()}"[:6],
        },
        headers=_auth_header(admin.id),
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # Update the project name
    patch_resp = await client.patch(
        f"{API}/{project_id}",
        json={"name": "Renamed Project"},
        headers=_auth_header(admin.id),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed Project"
