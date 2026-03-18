import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.models import Base
from app.models.enums import (
    IssuePriority,
    IssueStatus,
    IssueType,
    ProjectRole,
    SprintStatus,
    SystemRole,
)
from app.models.issue import Issue
from app.models.project import Project, ProjectMember
from app.models.sprint import Sprint
from app.models.user import User
from main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://jira:jira@localhost:5432/jira_test_db",
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_client(
    client: AsyncClient, db: AsyncSession
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    user = await create_user(db, system_role=SystemRole.admin)
    token = create_access_token(str(user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    yield client, user


async def create_user(
    db: AsyncSession,
    system_role: SystemRole = SystemRole.developer,
    **kwargs,
) -> User:
    defaults = {
        "id": uuid.uuid4(),
        "name": f"Test User {uuid.uuid4().hex[:6]}",
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "password_hash": hash_password("testpassword123"),
        "system_role": system_role,
        "is_active": True,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_project(
    db: AsyncSession,
    created_by: uuid.UUID,
    **kwargs,
) -> Project:
    defaults = {
        "id": uuid.uuid4(),
        "name": f"Test Project {uuid.uuid4().hex[:6]}",
        "key": uuid.uuid4().hex[:6].upper()[:6],
        "created_by": created_by,
        "is_archived": False,
    }
    defaults.update(kwargs)
    project = Project(**defaults)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def create_project_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: ProjectRole = ProjectRole.developer,
) -> ProjectMember:
    member = ProjectMember(
        id=uuid.uuid4(),
        project_id=project_id,
        user_id=user_id,
        project_role=role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def create_issue(
    db: AsyncSession,
    project: Project,
    reporter: User,
    type: IssueType = IssueType.task,
    **kwargs,
) -> Issue:
    defaults = {
        "id": uuid.uuid4(),
        "project_id": project.id,
        "title": f"Test Issue {uuid.uuid4().hex[:6]}",
        "type": type,
        "status": IssueStatus.backlog,
        "priority": IssuePriority.medium,
        "reporter_id": reporter.id,
        "backlog_rank": 0,
    }
    defaults.update(kwargs)
    issue = Issue(**defaults)
    db.add(issue)
    await db.flush()
    await db.refresh(issue)
    return issue


async def create_sprint(
    db: AsyncSession,
    project: Project,
    created_by: User,
    **kwargs,
) -> Sprint:
    defaults = {
        "id": uuid.uuid4(),
        "project_id": project.id,
        "name": f"Sprint {uuid.uuid4().hex[:6]}",
        "status": SprintStatus.planned,
        "created_by": created_by.id,
    }
    defaults.update(kwargs)
    sprint = Sprint(**defaults)
    db.add(sprint)
    await db.flush()
    await db.refresh(sprint)
    return sprint
