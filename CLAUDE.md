# CLAUDE.md — Master Instruction Manual
# Simplified Jira-Like Issue Tracking System (Backend)

This file is the authoritative guide for every developer and AI agent working on this project.
Read it fully before making any changes to the codebase.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Folder Structure](#3-folder-structure)
4. [Coding Conventions](#4-coding-conventions)
5. [API Conventions](#5-api-conventions)
6. [Database Conventions](#6-database-conventions)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [Error Handling Conventions](#8-error-handling-conventions)
9. [Testing Conventions](#9-testing-conventions)
10. [Git Workflow](#10-git-workflow)
11. [Environment Variables](#11-environment-variables)
12. [Pattern: Adding a New API Route](#12-pattern-adding-a-new-api-route)
13. [Pattern: Adding a New Model](#13-pattern-adding-a-new-model)
14. [Anti-Patterns to Avoid](#14-anti-patterns-to-avoid)

---

## 1. Project Overview

A RESTful backend API for a simplified project management and issue tracking system modeled after Jira.
**Backend only** — no frontend, no file uploads, no email, no OAuth.

### Core Features
- Multi-project workspace with isolated membership
- Hierarchical issues: **Epic → Story → Task / Bug** (single `issues` table, `type` discriminator)
- Sprint lifecycle: create → start → complete (one active sprint per project enforced at DB level)
- Backlog queue ordered by `backlog_rank`
- JWT auth (access token 15min + refresh token 7 days, stored hashed)
- Role-based access: **Admin** (system-wide) | **Project Manager** (per-project) | **Developer** (per-project)
- Full status audit log (`issue_status_history`)

### Key Documents
- `PRD.md` — Full product requirements, business rules, edge cases
- `ARCHITECTURE.md` — System design, folder structure, auth patterns, middleware
- `DATABASE.md` — Complete schema, indexes, ORM models, migration strategy

---

## 2. Tech Stack

| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| ASGI Server | Uvicorn | 0.30+ |
| ORM | SQLAlchemy async | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Database | PostgreSQL | 16+ |
| Async DB Driver | asyncpg | 0.29+ |
| JWT | python-jose[cryptography] | 3.3+ |
| Password Hashing | passlib[bcrypt] | 1.7+ |
| Validation | Pydantic v2 | 2.7+ |
| Config | pydantic-settings | 2.0+ |
| Testing | pytest + pytest-asyncio | 8.0+ / 0.23+ |
| HTTP Test Client | httpx | 0.27+ |

**Not used (deferred):** Celery, Redis (optional for token blacklist only — see ARCHITECTURE.md §12).

---

## 3. Folder Structure

```
jira-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Aggregates all routers
│   │       ├── auth.py            # /auth/* endpoints
│   │       ├── users.py           # /users/* endpoints (Admin)
│   │       ├── projects.py        # /projects/* endpoints
│   │       ├── epics.py           # /projects/:id/epics/*
│   │       ├── issues.py          # /projects/:id/issues/*
│   │       ├── sprints.py         # /projects/:id/sprints/*
│   │       ├── backlog.py         # /projects/:id/backlog/*
│   │       └── comments.py        # /projects/:id/issues/:id/comments/*
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── database.py            # Engine + session factory
│   │   ├── security.py            # JWT encode/decode, password hashing
│   │   └── dependencies.py        # All FastAPI Depends functions
│   ├── models/
│   │   ├── base.py                # Base, TimestampMixin, UUIDMixin
│   │   ├── user.py                # User, RefreshToken
│   │   ├── project.py             # Project, ProjectMember
│   │   ├── epic.py                # Epic
│   │   ├── issue.py               # Issue (story/task/bug)
│   │   ├── sprint.py              # Sprint
│   │   ├── comment.py             # Comment
│   │   └── issue_status_history.py
│   ├── schemas/
│   │   ├── common.py              # PaginatedResponse, ErrorResponse
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── epic.py
│   │   ├── issue.py
│   │   ├── sprint.py
│   │   ├── backlog.py
│   │   └── comment.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── project_service.py
│   │   ├── epic_service.py
│   │   ├── issue_service.py
│   │   ├── sprint_service.py
│   │   ├── backlog_service.py
│   │   └── comment_service.py
│   ├── repositories/
│   │   ├── base.py                # BaseRepository (generic CRUD)
│   │   ├── user_repository.py
│   │   ├── refresh_token_repository.py
│   │   ├── project_repository.py
│   │   ├── project_member_repository.py
│   │   ├── epic_repository.py
│   │   ├── issue_repository.py
│   │   ├── sprint_repository.py
│   │   ├── comment_repository.py
│   │   └── issue_status_history_repository.py
│   ├── middleware/
│   │   ├── request_id.py          # X-Request-ID header
│   │   └── logging.py             # Structured request logging
│   └── exceptions/
│       ├── app_exceptions.py      # AppException hierarchy
│       └── handlers.py            # FastAPI exception handlers
├── tests/
│   ├── conftest.py                # Fixtures: DB, client, factories
│   ├── unit/
│   └── integration/
├── alembic/
│   ├── env.py
│   └── versions/
├── main.py                        # App factory
├── pyproject.toml
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

**Rule:** One file per module per layer. Never put two entities in the same service/repository file unless they are tightly coupled (e.g., `User` + `RefreshToken` in `user.py`).

---

## 4. Coding Conventions

### Python Style
- Python 3.12+ syntax throughout. Use `X | Y` union types, not `Optional[X]`.
- All functions that touch the database must be `async def`.
- All public functions must have type annotations.
- Use `from __future__ import annotations` only if needed for forward references.
- Line length: 100 characters max.
- Imports: stdlib → third-party → local, separated by blank lines.

### Naming
| Thing | Convention | Example |
|---|---|---|
| Files | snake_case | `issue_service.py` |
| Classes | PascalCase | `IssueService`, `IssueRepository` |
| Functions/methods | snake_case | `get_by_id`, `change_status` |
| Variables | snake_case | `project_member`, `current_user` |
| Constants | UPPER_SNAKE | `ALLOWED_TRANSITIONS` |
| DB columns | snake_case | `backlog_rank`, `created_at` |
| Pydantic schemas | PascalCase + suffix | `IssueCreate`, `IssueResponse`, `IssueUpdate` |
| Enums (Python) | PascalCase | `IssueStatus`, `SystemRole` |
| Enum values | lowercase snake | `IssueStatus.in_progress` |

### Pydantic Schemas
- Always use three distinct schema classes per entity: `XCreate`, `XUpdate`, `XResponse`.
- `XUpdate` fields must all be `Optional` (PATCH semantics).
- `XResponse` must use `model_config = ConfigDict(from_attributes=True)` to support ORM → schema conversion.
- Never expose `password_hash` in any response schema.

```python
# Correct pattern
class IssueCreate(BaseModel):
    title: str
    type: IssueType
    priority: IssuePriority = IssuePriority.medium

class IssueUpdate(BaseModel):
    title: str | None = None
    priority: IssuePriority | None = None

class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    type: IssueType
    status: IssueStatus
```

### Services
- Each service is a **class** initialized with `db: AsyncSession`.
- Services instantiate their own repositories in `__init__`.
- Services hold **all business logic** — validation, authorization checks, side effects.
- Services do **not** call other services. Use repositories directly for cross-module data needs.
- Services do **not** import from `app.api` or `app.core.dependencies`.

```python
class EpicService:
    def __init__(self, db: AsyncSession):
        self.epic_repo = EpicRepository(db)
        self.issue_repo = IssueRepository(db)  # OK: repo, not service
```

### Repositories
- Each repository extends `BaseRepository[ModelType]` with `model = ModelClass`.
- Only repositories write SQLAlchemy queries. No queries in services or route handlers.
- Use `flush()` after writes, never `commit()` — the session context manager commits.
- Use `selectinload` for one-to-many, `joinedload` for many-to-one.
- All relationships on models use `lazy="raise"` — always explicit eager load.

---

## 5. API Conventions

### URL Structure
- Base path: `/api/v1`
- Resources are **nouns, plural, lowercase**: `/projects`, `/issues`, `/comments`
- Nested under ownership: `/projects/{project_id}/issues/{issue_id}/comments`
- State-change actions as sub-resources: `/sprints/{sprint_id}/start`, `/sprints/{sprint_id}/complete`
- Never use verbs in URLs: ~~`/getIssues`~~, ~~`/createProject`~~

### HTTP Methods
| Intent | Method | Success Status |
|---|---|---|
| Create resource | POST | 201 Created |
| Read resource / list | GET | 200 OK |
| Partial update | PATCH | 200 OK |
| Delete resource | DELETE | 204 No Content |
| State change action | POST (sub-resource) | 200 OK |

### Path Parameters
- Always `UUID` type. FastAPI validates automatically.
- Use descriptive names: `project_id`, `issue_id`, `sprint_id` — not `id`.

### Query Parameters for Lists
All list endpoints support:
- `page: int = 1` (1-based)
- `limit: int = 25` (max 100)

Issue list additionally supports: `type`, `status`, `priority`, `assignee_id`, `epic_id`, `sprint_id`

### Response Shape
- Single resource: return the Pydantic response schema directly (no wrapper).
- List / paginated: return `PaginatedResponse[XResponse]`:

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
```

### Route Handler Rules
- Route handlers must be **thin**. No business logic. No DB queries.
- Always declare `response_model` on the decorator.
- Always declare `status_code` on the decorator.
- Inject `current_user` via dependency — never decode JWT manually in a handler.

```python
@router.post(
    "/{project_id}/epics",
    response_model=EpicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_epic(
    project_id: UUID,
    body: EpicCreate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> EpicResponse:
    service = EpicService(db)
    return await service.create_epic(project_id, body, current_user)
```

---

## 6. Database Conventions

### Primary Keys
- Every table uses UUID PK: `id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))`
- Never use integer sequences or auto-increment IDs.

### Timestamps
- All timestamps: `DateTime(timezone=True)` (maps to `TIMESTAMPTZ` in PostgreSQL).
- `created_at`: `server_default=func.now()`, never updated.
- `updated_at`: `server_default=func.now()`, `onupdate=func.now()`.
- Use `TimestampMixin` from `app/models/base.py` for both columns.

### Enums
- Python enums in `app/models/` (or `app/schemas/`) mirror PostgreSQL native enums.
- Use SQLAlchemy `Enum(PythonEnum, name="enum_name")` to map to native PG ENUM type.
- Enum values are **lowercase snake_case**: `in_progress`, `project_manager`.

### Soft Deletes
- **Users**: `is_active = False` (never hard-delete).
- **Projects**: `is_archived = True` (never hard-delete).
- **Issues and Comments**: hard-delete is allowed (Admin/PM only).
- Soft-deleted records remain in the DB — filter `is_active = True` / `is_archived = False` in queries.

### Self-Referential FK (issues.parent_id)
- `parent_id` references `issues.id` with `ON DELETE SET NULL`.
- Only valid for `task` and `bug` types. `story` must have `parent_id = NULL` (CHECK constraint enforces this).

### Session Rules
- Never call `session.commit()` directly — the `get_db()` dependency manages the transaction via `session.begin()`.
- Always call `session.flush()` after writes so the row gets an ID before the transaction ends.
- Always call `session.refresh(instance)` after flush to load server-generated values.

### Foreign Key ON DELETE Behaviors
| FK | Behavior | Reason |
|---|---|---|
| `refresh_tokens.user_id` → users | CASCADE | Tokens are meaningless without the user |
| `project_members.user_id` → users | RESTRICT | Deactivate user in app; don't break project |
| `project_members.project_id` → projects | CASCADE | Members removed when project deleted |
| `epics.project_id` → projects | RESTRICT | Prevent deleting project with epics |
| `sprints.project_id` → projects | RESTRICT | Prevent deleting project with sprints |
| `issues.sprint_id` → sprints | SET NULL | Issues return to backlog when sprint deleted |
| `issues.epic_id` → epics | RESTRICT | Blocked in app before reaching DB |
| `issues.parent_id` → issues | SET NULL | Orphaned child issues stay, lose parent ref |
| `comments.issue_id` → issues | CASCADE | Comments deleted with their issue |
| `issue_status_history.issue_id` → issues | CASCADE | History deleted with issue |

### Indexing Rules
- **Index every FK column** — essential for join performance.
- **Composite index** `(project_id, backlog_rank)` for backlog ordering queries.
- **Partial unique index** on sprints: `WHERE status = 'active'` — enforces one active sprint per project at DB level. Do not remove this index.
- **Unique index** on `(project_id, user_id)` in `project_members`.

---

## 7. Authentication & Authorization

### JWT Tokens
- **Access token**: 15-minute lifetime, `{"sub": user_id, "type": "access"}`. Not stored server-side.
- **Refresh token**: 7-day lifetime. SHA-256 hash stored in `refresh_tokens` table. Raw token returned to client only at login/refresh.
- Refresh tokens are rotated on every `/auth/refresh` call (old revoked, new issued).
- All token operations are in `app/core/security.py`. Never call `jose.jwt` directly outside that file.

### Dependency Chain
Always compose dependencies — never duplicate auth logic in route handlers:

```
get_db()                          → AsyncSession
get_current_user(db)              → User (validates JWT, checks is_active)
require_admin(current_user)       → User (system_role == admin)
get_project_member(project_id, current_user, db) → ProjectMember | None
require_project_role([roles])(project_member, current_user) → ProjectMember | None
```

### Authorization Rules
- **System Admin** supersedes all project-level checks. `get_project_member` returns `None` for admins (they bypass membership).
- **Project Manager**: project-level role stored in `project_members.project_role`.
- **Developer**: can only update/change status on issues **assigned to them** — enforce in service layer, not dependency.
- Data-dependent ownership checks belong in the **service layer**, not in dependencies.

```python
# In service, not dependency:
if current_user.system_role != SystemRole.admin:
    if project_member.project_role == ProjectRole.developer:
        if issue.assignee_id != current_user.id:
            raise ForbiddenError("Developers can only update their own issues")
```

---

## 8. Error Handling Conventions

### Exception Classes (app/exceptions/app_exceptions.py)
Always raise the appropriate subclass. Never raise `HTTPException` directly in services or repositories.

| Exception | HTTP | When to use |
|---|---|---|
| `UnauthorizedError` | 401 | Invalid/expired token, wrong password |
| `ForbiddenError` | 403 | Valid user, insufficient role/ownership |
| `NotFoundError` | 404 | Resource doesn't exist |
| `GoneError` | 410 | Resource existed but is archived/deleted |
| `ConflictError` | 409 | Duplicate, constraint violation, business rule block |
| `ValidationError` | 422 | Business-level validation failure (not schema) |
| `AppException` | 500 | Unexpected errors (rarely raised directly) |

### Error Response Shape
All errors return this exact JSON shape:
```json
{
  "error": {
    "code": "not_found",
    "message": "Issue not found",
    "details": { "issue_id": "3f7e1c2a-..." }
  }
}
```
Never return a different shape. The global handlers in `app/exceptions/handlers.py` ensure this for all exceptions including Pydantic `RequestValidationError`.

### When to Include `details`
- `NotFoundError`: include the resource ID
- `ConflictError`: include what conflicted
- `ValidationError`: include the field name and why
- `ForbiddenError`: keep vague for security (don't leak resource existence)

---

## 9. Testing Conventions

### Test Structure
```
tests/
├── conftest.py          # Shared: async DB session, test client, user/project factories
├── unit/                # Test services in isolation (mock repositories)
│   ├── test_auth_service.py
│   ├── test_issue_service.py
│   └── test_sprint_service.py
└── integration/         # Test full HTTP stack against a real test DB
    ├── test_auth.py
    ├── test_projects.py
    ├── test_issues.py
    ├── test_sprints.py
    └── test_comments.py
```

### Rules
- Use a **separate test database** — never run tests against the development DB.
- Use `pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml`.
- Use `httpx.AsyncClient` with `ASGITransport` for integration tests — never use `TestClient` (sync).
- Every test must be fully isolated — use transactions that roll back after each test, or recreate schema per session.
- **Never** assert on exact UUIDs — assert on structure, status codes, and field values.

### Test Naming
```python
async def test_create_issue_returns_201_with_correct_type(): ...
async def test_developer_cannot_update_unassigned_issue(): ...
async def test_sprint_complete_moves_unfinished_issues_to_backlog(): ...
```

### Coverage Requirements
- Every service method: unit test with happy path + key failure paths.
- Every API endpoint: integration test with at least: success case, auth failure (401), permission failure (403), not-found (404).
- Status transition logic: test every valid transition and at least 3 invalid transitions.

### conftest.py Factories
Use factory functions, not fixtures, for creating test data:
```python
async def create_user(db, role=SystemRole.developer, **kwargs) -> User: ...
async def create_project(db, created_by, **kwargs) -> Project: ...
async def create_issue(db, project, reporter, type=IssueType.task, **kwargs) -> Issue: ...
```

---

## 10. Git Workflow

### Branch Naming
```
feature/issue-service-status-transitions
fix/sprint-complete-backlog-rank-gaps
chore/add-index-on-sprint-status
docs/update-api-conventions
```

### Commit Messages
Follow Conventional Commits:
```
feat(issues): add status transition validation
fix(sprints): prevent starting sprint when one is active
chore(deps): bump fastapi to 0.115.6
test(auth): add refresh token rotation test
refactor(repos): extract base list method to BaseRepository
```

### PR Rules
- Every PR must have at least one passing test for the changed behavior.
- Every PR must update `alembic/versions/` if any model changed.
- Never merge a PR with failing tests.
- Never force-push to `main`.

### What NOT to Commit
- `.env` files (use `.env.example` only)
- `__pycache__/`, `.pytest_cache/`, `*.pyc`
- IDE config files (`.vscode/`, `.idea/`)

---

## 11. Environment Variables

All variables are defined in `.env` (never committed) and validated at startup by `app/core/config.py` using `pydantic-settings`. Copy `.env.example` to get started.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | `postgresql+asyncpg://user:pass@host:port/db` |
| `SECRET_KEY` | Yes | — | Random string ≥ 32 chars for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime in days |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | JSON array of allowed origins |
| `REDIS_URL` | No | — | `redis://host:port/db` — only if using Redis for token blacklist |
| `DEBUG` | No | `false` | Enables debug mode and verbose logging |

**Security rules:**
- `SECRET_KEY` must never be a short or guessable value in production.
- Never hardcode any env var value in source code.
- Never log the `SECRET_KEY`, `DATABASE_URL` password, or any token value.

---

## 12. Pattern: Adding a New API Route

Follow this checklist in order for every new endpoint:

### Step 1 — Schema (`app/schemas/<module>.py`)
```python
class EpicCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "EpicCreate":
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

class EpicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    status: EpicStatus
    created_at: datetime
```

### Step 2 — Repository method (`app/repositories/epic_repository.py`)
Add only if the query doesn't exist in `BaseRepository`:
```python
async def get_with_stories(self, epic_id: UUID) -> Epic | None:
    result = await self.db.execute(
        select(Epic)
        .options(selectinload(Epic.stories))
        .where(Epic.id == epic_id)
    )
    return result.scalar_one_or_none()
```

### Step 3 — Service method (`app/services/epic_service.py`)
```python
async def create_epic(
    self,
    project_id: UUID,
    data: EpicCreate,
    current_user: User,
) -> Epic:
    # 1. Validate project exists and is not archived
    project = await self.project_repo.get_by_id(project_id)
    if not project:
        raise NotFoundError("Project not found", {"project_id": str(project_id)})
    if project.is_archived:
        raise GoneError("Project is archived")

    # 2. Business rule validation
    if data.end_date and data.start_date and data.end_date <= data.start_date:
        raise ValidationError("end_date must be after start_date")

    # 3. Create
    return await self.epic_repo.create({
        "project_id": project_id,
        "title": data.title,
        "description": data.description,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "status": EpicStatus.backlog,
        "created_by": current_user.id,
    })
```

### Step 4 — Route handler (`app/api/v1/epics.py`)
```python
@router.post(
    "/{project_id}/epics",
    response_model=EpicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_epic(
    project_id: UUID,
    body: EpicCreate,
    current_user: User = Depends(get_current_user),
    _: ProjectMember | None = Depends(require_project_role([ProjectRole.project_manager])),
    db: AsyncSession = Depends(get_db),
) -> EpicResponse:
    return await EpicService(db).create_epic(project_id, body, current_user)
```

### Step 5 — Register router (`app/api/v1/router.py`)
```python
from app.api.v1 import epics
v1_router.include_router(epics.router, prefix="/projects", tags=["Epics"])
```

### Step 6 — Write tests
- `tests/integration/test_epics.py`: POST success (201), 403 (developer cannot create), 404 (project not found), 422 (end before start), 410 (archived project).

---

## 13. Pattern: Adding a New Model

Follow this checklist in order when adding a new database table:

### Step 1 — ORM Model (`app/models/<entity>.py`)
```python
# app/models/epic.py
import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Enum, Date, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base, TimestampMixin
from app.models.enums import EpicStatus   # Python enum

class Epic(Base, TimestampMixin):
    __tablename__ = "epics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EpicStatus] = mapped_column(
        Enum(EpicStatus, name="epic_status_enum"), nullable=False, default=EpicStatus.backlog
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    # Relationships — always lazy="raise"
    project: Mapped["Project"] = relationship("Project", back_populates="epics", lazy="raise")
    stories: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="epic", lazy="raise",
        primaryjoin="and_(Issue.epic_id == Epic.id, Issue.type == 'story')"
    )
```

### Step 2 — Alembic Migration
```bash
# After adding the model
alembic revision --autogenerate -m "add epics table"
# Review the generated file in alembic/versions/
alembic upgrade head
```

**Always review autogenerated migrations** — Alembic may miss:
- Server defaults (`gen_random_uuid()`)
- Native ENUM creation (must precede the table)
- Partial indexes (add manually)
- CHECK constraints (add manually)

### Step 3 — Repository (`app/repositories/epic_repository.py`)
```python
from app.repositories.base import BaseRepository
from app.models.epic import Epic

class EpicRepository(BaseRepository[Epic]):
    model = Epic
    # Add entity-specific methods here
```

### Step 4 — Register model in `app/models/__init__.py`
Import the model so Alembic's `env.py` discovers it:
```python
from app.models.epic import Epic  # noqa: F401
```

### Step 5 — Add to `app/models/base.py` imports
Ensure `Base.metadata` includes the new table before Alembic runs.

---

## 14. Anti-Patterns to Avoid

### Database Anti-Patterns

❌ **Do not use integer IDs.**
```python
# WRONG
id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
# CORRECT
id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
```

❌ **Do not call `session.commit()` in repositories or services.**
```python
# WRONG — breaks transaction management
await self.db.commit()
# CORRECT
await self.db.flush()  # write to DB within transaction
await self.db.refresh(instance)
```

❌ **Do not use lazy loading.**
```python
# WRONG — will raise MissingGreenlet in async context
issue.comments  # lazy load — crashes or causes N+1
# CORRECT — use selectinload in repository
await self.db.execute(select(Issue).options(selectinload(Issue.comments)).where(...))
```

❌ **Do not write raw SQL.**
```python
# WRONG
await self.db.execute(text("SELECT * FROM issues WHERE project_id = :pid"), {"pid": project_id})
# CORRECT
await self.db.execute(select(Issue).where(Issue.project_id == project_id))
```

❌ **Do not skip the partial unique index on sprints.**
The index `idx_sprints_one_active_per_project` is the database-level enforcement of a critical business rule. Never drop it.

### Service/Business Logic Anti-Patterns

❌ **Do not put business logic in route handlers.**
```python
# WRONG — business logic in handler
@router.post("/{project_id}/sprints/{sprint_id}/start")
async def start_sprint(...):
    active = await db.execute(select(Sprint).where(Sprint.project_id == project_id, Sprint.status == "active"))
    if active.scalar_one_or_none():
        raise HTTPException(409, "Active sprint exists")
    ...
# CORRECT — delegate to service
    return await SprintService(db).start_sprint(sprint_id, project_id)
```

❌ **Do not call one service from another service.**
```python
# WRONG — circular dep risk
class SprintService:
    async def complete_sprint(self, ...):
        await IssueService(self.db).move_to_backlog(...)  # NO
# CORRECT — use repository directly
        await self.issue_repo.bulk_update_sprint(sprint_id=None, issue_ids=unfinished_ids)
```

❌ **Do not raise `HTTPException` in services or repositories.**
```python
# WRONG
raise HTTPException(status_code=404, detail="Issue not found")
# CORRECT
raise NotFoundError("Issue not found", {"issue_id": str(issue_id)})
```

### API Anti-Patterns

❌ **Do not use verbs in route paths.**
```python
# WRONG
@router.post("/projects/{id}/getIssues")
@router.post("/projects/{id}/createSprint")
# CORRECT
@router.get("/projects/{project_id}/issues")
@router.post("/projects/{project_id}/sprints")
```

❌ **Do not expose internal IDs or hashed secrets in responses.**
```python
# WRONG — schema includes password_hash
class UserResponse(BaseModel):
    id: UUID
    email: str
    password_hash: str  # NEVER
# CORRECT
class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    system_role: SystemRole
```

❌ **Do not skip `response_model` on route decorators.**
```python
# WRONG — no response_model = no output validation, no OpenAPI schema
@router.get("/projects/{project_id}/issues/{issue_id}")
async def get_issue(...):
    ...
# CORRECT
@router.get("...", response_model=IssueResponse, status_code=200)
```

### Auth Anti-Patterns

❌ **Do not decode JWT manually outside `security.py`.**
```python
# WRONG — duplicate logic, easy to get wrong
payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
# CORRECT — use the dependency
current_user: User = Depends(get_current_user)
```

❌ **Do not enforce authorization in the repository layer.**
Authorization belongs in: dependencies (role checks) and services (ownership/data-level checks). Repositories are pure data access with no knowledge of who is calling them.

❌ **Do not return 404 when the real error is 403.**
If a user tries to access a project they're not a member of, return `403 Forbidden`, not `404 Not Found`. Returning 404 for unauthorized access is acceptable only when you intentionally want to hide resource existence from unauthorized users — be consistent.

### Testing Anti-Patterns

❌ **Do not test against the production or development database.**
Always use a dedicated test database, configured via a separate `TEST_DATABASE_URL` env var.

❌ **Do not write tests that depend on insertion order or specific UUIDs.**
```python
# WRONG
assert response.json()["id"] == "3f7e1c2a-0000-0000-0000-000000000001"
# CORRECT
assert UUID(response.json()["id"])  # just validate it's a valid UUID
```

❌ **Do not skip testing failure paths.**
Every endpoint must have a test for: 401 (no token), 403 (wrong role), 404 (missing resource), and at least one 422 (bad input). Happy-path-only tests are insufficient.

---

## Quick Reference

### Common Imports
```python
# In route handlers
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user, require_project_role
from app.models.user import User
from app.models.project import ProjectMember

# In services
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions.app_exceptions import NotFoundError, ForbiddenError, ConflictError

# In repositories
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, joinedload
from app.repositories.base import BaseRepository
```

### Running the App
```bash
# Development (with hot reload)
uvicorn main:app --reload --port 8000

# With Docker Compose
docker compose up

# Run migrations
alembic upgrade head

# Generate new migration
alembic revision --autogenerate -m "describe change"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### OpenAPI Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
