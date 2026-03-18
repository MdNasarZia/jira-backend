# Jira Backend API

A RESTful backend API for a simplified project management and issue tracking system modeled after Jira. Supports multi-project workspaces, hierarchical issues (Epic, Story, Task, Bug), sprint lifecycle management, backlog ordering, and role-based access control.

## Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI 0.115+
- **ORM:** SQLAlchemy 2.0+ (async)
- **Database:** PostgreSQL 16+
- **Migrations:** Alembic 1.13+
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-asyncio + httpx

## Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker and Docker Compose (optional)

## Quick Start with Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -e ".[dev]"

cp .env.example .env
# Edit .env with your database credentials

alembic upgrade head

uvicorn main:app --reload --port 8000
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | - | PostgreSQL async connection string |
| `SECRET_KEY` | Yes | - | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 15 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | Allowed CORS origins |
| `REDIS_URL` | No | - | Redis URL (optional) |
| `DEBUG` | No | false | Enable debug mode |

## Running Tests

```bash
# Set test database URL
export TEST_DATABASE_URL=postgresql+asyncpg://jira:jira@localhost:5432/jira_test_db

pytest tests/ -v
pytest tests/ --cov=app --cov-report=term-missing
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Login and get tokens |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Get current user |
| GET | `/api/v1/users` | List users (Admin) |
| GET | `/api/v1/users/{id}` | Get user (Admin) |
| PATCH | `/api/v1/users/{id}` | Update user (Admin) |
| PATCH | `/api/v1/users/{id}/role` | Change user role (Admin) |
| POST | `/api/v1/projects` | Create project (Admin) |
| GET | `/api/v1/projects` | List projects |
| GET | `/api/v1/projects/{id}` | Get project |
| PATCH | `/api/v1/projects/{id}` | Update project |
| POST | `/api/v1/projects/{id}/archive` | Archive project (Admin) |
| GET/POST | `/api/v1/projects/{id}/members` | List/add members |
| PATCH/DELETE | `/api/v1/projects/{id}/members/{uid}` | Update/remove member |
| POST/GET | `/api/v1/projects/{id}/epics` | Create/list epics |
| GET/PATCH/DELETE | `/api/v1/projects/{id}/epics/{eid}` | Get/update/delete epic |
| POST/GET | `/api/v1/projects/{id}/sprints` | Create/list sprints |
| GET/PATCH/DELETE | `/api/v1/projects/{id}/sprints/{sid}` | Get/update/delete sprint |
| POST | `/api/v1/projects/{id}/sprints/{sid}/start` | Start sprint |
| POST | `/api/v1/projects/{id}/sprints/{sid}/complete` | Complete sprint |
| POST/GET | `/api/v1/projects/{id}/issues` | Create/list issues |
| GET/PATCH/DELETE | `/api/v1/projects/{id}/issues/{iid}` | Get/update/delete issue |
| PATCH | `/api/v1/projects/{id}/issues/{iid}/status` | Change issue status |
| GET | `/api/v1/projects/{id}/issues/{iid}/history` | Get status history |
| GET | `/api/v1/projects/{id}/backlog` | Get backlog |
| POST | `/api/v1/projects/{id}/backlog/reorder` | Reorder backlog |
| POST | `/api/v1/projects/{id}/backlog/{iid}/move-to-sprint` | Move issue to sprint |
| POST/GET | `/api/v1/projects/{id}/issues/{iid}/comments` | Create/list comments |
| PATCH/DELETE | `/api/v1/projects/{id}/issues/{iid}/comments/{cid}` | Update/delete comment |

## Architecture

The application follows a layered architecture with route handlers, services, and repositories. Route handlers are thin and delegate all business logic to services, which in turn use repositories for data access. All database operations are async, using SQLAlchemy 2.0 with asyncpg, and transactions are managed by the dependency injection layer.

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
