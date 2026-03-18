import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions.app_exceptions import ConflictError, UnauthorizedError
from app.models.enums import SystemRole
from app.models.user import RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


def _make_user(**kwargs) -> User:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test User",
        "email": "test@example.com",
        "password_hash": "$2b$12$fakehash",
        "system_role": SystemRole.developer,
        "is_active": True,
    }
    defaults.update(kwargs)
    user = MagicMock(spec=User)
    for k, v in defaults.items():
        setattr(user, k, v)
    return user


def _make_refresh_token(
    user_id: uuid.UUID,
    token_hash: str,
    revoked: bool = False,
    expired: bool = False,
) -> RefreshToken:
    token = MagicMock(spec=RefreshToken)
    token.id = uuid.uuid4()
    token.user_id = user_id
    token.token_hash = token_hash
    if expired:
        token.expires_at = datetime.now(UTC) - timedelta(days=1)
    else:
        token.expires_at = datetime.now(UTC) + timedelta(days=7)
    token.revoked_at = datetime.now(UTC) if revoked else None
    return token


def _build_service() -> tuple[AuthService, AsyncMock, AsyncMock]:
    db = AsyncMock()
    service = AuthService(db)
    service.user_repo = AsyncMock()
    service.token_repo = AsyncMock()
    return service, service.user_repo, service.token_repo


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------


async def test_register_creates_user_with_hashed_password():
    service, user_repo, _ = _build_service()
    user_repo.get_by_email.return_value = None
    created_user = _make_user()
    user_repo.create.return_value = created_user

    data = RegisterRequest(name="Jane", email="jane@example.com", password="strongpass123")
    result = await service.register(data)

    user_repo.create.assert_called_once()
    call_args = user_repo.create.call_args[0][0]
    assert call_args["name"] == "Jane"
    assert call_args["email"] == "jane@example.com"
    # Password must be hashed, not plain text
    assert call_args["password_hash"] != "strongpass123"
    assert len(call_args["password_hash"]) > 20
    assert result[0] == created_user


async def test_register_raises_conflict_on_duplicate_email():
    service, user_repo, _ = _build_service()
    user_repo.get_by_email.return_value = _make_user()

    data = RegisterRequest(name="Dup", email="exists@example.com", password="strongpass123")
    with pytest.raises(ConflictError):
        await service.register(data)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


@patch("app.services.auth_service.verify_password", return_value=True)
@patch(
    "app.services.auth_service.create_access_token",
    return_value="access.jwt.token",
)
@patch(
    "app.services.auth_service.create_refresh_token",
    return_value=("raw_refresh", "hashed_refresh"),
)
async def test_login_returns_token_pair_on_valid_credentials(
    mock_refresh, mock_access, mock_verify
):
    service, user_repo, token_repo = _build_service()
    user = _make_user()
    user_repo.get_by_email.return_value = user
    token_repo.create.return_value = MagicMock()

    data = LoginRequest(email="test@example.com", password="correctpassword")
    access_token, refresh_token = await service.login(data)

    assert access_token == "access.jwt.token"
    assert refresh_token == "raw_refresh"
    mock_verify.assert_called_once_with("correctpassword", user.password_hash)
    token_repo.create.assert_called_once()


@patch("app.services.auth_service.verify_password", return_value=False)
async def test_login_raises_unauthorized_on_wrong_password(mock_verify):
    service, user_repo, _ = _build_service()
    user_repo.get_by_email.return_value = _make_user()

    data = LoginRequest(email="test@example.com", password="wrongpassword")
    with pytest.raises(UnauthorizedError):
        await service.login(data)


async def test_login_raises_unauthorized_on_nonexistent_user():
    service, user_repo, _ = _build_service()
    user_repo.get_by_email.return_value = None

    data = LoginRequest(email="ghost@example.com", password="anything")
    with pytest.raises(UnauthorizedError):
        await service.login(data)


@patch("app.services.auth_service.verify_password", return_value=True)
async def test_login_raises_unauthorized_for_inactive_user(mock_verify):
    service, user_repo, _ = _build_service()
    user_repo.get_by_email.return_value = _make_user(is_active=False)

    data = LoginRequest(email="inactive@example.com", password="anything")
    with pytest.raises(UnauthorizedError):
        await service.login(data)


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


@patch(
    "app.services.auth_service.create_access_token",
    return_value="new_access",
)
@patch(
    "app.services.auth_service.create_refresh_token",
    return_value=("new_raw_refresh", "new_hash"),
)
async def test_refresh_rotates_token(mock_refresh_fn, mock_access_fn):
    service, _, token_repo = _build_service()

    raw_token = "some_raw_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    user_id = uuid.uuid4()
    stored = _make_refresh_token(user_id, token_hash)
    token_repo.get_by_hash.return_value = stored
    token_repo.update.return_value = stored
    token_repo.create.return_value = MagicMock()

    access, refresh = await service.refresh(raw_token)

    assert access == "new_access"
    assert refresh == "new_raw_refresh"
    # Old token should be revoked
    token_repo.update.assert_called_once()
    revoke_data = token_repo.update.call_args[0][1]
    assert "revoked_at" in revoke_data
    # New token should be created
    token_repo.create.assert_called_once()


async def test_refresh_raises_on_revoked_token():
    service, _, token_repo = _build_service()

    raw_token = "revoked_raw_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stored = _make_refresh_token(uuid.uuid4(), token_hash, revoked=True)
    token_repo.get_by_hash.return_value = stored

    with pytest.raises(UnauthorizedError):
        await service.refresh(raw_token)


async def test_refresh_raises_on_expired_token():
    service, _, token_repo = _build_service()

    raw_token = "expired_raw_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stored = _make_refresh_token(uuid.uuid4(), token_hash, expired=True)
    token_repo.get_by_hash.return_value = stored

    with pytest.raises(UnauthorizedError):
        await service.refresh(raw_token)


async def test_refresh_raises_on_invalid_token():
    service, _, token_repo = _build_service()
    token_repo.get_by_hash.return_value = None

    with pytest.raises(UnauthorizedError):
        await service.refresh("totally_invalid_token")


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


async def test_logout_revokes_token_for_current_user():
    service, _, token_repo = _build_service()

    user_id = uuid.uuid4()
    raw_token = "logout_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stored = _make_refresh_token(user_id, token_hash)
    token_repo.get_by_hash.return_value = stored
    token_repo.update.return_value = stored

    await service.logout(raw_token, user_id)

    token_repo.update.assert_called_once()
    revoke_data = token_repo.update.call_args[0][1]
    assert "revoked_at" in revoke_data


async def test_logout_raises_if_token_belongs_to_another_user():
    service, _, token_repo = _build_service()

    owner_id = uuid.uuid4()
    caller_id = uuid.uuid4()
    raw_token = "stolen_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    stored = _make_refresh_token(owner_id, token_hash)
    token_repo.get_by_hash.return_value = stored

    with pytest.raises(UnauthorizedError):
        await service.logout(raw_token, caller_id)


async def test_logout_does_nothing_for_missing_token():
    service, _, token_repo = _build_service()
    token_repo.get_by_hash.return_value = None

    # Should not raise, just silently return
    await service.logout("missing_token", uuid.uuid4())
    token_repo.update.assert_not_called()
