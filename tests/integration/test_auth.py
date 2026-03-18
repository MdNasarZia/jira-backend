import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import SystemRole
from tests.conftest import create_user

API = "/api/v1/auth"


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


async def test_register_returns_201_with_valid_data(client: AsyncClient):
    payload = {
        "name": "Jane Doe",
        "email": f"jane-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securepassword123",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    # Top-level token fields
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    # Nested user object
    user = body["user"]
    assert user["name"] == payload["name"]
    assert user["email"] == payload["email"]
    assert user["system_role"] == "developer"
    assert user["is_active"] is True
    # Validate id is a valid UUID
    uuid.UUID(user["id"])
    # password_hash must never be exposed
    assert "password_hash" not in body
    assert "password_hash" not in user


async def test_register_returns_409_on_duplicate_email(client: AsyncClient, db: AsyncSession):
    user = await create_user(db)
    payload = {
        "name": "Duplicate",
        "email": user.email,
        "password": "securepassword123",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_register_returns_422_on_short_password(client: AsyncClient):
    payload = {
        "name": "Short Pass",
        "email": f"short-{uuid.uuid4().hex[:8]}@example.com",
        "password": "abc",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 422


async def test_register_returns_422_on_invalid_email(client: AsyncClient):
    payload = {
        "name": "Bad Email",
        "email": "not-an-email",
        "password": "securepassword123",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 422


async def test_register_returns_422_on_missing_name(client: AsyncClient):
    payload = {
        "email": f"noname-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securepassword123",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


async def test_login_returns_200_with_both_tokens(client: AsyncClient, db: AsyncSession):
    password = "correcthorse99"
    user = await create_user(db, password_hash=hash_password(password))
    payload = {"email": user.email, "password": password}
    resp = await client.post(f"{API}/login", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_returns_401_on_wrong_password(client: AsyncClient, db: AsyncSession):
    user = await create_user(db, password_hash=hash_password("realpassword"))
    payload = {"email": user.email, "password": "wrongpassword"}
    resp = await client.post(f"{API}/login", json=payload)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_login_returns_401_on_nonexistent_email(client: AsyncClient):
    payload = {"email": "ghost@example.com", "password": "anything123"}
    resp = await client.post(f"{API}/login", json=payload)
    assert resp.status_code == 401


async def test_login_returns_401_for_inactive_user(client: AsyncClient, db: AsyncSession):
    password = "securepassword123"
    user = await create_user(
        db,
        is_active=False,
        password_hash=hash_password(password),
    )
    payload = {"email": user.email, "password": password}
    resp = await client.post(f"{API}/login", json=payload)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


async def test_refresh_returns_200_with_new_token_pair(client: AsyncClient, db: AsyncSession):
    password = "securepassword123"
    user = await create_user(db, password_hash=hash_password(password))
    login_resp = await client.post(
        f"{API}/login",
        json={"email": user.email, "password": password},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post(f"{API}/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    # New refresh token must differ from old one (rotation)
    assert body["refresh_token"] != refresh_token


async def test_refresh_returns_401_on_invalid_token(client: AsyncClient):
    resp = await client.post(f"{API}/refresh", json={"refresh_token": "completely-invalid-token"})
    assert resp.status_code == 401


async def test_refresh_returns_401_on_revoked_token(client: AsyncClient, db: AsyncSession):
    password = "securepassword123"
    user = await create_user(db, password_hash=hash_password(password))
    login_resp = await client.post(
        f"{API}/login",
        json={"email": user.email, "password": password},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Use the token once (it gets revoked after rotation)
    await client.post(f"{API}/refresh", json={"refresh_token": refresh_token})

    # Try to use the same token again
    resp = await client.post(f"{API}/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


async def test_logout_returns_204_with_valid_token(client: AsyncClient, db: AsyncSession):
    password = "securepassword123"
    user = await create_user(db, password_hash=hash_password(password))
    login_resp = await client.post(
        f"{API}/login",
        json={"email": user.email, "password": password},
    )
    tokens = login_resp.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    client.headers["Authorization"] = f"Bearer {access_token}"
    resp = await client.post(f"{API}/logout", json={"refresh_token": refresh_token})
    assert resp.status_code == 204


async def test_logout_returns_401_without_auth_token(client: AsyncClient):
    resp = await client.post(f"{API}/logout", json={"refresh_token": "some-token"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


async def test_me_returns_200_with_user_info(client: AsyncClient, db: AsyncSession):
    user = await create_user(db, system_role=SystemRole.admin)
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get(f"{API}/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == user.email
    assert body["name"] == user.name
    assert body["system_role"] == user.system_role.value
    uuid.UUID(body["id"])
    assert "password_hash" not in body


async def test_me_returns_401_without_token(client: AsyncClient):
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 401


async def test_me_returns_401_with_invalid_token(client: AsyncClient):
    client.headers["Authorization"] = "Bearer invalid.jwt.token"
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Feature: Registration returns tokens
# ---------------------------------------------------------------------------


async def test_register_returns_201_with_tokens_and_user_info(
    client: AsyncClient,
):
    payload = {
        "name": "Token Tester",
        "email": f"toktest-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securepassword123",
    }
    resp = await client.post(f"{API}/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()

    # Token fields present and non-empty
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0
    assert isinstance(body["refresh_token"], str) and len(body["refresh_token"]) > 0
    assert body["token_type"] == "bearer"

    # Nested user object with expected fields
    user = body["user"]
    uuid.UUID(user["id"])
    assert user["name"] == payload["name"]
    assert user["email"] == payload["email"]
    assert user["system_role"] == "developer"

    # password_hash must never leak in any part of the response
    assert "password_hash" not in body
    assert "password_hash" not in user


async def test_register_access_token_works_for_authenticated_endpoint(
    client: AsyncClient,
):
    payload = {
        "name": "Auth Flow User",
        "email": f"authflow-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securepassword123",
    }
    reg_resp = await client.post(f"{API}/register", json=payload)
    assert reg_resp.status_code == 201
    access_token = reg_resp.json()["access_token"]

    # Use the token returned by register to call GET /auth/me
    client.headers["Authorization"] = f"Bearer {access_token}"
    me_resp = await client.get(f"{API}/me")
    assert me_resp.status_code == 200
    me_body = me_resp.json()
    assert me_body["email"] == payload["email"]
    assert me_body["name"] == payload["name"]
    uuid.UUID(me_body["id"])


async def test_register_duplicate_email_returns_409_generic_message(
    client: AsyncClient,
    db: AsyncSession,
):
    email = f"dupecheck-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "name": "First Registration",
        "email": email,
        "password": "securepassword123",
    }
    first_resp = await client.post(f"{API}/register", json=payload)
    assert first_resp.status_code == 201

    # Second registration with the same email
    payload["name"] = "Second Registration"
    second_resp = await client.post(f"{API}/register", json=payload)
    assert second_resp.status_code == 409

    error_body = second_resp.json()
    assert "error" in error_body
    assert "code" in error_body["error"]

    # The response must NOT contain the email address (enumeration prevention)
    raw_text = second_resp.text
    assert email not in raw_text


async def test_register_returns_401_if_no_token_on_me_endpoint(
    client: AsyncClient,
):
    # Calling GET /auth/me without any Authorization header must fail
    resp = await client.get(f"{API}/me")
    assert resp.status_code == 401
