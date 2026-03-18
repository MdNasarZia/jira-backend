import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.exceptions.app_exceptions import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def register(self, data: RegisterRequest) -> tuple[User, str, str]:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("Registration failed. Please try again with different details.")
        user = await self.user_repo.create(
            {
                "name": data.name,
                "email": data.email,
                "password_hash": hash_password(data.password),
            }
        )

        if not user.is_active:
            raise UnauthorizedError("User account could not be activated")

        access_token = create_access_token(str(user.id))
        raw_refresh, refresh_hash = create_refresh_token()

        expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create(
            {
                "user_id": user.id,
                "token_hash": refresh_hash,
                "expires_at": expires_at,
            }
        )

        return user, access_token, raw_refresh

    async def login(self, data: LoginRequest) -> tuple[str, str]:
        user = await self.user_repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("User account is deactivated")

        access_token = create_access_token(str(user.id))
        raw_refresh, refresh_hash = create_refresh_token()

        expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create(
            {
                "user_id": user.id,
                "token_hash": refresh_hash,
                "expires_at": expires_at,
            }
        )

        return access_token, raw_refresh

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored = await self.token_repo.get_by_hash(token_hash)
        if stored is None:
            raise UnauthorizedError("Invalid refresh token")
        if stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token has been revoked")
        if stored.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Refresh token has expired")

        await self.token_repo.update(stored, {"revoked_at": datetime.now(UTC)})

        access_token = create_access_token(str(stored.user_id))
        raw_refresh, new_hash = create_refresh_token()

        expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self.token_repo.create(
            {
                "user_id": stored.user_id,
                "token_hash": new_hash,
                "expires_at": expires_at,
            }
        )

        return access_token, raw_refresh

    async def logout(self, refresh_token: str, user_id: "UUID") -> None:

        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        stored = await self.token_repo.get_by_hash(token_hash)
        if stored is None or stored.revoked_at is not None:
            return
        if stored.user_id != user_id:
            raise UnauthorizedError("Token does not belong to the current user")
        await self.token_repo.update(stored, {"revoked_at": datetime.now(UTC)})
