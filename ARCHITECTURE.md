# Architecture Document
# Simplified Jira-Like Issue Tracking System — Backend

**Version:** 1.0
**Date:** 2026-03-09
**Stack:** Python 3.12+, FastAPI, SQLAlchemy (async), PostgreSQL, JWT

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Recommended Tech Stack](#2-recommended-tech-stack)
3. [Folder Structure](#3-folder-structure)
4. [API Architecture](#4-api-architecture)
5. [Service Layer Design](#5-service-layer-design)
6. [Repository / Data Access Layer](#6-repository--data-access-layer)
7. [Authentication Architecture](#7-authentication-architecture)
8. [Role-Based Authorization](#8-role-based-authorization)
9. [Request Lifecycle](#9-request-lifecycle)
10. [Error Handling Patterns](#10-error-handling-patterns)
11. [Middleware Pipeline](#11-middleware-pipeline)
12. [External Services](#12-external-services)
13. [Deployment Architecture](#13-deployment-architecture)
14. [Architecture Diagram](#14-architecture-diagram)

---

## 1. System Overview

### What Is This System?

This is a RESTful backend API for a simplified project management and issue tracking system modeled after Jira. It is a **learning project** built with Python and FastAPI that demonstrates clean architecture, async database access, JWT authentication, role-based authorization, and RESTful API design.

The system is **backend-only**. There is no frontend UI, file upload service, email system, or real-time notification layer in this version.

### Who Uses It?

Three actor types interact with the system:

| Actor | Scope | Primary Actions |
|---|---|---|
| **Admin** | System-wide | Manages users, creates/archives projects, full data access |
| **Project Manager (PM)** | Per-project | Manages sprints, epics, issues, team membership within a project |
| **Developer** | Per-project | Creates and updates tasks/bugs assigned to them, adds comments |

### Core Flows

**1. User Onboarding**
A new user registers via `POST /api/v1/auth/register`. An Admin then assigns them a system role and adds them to one or more projects with a project-level role.

**2. Project Setup**
An Admin creates a project (`POST /api/v1/projects`). A PM is assigned. The PM creates Epics (`POST /api/v1/projects/:id/epics`) to organize the work, then creates Stories linked to those Epics. Developers are added as project members.

**3. Sprint Planning**
A PM creates a Sprint (`POST /api/v1/projects/:id/sprints`), moves backlog issues into it, then starts the sprint (`POST /sprints/:id/start`). The team works through the sprint. When complete, the PM calls `POST /sprints/:id/complete`, which moves unfinished issues back to the backlog.

**4. Issue Lifecycle**
Issues begin in `backlog` status. As a developer picks up work, they transition the issue: `backlog → todo → in_progress → review → done`. Every status change is recorded in `IssueStatusHistory` for audit purposes.

**5. Comments**
Any project member can comment on issues. Authors can edit their own comments. Admins and PMs can delete any comment.

---

## 2. Recommended Tech Stack

| Category | Library / Tool | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.12+ | Runtime |
| Web Framework | FastAPI | 0.115+ | HTTP routing, DI, OpenAPI docs |
| ASGI Server | Uvicorn | 0.30+ | Production-grade ASGI server |
| ORM | SQLAlchemy (async) | 2.0+ | Async database access, query building |
| DB Migrations | Alembic | 1.13+ | Schema versioning and migrations |
| Database | PostgreSQL | 16+ | Primary relational datastore |
| Async DB Driver | asyncpg | 0.29+ | Async PostgreSQL driver for SQLAlchemy |
| Auth — Tokens | python-jose[cryptography] | 3.3+ | JWT encoding/decoding (HS256/RS256) |
| Auth — Passwords | passlib[bcrypt] | 1.7+ | Password hashing using bcrypt |
| Schema Validation | Pydantic v2 | 2.7+ | Request/response schemas, validation |
| Config Management | python-dotenv | 1.0+ | Load `.env` into environment variables |
| Testing Framework | Pytest | 8.0+ | Test runner |
| Async Test Client | httpx | 0.27+ | Async HTTP client for integration tests |
| Test DB Fixtures | pytest-asyncio | 0.23+ | Async test support |
| CORS | FastAPI built-in | — | CORSMiddleware from Starlette |

### Deferred / Optional

| Tool | Decision |
|---|---|
| **Redis** | Deferred but recommended for refresh token blacklisting (see Section 12). Not required for core functionality. |
| **Celery** | Not recommended for this project scope. No background task queue is needed. Can be added later for notifications or report generation. |
| **Docker Compose** | Included for local development (app + postgres + optional redis). |

---

## 3. Folder Structure

```
jira-backend/
│
├── app/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py             # Aggregates all v1 routers
│   │       ├── auth.py               # /auth/* endpoints
│   │       ├── users.py              # /users/* endpoints (Admin)
│   │       ├── projects.py           # /projects/* endpoints
│   │       ├── epics.py              # /projects/:id/epics/* endpoints
│   │       ├── issues.py             # /projects/:id/issues/* endpoints
│   │       ├── sprints.py            # /projects/:id/sprints/* endpoints
│   │       ├── backlog.py            # /projects/:id/backlog/* endpoints
│   │       └── comments.py           # /projects/:id/issues/:id/comments/*
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # Settings class (pydantic-settings)
│   │   ├── security.py               # JWT creation/validation, password hashing
│   │   └── dependencies.py           # FastAPI Depends: DB session, current user, roles
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                   # DeclarativeBase, common mixins (id, timestamps)
│   │   ├── user.py                   # User, RefreshToken models
│   │   ├── project.py                # Project, ProjectMember models
│   │   ├── epic.py                   # Epic model
│   │   ├── issue.py                  # Issue model (Story/Task/Bug discriminated by type)
│   │   ├── sprint.py                 # Sprint model
│   │   ├── comment.py                # Comment model
│   │   └── issue_status_history.py   # IssueStatusHistory model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py                 # PaginatedResponse, ErrorResponse schemas
│   │   ├── auth.py                   # RegisterRequest, LoginRequest, TokenResponse, etc.
│   │   ├── user.py                   # UserResponse, UpdateRoleRequest, etc.
│   │   ├── project.py                # ProjectCreate, ProjectResponse, MemberAdd, etc.
│   │   ├── epic.py                   # EpicCreate, EpicUpdate, EpicResponse
│   │   ├── issue.py                  # IssueCreate, IssueUpdate, IssueResponse, StatusChange
│   │   ├── sprint.py                 # SprintCreate, SprintUpdate, SprintResponse
│   │   ├── backlog.py                # BacklogResponse, ReorderRequest, MoveToSprintRequest
│   │   └── comment.py                # CommentCreate, CommentUpdate, CommentResponse
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── project_service.py
│   │   ├── epic_service.py
│   │   ├── issue_service.py
│   │   ├── sprint_service.py
│   │   ├── backlog_service.py
│   │   └── comment_service.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseRepository with generic CRUD
│   │   ├── user_repository.py
│   │   ├── refresh_token_repository.py
│   │   ├── project_repository.py
│   │   ├── project_member_repository.py
│   │   ├── epic_repository.py
│   │   ├── issue_repository.py
│   │   ├── sprint_repository.py
│   │   ├── comment_repository.py
│   │   └── issue_status_history_repository.py
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py             # Attach UUID to each request
│   │   └── logging.py                # Log method, path, status, duration
│   │
│   └── exceptions/
│       ├── __init__.py
│       ├── app_exceptions.py         # AppException hierarchy
│       └── handlers.py               # FastAPI exception handlers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # DB fixtures, test client, factory helpers
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_issue_service.py
│   │   ├── test_sprint_service.py
│   │   └── test_security.py
│   └── integration/
│       ├── test_auth.py
│       ├── test_projects.py
│       ├── test_issues.py
│       ├── test_sprints.py
│       └── test_comments.py
│
├── alembic/
│   ├── env.py                        # Alembic async environment config
│   ├── script.py.mako
│   └── versions/                     # Auto-generated migration scripts
│
├── main.py                           # FastAPI app factory, middleware, router registration
├── pyproject.toml                    # Project metadata and dependencies
├── .env.example                      # Environment variable template
├── Dockerfile                        # Multi-stage Docker build
└── docker-compose.yml                # Local dev: app + postgres + redis (optional)
```

---

## 4. API Architecture

### RESTful Principles

The API follows REST conventions:

- Resources are nouns (`/projects`, `/issues`, not `/getProjects`).
- HTTP verbs encode intent: `GET` reads, `POST` creates, `PATCH` partially updates, `DELETE` removes.
- Nested resources reflect ownership: `/projects/:projectId/epics/:epicId/`.
- State-changing actions that do not map cleanly to CRUD use sub-resource verbs: `/sprints/:id/start`, `/sprints/:id/complete`.
- HTTP status codes are semantically correct: `200 OK`, `201 Created`, `204 No Content`, `400`, `401`, `403`, `404`, `409`, `422`.

### Versioning Strategy

All routes are prefixed with `/api/v1`. This is implemented via a dedicated `APIRouter` aggregated in `app/api/v1/router.py` and mounted in `main.py`:

```python
# main.py
from app.api.v1.router import v1_router

app.include_router(v1_router, prefix="/api/v1")
```

When a v2 becomes necessary, a parallel `app/api/v2/` directory is created and mounted alongside v1 without breaking existing clients.

### Router Registration

Each module has its own `APIRouter`. The v1 aggregate router imports and includes them:

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1 import auth, users, projects, epics, issues, sprints, backlog, comments

v1_router = APIRouter()
v1_router.include_router(auth.router,     prefix="/auth",     tags=["Auth"])
v1_router.include_router(users.router,    prefix="/users",    tags=["Users"])
v1_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
v1_router.include_router(issues.router,   prefix="/projects", tags=["Issues"])
v1_router.include_router(sprints.router,  prefix="/projects", tags=["Sprints"])
v1_router.include_router(backlog.router,  prefix="/projects", tags=["Backlog"])
v1_router.include_router(comments.router, prefix="/projects", tags=["Comments"])
```

### Dependency Injection

FastAPI's `Depends` system is used pervasively:

- `get_db` — yields an async SQLAlchemy session per request.
- `get_current_user` — decodes JWT, fetches the user, raises `401` if invalid.
- `require_admin` — wraps `get_current_user`, raises `403` if not Admin.
- `require_project_member` — resolves project from path param, checks membership.
- `require_project_role(roles=[...])` — dependency factory for fine-grained project role checks.

### Response Shape

No global envelope wrapper is used. Responses return the resource directly as a Pydantic schema. For lists, a standard paginated wrapper is used:

```python
# app/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
```

### Pagination Pattern

Pagination is query-parameter driven: `?page=1&limit=25`. Defaults are `page=1`, `limit=25`, maximum `limit=100`. The repository layer accepts `offset` and `limit` computed from these values. The service layer computes `pages = ceil(total / limit)` and wraps results in `PaginatedResponse`.

---

## 5. Service Layer Design

### Responsibilities

The service layer is the **sole holder of business logic**. It:

- Validates business rules that go beyond schema validation (e.g., "only one active sprint per project").
- Enforces authorization logic that is data-dependent (e.g., "a developer can only update issues assigned to them").
- Orchestrates calls to one or more repositories.
- Records side effects such as writing to `IssueStatusHistory` on status changes.
- Does **not** interact with HTTP request/response objects directly.

### Structure

Each service corresponds to one module and is a plain Python class that receives an async SQLAlchemy session at construction time:

```python
# app/services/issue_service.py
class IssueService:
    def __init__(self, db: AsyncSession):
        self.issue_repo = IssueRepository(db)
        self.history_repo = IssueStatusHistoryRepository(db)
        self.member_repo = ProjectMemberRepository(db)

    async def change_status(
        self,
        issue_id: UUID,
        new_status: IssueStatus,
        current_user: User,
        project_member: ProjectMember | None,
    ) -> Issue:
        issue = await self.issue_repo.get_by_id(issue_id)
        if not issue:
            raise NotFoundError("Issue not found")
        self._validate_transition(issue.status, new_status)
        self._check_transition_permission(issue, current_user, project_member)
        updated = await self.issue_repo.update(issue, {"status": new_status})
        await self.history_repo.create({
            "issue_id": issue.id,
            "changed_by": current_user.id,
            "from_status": issue.status,
            "to_status": new_status,
        })
        return updated
```

### Inter-Service Communication Rule

Services do **not** call other services. This avoids circular dependency problems and keeps the dependency graph flat. When a service needs data normally owned by another module, it either:

1. Accepts that data as a pre-resolved parameter (passed in by the route handler via a dependency), or
2. Uses the relevant repository directly (repositories are not coupled to services).

For example, when `SprintService.complete_sprint()` needs to move issues back to the backlog, it uses `IssueRepository` directly rather than calling `IssueService`.

### Status Transition Validation

The allowed transition graph is encoded as a dictionary constant:

```python
# app/services/issue_service.py
ALLOWED_TRANSITIONS: dict[IssueStatus, list[IssueStatus]] = {
    IssueStatus.backlog:      [IssueStatus.todo],
    IssueStatus.todo:         [IssueStatus.in_progress],
    IssueStatus.in_progress:  [IssueStatus.review, IssueStatus.todo],
    IssueStatus.review:       [IssueStatus.done, IssueStatus.in_progress],
    IssueStatus.done:         [IssueStatus.in_progress],
}
```

---

## 6. Repository / Data Access Layer

### Purpose

The repository layer provides a clean interface between the service layer and the database. It contains all SQLAlchemy query logic. Services never write raw ORM queries — they always go through a repository method.

### Base Repository

A generic `BaseRepository` provides common CRUD operations:

```python
# app/repositories/base.py
from typing import Generic, TypeVar, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    model: Type[ModelType]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: UUID) -> ModelType | None:
        result = await self.db.get(self.model, id)
        return result

    async def list(
        self, offset: int = 0, limit: int = 25, **filters
    ) -> tuple[list[ModelType], int]:
        query = select(self.model)
        for attr, value in filters.items():
            query = query.where(getattr(self.model, attr) == value)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()
        rows = (await self.db.execute(query.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def create(self, data: dict[str, Any]) -> ModelType:
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        for key, value in data.items():
            setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()
```

### Entity Repositories

Each entity has its own repository that extends `BaseRepository` and adds entity-specific queries:

```python
# app/repositories/issue_repository.py
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.issue import Issue

class IssueRepository(BaseRepository[Issue]):
    model = Issue

    async def get_with_comments(self, issue_id: UUID) -> Issue | None:
        result = await self.db.execute(
            select(Issue)
            .options(selectinload(Issue.comments))
            .where(Issue.id == issue_id)
        )
        return result.scalar_one_or_none()

    async def list_backlog(self, project_id: UUID) -> list[Issue]:
        result = await self.db.execute(
            select(Issue)
            .where(Issue.project_id == project_id, Issue.sprint_id == None)
            .order_by(Issue.backlog_rank.asc())
        )
        return list(result.scalars().all())
```

### Session Management

The async SQLAlchemy session is created per HTTP request and injected via FastAPI's `Depends`:

```python
# app/core/dependencies.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        async with session.begin():
            yield session
```

The session is used inside a transaction context (`session.begin()`). On commit, all `flush()` calls within a request are persisted atomically. On unhandled exception, the transaction is automatically rolled back.

### Joins and Eager Loading

- Use `selectinload` for one-to-many relationships (e.g., loading `Issue.comments`).
- Use `joinedload` for many-to-one relationships (e.g., loading `Issue.assignee`).
- Avoid lazy loading — all relationships on models are configured with `lazy="raise"` to prevent accidental N+1 queries in async context.
- Complex filtered list queries with joins are written as explicit `select()` statements in the specific repository method.

### No Raw SQL

All queries use the SQLAlchemy ORM query API. Raw `text()` queries are prohibited. This ensures type safety, migration compatibility, and readability.

---

## 7. Authentication Architecture

### Token Strategy

The system uses a dual-token JWT scheme:

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access Token | 15 minutes | Client memory (not stored server-side) | Authenticate API requests |
| Refresh Token | 7 days | Hashed in `refresh_tokens` DB table | Obtain a new access token |

Access tokens are short-lived to limit exposure if intercepted. Refresh tokens are long-lived but are hashed before storage — the raw token is only ever held by the client.

### Token Generation and Validation

`python-jose` handles JWT encoding and decoding using HS256. The secret key is loaded from environment config:

```python
# app/core/security.py
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(subject: str, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")
```

### `get_current_user` Dependency

```python
# app/core/dependencies.py
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_access_token
from app.repositories.user_repository import UserRepository
from app.exceptions.app_exceptions import UnauthorizedError

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")
    user = await UserRepository(db).get_by_id(UUID(user_id))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or deactivated")
    return user
```

### Refresh Token Flow

1. On login, a raw refresh token (UUID or random bytes) is generated.
2. The raw token is returned to the client.
3. A SHA-256 hash of the raw token is stored in the `refresh_tokens` table alongside `user_id`, `expires_at`, and a nullable `revoked_at`.
4. On `POST /auth/refresh`, the client sends the raw token. The server hashes it, looks up the record, checks expiry and revocation, then issues a new access token (and optionally rotates the refresh token).
5. On `POST /auth/logout`, the matching refresh token record is soft-deleted by setting `revoked_at`.

### Refresh Token Rotation

When a refresh endpoint is called, the old refresh token is immediately revoked (`revoked_at` set) and a new refresh token is issued. This limits the window of token reuse attacks.

### Password Hashing

`passlib[bcrypt]` is used with the default bcrypt work factor (12 rounds). Passwords are never stored in plain text or logged.

---

## 8. Role-Based Authorization

### Role Architecture

Authorization is two-dimensional:

- **System Role** — Stored on `User.system_role`. Values: `admin`, `project_manager`, `developer`. Admin supersedes all project-level checks.
- **Project Role** — Stored on `ProjectMember.project_role`. Values: `project_manager`, `developer`. Scoped to a single project.

### Dependency Factory Pattern

Authorization is enforced by composable FastAPI dependencies:

**Admin-only guard:**

```python
# app/core/dependencies.py
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.system_role != SystemRole.admin:
        raise ForbiddenError("Admin access required")
    return current_user
```

**Project membership resolver:**

```python
async def get_project_member(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMember | None:
    if current_user.system_role == SystemRole.admin:
        return None  # Admins bypass project membership checks
    member = await ProjectMemberRepository(db).get_by_user_and_project(
        user_id=current_user.id, project_id=project_id
    )
    if not member:
        raise ForbiddenError("You are not a member of this project")
    return member
```

**Project role factory — the primary authorization tool:**

```python
def require_project_role(roles: list[ProjectRole]):
    async def dependency(
        project_member: ProjectMember | None = Depends(get_project_member),
        current_user: User = Depends(get_current_user),
    ) -> ProjectMember | None:
        # System admin always passes
        if current_user.system_role == SystemRole.admin:
            return project_member
        if project_member is None or project_member.project_role not in roles:
            raise ForbiddenError(
                f"Required project role: {[r.value for r in roles]}"
            )
        return project_member
    return dependency
```

### Enforcement at Endpoint Level

Authorization dependencies are declared directly on route handlers:

```python
# app/api/v1/sprints.py
@router.post("/{project_id}/sprints/{sprint_id}/start")
async def start_sprint(
    project_id: UUID,
    sprint_id: UUID,
    _: ProjectMember | None = Depends(
        require_project_role([ProjectRole.project_manager])
    ),
    db: AsyncSession = Depends(get_db),
):
    service = SprintService(db)
    return await service.start_sprint(sprint_id, project_id)
```

For endpoints with finer-grained data-dependent rules (e.g., "Developer can only update their own issues"), the dependency grants entry at the `developer` role level, and the service layer performs the ownership check using the pre-fetched `current_user`.

### Authorization Summary Table

| Dependency | Effect |
|---|---|
| `get_current_user` | Requires valid JWT; returns `User` |
| `require_admin` | Requires `system_role == admin` |
| `get_project_member` | Requires project membership (Admin bypasses) |
| `require_project_role([PM])` | Requires PM or Admin |
| `require_project_role([PM, DEV])` | Requires any project member |

---

## 9. Request Lifecycle

The following is the step-by-step path of a single HTTP request through the system, using `PATCH /api/v1/projects/{projectId}/issues/{issueId}/status` as the example:

```
1. HTTP Request arrives at Uvicorn (ASGI server)

2. Middleware Pipeline (applied in registration order)
   a. CORSMiddleware — checks Origin header, adds CORS response headers
   b. RequestIDMiddleware — generates UUID4, attaches as X-Request-ID header
   c. LoggingMiddleware — records start time, method, path

3. FastAPI routes to the matching path operation function

4. Dependency Injection (resolved in dependency graph order)
   a. get_db() — opens async SQLAlchemy session, begins transaction
   b. get_current_user() — extracts Bearer token from Authorization header
      → decode_access_token() validates JWT signature and expiry
      → UserRepository.get_by_id() fetches user from DB
      → raises 401 if invalid or user inactive
   c. get_project_member() — fetches ProjectMember row for this user+project
      → raises 403 if not a member (Admin bypasses)
   d. require_project_role([PM, DEV]) — validates project role
      → raises 403 if insufficient role

5. Route Handler is called with resolved dependencies
   → Receives: project_id, issue_id, StatusChangeRequest schema, db, current_user, project_member

6. Service Layer
   → IssueService(db).change_status(issue_id, new_status, current_user, project_member)
   → Validates business rules (transition allowed? developer owns this issue?)
   → Raises AppException subclass if validation fails

7. Repository Layer
   → IssueRepository.get_by_id(issue_id) — SELECT query
   → IssueRepository.update(issue, {"status": new_status}) — flush to DB
   → IssueStatusHistoryRepository.create({...}) — INSERT audit record

8. Transaction Commit
   → AsyncSession.begin() context manager commits on clean exit
   → Rolls back automatically on exception

9. Response Serialization
   → Service returns ORM model instance
   → FastAPI serializes via response_model Pydantic schema
   → Pydantic v2 model_validate converts ORM → schema

10. LoggingMiddleware completes — logs status code and duration

11. HTTP Response sent to client
    → Body: JSON-serialized resource
    → Headers: Content-Type, X-Request-ID
    → Status: 200 OK
```

---

## 10. Error Handling Patterns

### Exception Hierarchy

```python
# app/exceptions/app_exceptions.py
class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}

class NotFoundError(AppException):
    status_code = 404
    code = "not_found"

class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"

class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"

class ConflictError(AppException):
    status_code = 409
    code = "conflict"

class ValidationError(AppException):
    status_code = 422
    code = "validation_error"

class GoneError(AppException):
    status_code = 410
    code = "gone"
```

### Standard Error Response Shape

All errors — including Pydantic validation failures — are normalized to a single shape:

```json
{
  "error": {
    "code": "not_found",
    "message": "Issue not found",
    "details": {
      "issue_id": "3f7e1c2a-..."
    }
  }
}
```

### Global Exception Handlers

Registered in `main.py` via FastAPI's exception handler mechanism:

```python
# app/exceptions/handlers.py
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed",
                            "details": {"errors": exc.errors()}}},
    )
```

### HTTP Status Code Mapping

| Exception Class | HTTP Status |
|---|---|
| `UnauthorizedError` | 401 |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 |
| `GoneError` | 410 |
| `ConflictError` | 409 |
| `ValidationError` | 422 |
| `AppException` (base) | 500 |
| FastAPI `RequestValidationError` | 422 |

---

## 11. Middleware Pipeline

Middleware is registered in `main.py` in the following order. Starlette applies middleware in **reverse registration order** (last registered runs first), so the logical request order matches the registration order below when using `add_middleware`.

### Middleware Stack (outermost to innermost)

#### 1. CORSMiddleware

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # loaded from .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Handles preflight OPTIONS requests and injects CORS headers. `CORS_ORIGINS` defaults to `["http://localhost:3000"]` in development. In production, set explicitly to the frontend domain.

#### 2. RequestIDMiddleware

A custom Starlette middleware that generates a UUID4 for every incoming request and attaches it to:

- The request's state (`request.state.request_id`) so it can be included in log records.
- The response headers as `X-Request-ID`.

This allows correlating log lines, distributed traces, and error reports to a single request.

```python
# app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

#### 3. LoggingMiddleware

Logs structured information for every request:

- Method and path
- HTTP status code
- Duration in milliseconds
- Request ID (from `request.state.request_id`)

Log output uses Python's `logging` module with JSON formatting in production. In development, human-readable format is acceptable.

```python
# app/middleware/logging.py
import time, logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %d %.1fms [%s]",
            request.method, request.url.path,
            response.status_code, duration_ms,
            getattr(request.state, "request_id", "-"),
        )
        return response
```

#### 4. Rate Limiting (Future Enhancement)

Rate limiting is not included in this version. When needed, the recommended approach is to add `slowapi` (a Starlette-compatible rate limiting library backed by Redis) as a fourth middleware layer. This avoids implementing a custom sliding-window counter from scratch.

---

## 12. External Services

### asyncpg — Async PostgreSQL Driver

`asyncpg` is used as the underlying driver for SQLAlchemy's async engine. It is not called directly; SQLAlchemy's `create_async_engine` uses it via the connection URL:

```
postgresql+asyncpg://user:password@localhost:5432/jira_db
```

`asyncpg` provides true non-blocking I/O for database queries, which is essential for an async FastAPI application. Without it, SQLAlchemy async mode cannot function with PostgreSQL.

### Redis — Refresh Token Blacklisting (Optional, Recommended)

**Recommendation: Include Redis if the deployment already has it available. Skip it for the simplest initial setup.**

Without Redis, token revocation (logout) is handled entirely in the PostgreSQL `refresh_tokens` table by setting `revoked_at`. This works correctly but requires a DB read on every refresh operation.

With Redis, the logout flow additionally writes the refresh token hash to a Redis key with a TTL equal to the token's remaining lifetime. The refresh endpoint checks Redis first (fast O(1) lookup) before hitting the database. This is a minor optimization and adds operational complexity.

Redis is **not** needed for access token revocation because access tokens are short-lived (15 minutes). The 15-minute expiry window is an acceptable revocation lag for this project scope.

**If Redis is included**, the connection is managed via `redis.asyncio` and injected as a dependency alongside the DB session:

```python
# app/core/dependencies.py
import redis.asyncio as aioredis

async def get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)
```

### Celery — Not Recommended

Celery is not included. This system has no background task requirements in its current scope:

- No emails or notifications.
- No scheduled jobs.
- No long-running report generation.

All operations complete within the HTTP request/response cycle. Adding Celery would introduce a message broker (Redis or RabbitMQ), a worker process, and significant operational overhead with no benefit. Celery can be added in a future version if notification emails or async report generation are required.

---

## 13. Deployment Architecture

### Local Development with Docker Compose

The `docker-compose.yml` defines three services:

```yaml
# docker-compose.yml (summary)
services:
  app:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://jira:jira@db:5432/jira_db
    depends_on: [db]
    volumes: ["./:/app"]   # Mount source for hot-reload in dev

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: jira
      POSTGRES_PASSWORD: jira
      POSTGRES_DB: jira_db
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    ports: ["5432:5432"]

  redis:           # Optional — include only if using Redis for token blacklist
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  postgres_data:
```

In development, Uvicorn runs with `--reload` so code changes are picked up automatically without restarting the container.

### Dockerfile — Multi-Stage Build

```dockerfile
# Stage 1: builder — install dependencies
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install --no-cache-dir .

# Stage 2: runtime — minimal image
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

The multi-stage build keeps the final image lean by excluding build tools and pip cache from the runtime layer.

### Environment Variables

All secrets and environment-specific values are managed via `.env` (never committed). The `.env.example` template documents all required keys:

```
# .env.example
DATABASE_URL=postgresql+asyncpg://jira:jira@localhost:5432/jira_db
SECRET_KEY=change-me-to-a-long-random-string
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:3000"]
REDIS_URL=redis://localhost:6379/0   # Optional
DEBUG=false
```

`pydantic-settings` is used in `app/core/config.py` to load and validate these values at startup, failing fast if required variables are missing.

### Production Deployment

For this project scope, the simplest production setup is:

- **Single VPS or cloud VM** (e.g., DigitalOcean Droplet, AWS EC2 t3.small).
- Docker Compose with the production `docker-compose.prod.yml` (no volume mount, no `--reload`, `DEBUG=false`).
- A reverse proxy (Nginx or Caddy) in front of Uvicorn for TLS termination and HTTP/2.
- PostgreSQL managed service (e.g., RDS, Supabase) is recommended over a self-managed container in production.

### Future Kubernetes Path

When the system needs horizontal scaling:

1. The Docker image is published to a container registry (ECR, GCR, Docker Hub).
2. A Kubernetes `Deployment` runs multiple replicas of the app container.
3. A `Service` and `Ingress` replace Nginx.
4. PostgreSQL migrates to a managed cloud database with connection pooling via PgBouncer.
5. A `HorizontalPodAutoscaler` scales based on CPU or request throughput.

This is not needed for the current learning project scope.

### Database Migrations

Alembic is configured for async operation in `alembic/env.py`. Migration workflow:

```bash
# Generate a new migration after changing ORM models
alembic revision --autogenerate -m "add issue status history table"

# Apply migrations to the database
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Migrations are run as a startup step (either in the Dockerfile CMD or as a separate init container in Kubernetes).

---

## 14. Architecture Diagram

```mermaid
graph TD
    Client["Client\n(API Consumer / Test Client)"]

    subgraph Docker["Docker Compose Environment"]
        subgraph App["FastAPI Application"]
            MW["Middleware Pipeline\n(CORS → Request ID → Logging)"]
            Router["API Router\n/api/v1/*"]

            subgraph DI["Dependency Injection"]
                GetDB["get_db()\nAsync DB Session"]
                GetUser["get_current_user()\nJWT Validation"]
                GetRole["require_project_role()\nRole Enforcement"]
            end

            subgraph Layers["Application Layers"]
                Service["Service Layer\nBusiness Logic + Validation"]
                Repo["Repository Layer\nORM Queries + Data Access"]
            end

            Security["security.py\nJWT Encode/Decode\nPassword Hashing"]
        end

        PG[("PostgreSQL\nPrimary Database")]
        Redis[("Redis\nToken Blacklist\n(Optional)")]
    end

    Client -->|"HTTP Request\nBearer Token"| MW
    MW --> Router
    Router --> DI
    GetDB -->|"AsyncSession"| Layers
    GetUser -->|"Decoded User"| GetRole
    GetRole -->|"Authorized User\n+ Project Member"| Service
    Service -->|"Query / Mutate"| Repo
    Repo -->|"SQLAlchemy ORM\nasyncpg driver"| PG
    GetUser -->|"Decode JWT"| Security
    Service -->|"Token Revocation\nCheck (optional)"| Redis
    PG -->|"Query Results"| Repo
    Repo -->|"ORM Models"| Service
    Service -->|"Business Objects"| Router
    Router -->|"Pydantic Schema\nSerialization"| Client
```

### Key Architectural Decisions Summarized

| Decision | Choice | Rationale |
|---|---|---|
| Async all the way | asyncpg + SQLAlchemy async | Non-blocking I/O for high concurrency |
| No service-to-service calls | Services use repos directly | Prevents circular dependencies |
| Repository pattern | BaseRepository + entity repos | Separates query logic from business logic |
| Dependency injection for auth | FastAPI `Depends` | Composable, testable, declarative |
| Dual-token auth | Access (15m) + Refresh (7d) | Balance between security and UX |
| Single Issue table | Discriminated by `type` column | Simplifies queries; types share most fields |
| Soft deletes | `is_active`, `is_archived` | Preserves referential integrity and audit trail |
| Status audit log | `IssueStatusHistory` table | Full traceability of issue state changes |
| No Celery | Deferred | No async task requirements in current scope |
