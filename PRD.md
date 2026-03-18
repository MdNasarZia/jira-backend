# Product Requirements Document
# Simplified Jira-Like Issue Tracking System (Backend)

**Version:** 1.0
**Date:** 2026-03-09
**Type:** Learning Project — Backend Only

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Tech Stack Recommendation](#2-tech-stack-recommendation)
3. [User Roles & Permissions](#3-user-roles--permissions)
4. [Modules & Features](#4-modules--features)
5. [Data Entities & Attributes](#5-data-entities--attributes)
6. [API Endpoints](#6-api-endpoints)
7. [Validation Rules](#7-validation-rules)
8. [Edge Cases](#8-edge-cases)
9. [Business Rules Summary](#9-business-rules-summary)

---

## 1. System Overview

A RESTful backend API that models a simplified project management and issue tracking system, inspired by Jira. It supports multi-project workspaces, hierarchical issue types (Epic → Story → Task/Bug), sprint-based planning, backlog management, and role-based access control.

### Core Capabilities

- Multi-project workspace with isolated membership
- Hierarchical issues: Epic → Story → Task / Bug
- Sprint lifecycle management (create, start, complete)
- Backlog queue per project
- Issue assignment, status transitions, and comments
- Role-based permissions (Admin, Project Manager, Developer)

### Out of Scope (for this version)

- Frontend / UI
- File attachments
- Notifications / email
- OAuth / third-party SSO
- Time tracking
- Reporting & analytics

---

## 2. Tech Stack Recommendation

| Layer         | Choice                          |
|---------------|---------------------------------|
| Language      | Python (3.12+)                  |
| Framework     | FastAPI                         |
| ORM           | SQLAlchemy (async) + Alembic    |
| Database      | PostgreSQL                      |
| Auth          | JWT (access + refresh tokens) via python-jose |
| Validation    | Pydantic v2 (built into FastAPI)|
| Testing       | Pytest + httpx (AsyncClient)    |
| Server        | Uvicorn (ASGI)                  |

---

## 3. User Roles & Permissions

### Role Definitions

| Role              | Scope                                                         |
|-------------------|---------------------------------------------------------------|
| **Admin**         | System-wide. Manages users, projects, and all resources.      |
| **Project Manager** | Per-project. Manages sprints, epics, stories, assignments.  |
| **Developer**     | Per-project. Creates/updates tasks and bugs, adds comments.   |

### Permission Matrix

| Action                             | Admin | PM  | Developer |
|------------------------------------|-------|-----|-----------|
| Create / delete users              | ✅    | ❌  | ❌        |
| Create / archive projects          | ✅    | ❌  | ❌        |
| Add members to project             | ✅    | ✅  | ❌        |
| Remove members from project        | ✅    | ✅  | ❌        |
| Create / delete epics              | ✅    | ✅  | ❌        |
| Create / update / delete stories   | ✅    | ✅  | ❌        |
| Create tasks & bugs                | ✅    | ✅  | ✅        |
| Update own tasks & bugs            | ✅    | ✅  | ✅        |
| Update any issue (in their project)| ✅    | ✅  | ❌        |
| Delete tasks & bugs                | ✅    | ✅  | ❌        |
| Assign issues                      | ✅    | ✅  | ❌        |
| Change issue status                | ✅    | ✅  | ✅ (own)  |
| Create / start / complete sprints  | ✅    | ✅  | ❌        |
| Move issues to/from sprint/backlog | ✅    | ✅  | ❌        |
| Add comments                       | ✅    | ✅  | ✅        |
| Edit / delete own comments         | ✅    | ✅  | ✅        |
| Delete any comment                 | ✅    | ✅  | ❌        |
| View all project data              | ✅    | ✅  | ✅ (member only) |

---

## 4. Modules & Features

### 4.1 Authentication Module

- **Register** — Create a new user account with name, email, and password.
- **Login** — Authenticate via email/password; receive JWT access token + refresh token.
- **Refresh token** — Exchange refresh token for new access token.
- **Logout** — Invalidate refresh token.
- **Get current user** — Return authenticated user's profile.
- **Change password** — Authenticated user updates their own password.

### 4.2 User Management Module (Admin only)

- List all users (with pagination and search).
- Get user by ID.
- Update user role.
- Soft-delete (deactivate) a user.
- Restore a deactivated user.

### 4.3 Project Module

- Create a project (Admin).
- List all projects (Admin sees all; PM/Developer see only their projects).
- Get project details (members, stats).
- Update project (name, description, key).
- Archive / restore project (Admin).
- Add member to project with a role (Admin / PM).
- Remove member from project (Admin / PM).
- Update a member's role within a project.

### 4.4 Epic Module

- Create an epic within a project.
- List epics for a project.
- Get epic details (with linked stories).
- Update epic (title, description, status, dates).
- Delete epic (only if it has no stories).

### 4.5 Story Module

- Create a story within a project, optionally linked to an epic.
- List stories for a project (filterable by epic, status, sprint, assignee).
- Get story details (with child tasks and bugs).
- Update story (title, description, priority, assignee, status, story points).
- Move story to/from epic.
- Delete story (only if it has no child issues).

### 4.6 Task & Bug Module

- Create a task or bug within a project, linked to a story (optional).
- List issues for a project (filterable by type, status, assignee, sprint, story).
- Get issue details (with comments).
- Update issue (title, description, priority, assignee, status, story points).
- Delete issue (Admin / PM only).
- Change issue status (with allowed transition validation).

### 4.7 Sprint Module

- Create a sprint for a project (name, goal, start date, end date).
- List sprints for a project (active, planned, completed).
- Get sprint details (with all issues in it).
- Start a sprint (only one active sprint per project at a time).
- Complete a sprint (moves unfinished issues to backlog or next sprint).
- Delete a sprint (only if it has no issues and is not active).
- Add issue(s) to sprint.
- Remove issue(s) from sprint (returns to backlog).

### 4.8 Backlog Module

- List backlog issues for a project (issues not assigned to any sprint).
- Reorder backlog items (update rank/position).
- Move backlog issue to a sprint.
- Move sprint issue back to backlog.

### 4.9 Comment Module

- Add comment to an issue.
- List comments for an issue (paginated, ordered by created_at).
- Update own comment.
- Delete own comment (Admin / PM can delete any comment).

### 4.10 Issue Assignment Module

- Assign an issue to a project member.
- Unassign an issue.
- List issues assigned to a specific user in a project.

---

## 5. Data Entities & Attributes

### 5.1 User

| Column         | Type         | Notes                            |
|----------------|--------------|----------------------------------|
| id             | UUID (PK)    |                                  |
| name           | VARCHAR(100) | Required                         |
| email          | VARCHAR(255) | Unique, required                 |
| password_hash  | TEXT         | bcrypt hash                      |
| system_role    | ENUM         | admin, project_manager, developer|
| is_active      | BOOLEAN      | Default true                     |
| created_at     | TIMESTAMP    |                                  |
| updated_at     | TIMESTAMP    |                                  |

### 5.2 RefreshToken

| Column      | Type      | Notes                      |
|-------------|-----------|----------------------------|
| id          | UUID (PK) |                            |
| user_id     | UUID (FK) | → User                     |
| token_hash  | TEXT      | Hashed refresh token       |
| expires_at  | TIMESTAMP |                            |
| revoked_at  | TIMESTAMP | Nullable                   |
| created_at  | TIMESTAMP |                            |

### 5.3 Project

| Column      | Type         | Notes                          |
|-------------|--------------|--------------------------------|
| id          | UUID (PK)    |                                |
| name        | VARCHAR(100) | Required                       |
| key         | VARCHAR(10)  | Unique, uppercase, e.g. "PRJ"  |
| description | TEXT         | Nullable                       |
| is_archived | BOOLEAN      | Default false                  |
| created_by  | UUID (FK)    | → User                         |
| created_at  | TIMESTAMP    |                                |
| updated_at  | TIMESTAMP    |                                |

### 5.4 ProjectMember

| Column       | Type      | Notes                                      |
|--------------|-----------|--------------------------------------------|
| id           | UUID (PK) |                                            |
| project_id   | UUID (FK) | → Project                                  |
| user_id      | UUID (FK) | → User                                     |
| project_role | ENUM      | project_manager, developer                 |
| joined_at    | TIMESTAMP |                                            |
| UNIQUE       |           | (project_id, user_id)                      |

### 5.5 Epic

| Column      | Type         | Notes                                         |
|-------------|--------------|-----------------------------------------------|
| id          | UUID (PK)    |                                               |
| project_id  | UUID (FK)    | → Project                                     |
| title       | VARCHAR(255) | Required                                      |
| description | TEXT         | Nullable                                      |
| status      | ENUM         | backlog, in_progress, done                    |
| start_date  | DATE         | Nullable                                      |
| end_date    | DATE         | Nullable                                      |
| created_by  | UUID (FK)    | → User                                        |
| created_at  | TIMESTAMP    |                                               |
| updated_at  | TIMESTAMP    |                                               |

### 5.6 Issue

Single table for Story, Task, and Bug (discriminated by `type`).

| Column         | Type         | Notes                                           |
|----------------|--------------|-------------------------------------------------|
| id             | UUID (PK)    |                                                 |
| project_id     | UUID (FK)    | → Project                                       |
| epic_id        | UUID (FK)    | → Epic; nullable; only for Story type           |
| parent_id      | UUID (FK)    | → Issue (self-ref); nullable; for Task/Bug only |
| sprint_id      | UUID (FK)    | → Sprint; nullable                              |
| type           | ENUM         | story, task, bug                                |
| title          | VARCHAR(255) | Required                                        |
| description    | TEXT         | Nullable                                        |
| status         | ENUM         | backlog, todo, in_progress, review, done        |
| priority       | ENUM         | lowest, low, medium, high, highest              |
| story_points   | INTEGER      | Nullable; 0–100                                 |
| assignee_id    | UUID (FK)    | → User; nullable                                |
| reporter_id    | UUID (FK)    | → User                                          |
| backlog_rank   | INTEGER      | Used for ordering in backlog                    |
| created_at     | TIMESTAMP    |                                                 |
| updated_at     | TIMESTAMP    |                                                 |

### 5.7 Sprint

| Column      | Type         | Notes                                      |
|-------------|--------------|--------------------------------------------|
| id          | UUID (PK)    |                                            |
| project_id  | UUID (FK)    | → Project                                  |
| name        | VARCHAR(100) | Required                                   |
| goal        | TEXT         | Nullable                                   |
| status      | ENUM         | planned, active, completed                 |
| start_date  | DATE         | Nullable until sprint is started           |
| end_date    | DATE         | Nullable until sprint is started           |
| created_by  | UUID (FK)    | → User                                     |
| started_at  | TIMESTAMP    | Nullable                                   |
| completed_at| TIMESTAMP    | Nullable                                   |
| created_at  | TIMESTAMP    |                                            |
| updated_at  | TIMESTAMP    |                                            |

### 5.8 Comment

| Column     | Type      | Notes                  |
|------------|-----------|------------------------|
| id         | UUID (PK) |                        |
| issue_id   | UUID (FK) | → Issue                |
| author_id  | UUID (FK) | → User                 |
| body       | TEXT      | Required               |
| is_edited  | BOOLEAN   | Default false          |
| created_at | TIMESTAMP |                        |
| updated_at | TIMESTAMP |                        |

### 5.9 IssueStatusHistory *(audit log)*

| Column      | Type      | Notes              |
|-------------|-----------|--------------------|
| id          | UUID (PK) |                    |
| issue_id    | UUID (FK) | → Issue            |
| changed_by  | UUID (FK) | → User             |
| from_status | ENUM      |                    |
| to_status   | ENUM      |                    |
| changed_at  | TIMESTAMP |                    |

---

## 6. API Endpoints

Base path: `/api/v1`

### Auth

| Method | Path                        | Description                    | Auth |
|--------|-----------------------------|--------------------------------|------|
| POST   | /auth/register              | Register new user              | None |
| POST   | /auth/login                 | Login, receive tokens          | None |
| POST   | /auth/refresh               | Refresh access token           | None |
| POST   | /auth/logout                | Revoke refresh token           | ✅   |
| GET    | /auth/me                    | Get current user profile       | ✅   |
| PATCH  | /auth/me/password           | Change own password            | ✅   |

### Users (Admin)

| Method | Path                        | Description                    | Auth  |
|--------|-----------------------------|--------------------------------|-------|
| GET    | /users                      | List all users                 | Admin |
| GET    | /users/:userId              | Get user by ID                 | Admin |
| PATCH  | /users/:userId/role         | Update system role             | Admin |
| DELETE | /users/:userId              | Deactivate user                | Admin |
| PATCH  | /users/:userId/restore      | Restore deactivated user       | Admin |

### Projects

| Method | Path                                      | Description                    | Auth       |
|--------|-------------------------------------------|--------------------------------|------------|
| POST   | /projects                                 | Create project                 | Admin      |
| GET    | /projects                                 | List accessible projects       | Any        |
| GET    | /projects/:projectId                      | Get project details            | Member     |
| PATCH  | /projects/:projectId                      | Update project                 | Admin      |
| DELETE | /projects/:projectId/archive              | Archive project                | Admin      |
| PATCH  | /projects/:projectId/restore              | Restore archived project       | Admin      |
| GET    | /projects/:projectId/members             | List members                   | Member     |
| POST   | /projects/:projectId/members             | Add member                     | Admin/PM   |
| PATCH  | /projects/:projectId/members/:userId     | Update member role             | Admin/PM   |
| DELETE | /projects/:projectId/members/:userId     | Remove member                  | Admin/PM   |

### Epics

| Method | Path                                      | Description                    | Auth     |
|--------|-------------------------------------------|--------------------------------|----------|
| POST   | /projects/:projectId/epics               | Create epic                    | Admin/PM |
| GET    | /projects/:projectId/epics               | List epics                     | Member   |
| GET    | /projects/:projectId/epics/:epicId       | Get epic details               | Member   |
| PATCH  | /projects/:projectId/epics/:epicId       | Update epic                    | Admin/PM |
| DELETE | /projects/:projectId/epics/:epicId       | Delete epic                    | Admin/PM |

### Issues (Stories, Tasks, Bugs)

| Method | Path                                            | Description                       | Auth          |
|--------|-------------------------------------------------|-----------------------------------|---------------|
| POST   | /projects/:projectId/issues                    | Create issue                      | Member        |
| GET    | /projects/:projectId/issues                    | List issues (filters supported)   | Member        |
| GET    | /projects/:projectId/issues/:issueId           | Get issue details                 | Member        |
| PATCH  | /projects/:projectId/issues/:issueId           | Update issue                      | Admin/PM/Dev* |
| DELETE | /projects/:projectId/issues/:issueId           | Delete issue                      | Admin/PM      |
| PATCH  | /projects/:projectId/issues/:issueId/status    | Change issue status               | Admin/PM/Dev* |
| PATCH  | /projects/:projectId/issues/:issueId/assign    | Assign or unassign issue          | Admin/PM      |
| GET    | /projects/:projectId/issues/:issueId/history   | Get status change history         | Member        |

*Developer can only update/change status on issues assigned to them.

**Query filters for GET /issues:**
- `type`: story | task | bug
- `status`: backlog | todo | in_progress | review | done
- `priority`: lowest | low | medium | high | highest
- `assigneeId`: UUID
- `epicId`: UUID
- `sprintId`: UUID | "backlog" (no sprint assigned)
- `page`, `limit`: pagination

### Sprints

| Method | Path                                               | Description                    | Auth     |
|--------|----------------------------------------------------|--------------------------------|----------|
| POST   | /projects/:projectId/sprints                      | Create sprint                  | Admin/PM |
| GET    | /projects/:projectId/sprints                      | List sprints                   | Member   |
| GET    | /projects/:projectId/sprints/:sprintId            | Get sprint + issues            | Member   |
| PATCH  | /projects/:projectId/sprints/:sprintId            | Update sprint details          | Admin/PM |
| DELETE | /projects/:projectId/sprints/:sprintId            | Delete sprint                  | Admin/PM |
| POST   | /projects/:projectId/sprints/:sprintId/start      | Start sprint                   | Admin/PM |
| POST   | /projects/:projectId/sprints/:sprintId/complete   | Complete sprint                | Admin/PM |
| POST   | /projects/:projectId/sprints/:sprintId/issues     | Add issues to sprint           | Admin/PM |
| DELETE | /projects/:projectId/sprints/:sprintId/issues     | Remove issues from sprint      | Admin/PM |

### Backlog

| Method | Path                                      | Description                    | Auth     |
|--------|-------------------------------------------|--------------------------------|----------|
| GET    | /projects/:projectId/backlog             | List backlog issues (ordered)  | Member   |
| PATCH  | /projects/:projectId/backlog/reorder     | Reorder backlog items          | Admin/PM |
| PATCH  | /projects/:projectId/backlog/move-to-sprint | Move issues to sprint       | Admin/PM |

### Comments

| Method | Path                                                              | Description          | Auth          |
|--------|-------------------------------------------------------------------|----------------------|---------------|
| POST   | /projects/:projectId/issues/:issueId/comments                   | Add comment          | Member        |
| GET    | /projects/:projectId/issues/:issueId/comments                   | List comments        | Member        |
| PATCH  | /projects/:projectId/issues/:issueId/comments/:commentId        | Update comment       | Author        |
| DELETE | /projects/:projectId/issues/:issueId/comments/:commentId        | Delete comment       | Author/PM/Admin|

---

## 7. Validation Rules

### User / Auth

- `email`: valid format, max 255 chars, unique in system.
- `password`: min 8 chars, at least one uppercase letter, one digit.
- `name`: required, 2–100 chars, no leading/trailing whitespace.
- `system_role`: must be one of `admin`, `project_manager`, `developer`.
- Cannot delete/deactivate the last Admin in the system.
- Cannot change own role.

### Project

- `name`: required, 2–100 chars.
- `key`: required, 2–10 chars, uppercase letters and digits only (regex: `^[A-Z0-9]{2,10}$`), unique across system.
- `description`: optional, max 1000 chars.
- Cannot update the key after the project has issues.
- Cannot add duplicate member (same user_id + project_id).
- Assignee must be an active member of the project.

### Epic

- `title`: required, 3–255 chars.
- `end_date` must be after `start_date` if both are provided.
- `status`: must be one of `backlog`, `in_progress`, `done`.
- Cannot delete an epic that has linked stories.

### Issue

- `title`: required, 3–255 chars.
- `type`: required; must be `story`, `task`, or `bug`.
- `priority`: required; default `medium`.
- `status`: default `backlog`.
- `story_points`: integer, 0–100, nullable.
- `parent_id`: only valid for `task` and `bug` types; must reference a `story` in the same project.
- `epic_id`: only valid for `story` type; must reference an epic in the same project.
- `assignee_id`: must be an active project member.
- Cannot set `epic_id` on a `task` or `bug`.
- Cannot set `parent_id` on a `story`.

### Status Transitions

Allowed transitions only (no arbitrary jumps):

```
backlog     → todo
todo        → in_progress
in_progress → review
in_progress → todo          (back)
review      → in_progress   (back)
review      → done
done        → in_progress   (reopen)
```

Admin and PM can make any transition. Developers can only transition issues assigned to them.

### Sprint

- `name`: required, 3–100 chars.
- `start_date` and `end_date` required when starting a sprint.
- `end_date` must be after `start_date`.
- Only **one active sprint** per project at a time.
- Cannot start a sprint if another is already active in the same project.
- Cannot delete an active sprint.
- Cannot delete a sprint that contains issues.
- When completing a sprint, all `done` issues stay in the sprint (for history). Unfinished issues are moved to backlog.

### Backlog

- `backlog_rank` must be a positive integer.
- Reorder request must provide a contiguous set of ranks without gaps.
- Issues in an active sprint cannot be in the backlog simultaneously.

### Comment

- `body`: required, 1–5000 chars.
- Only the author can edit their own comment.
- Only author, PM, or Admin can delete a comment.

---

## 8. Edge Cases

### Authentication & Users

- Login with a deactivated account → `403 Forbidden` with a clear message.
- Expired refresh token → `401 Unauthorized`.
- Refresh token reuse after logout → `401 Unauthorized` (token blacklisted).
- Attempting to deactivate the only Admin → `409 Conflict`.

### Projects

- Adding a user to a project they are already a member of → `409 Conflict`.
- Removing a user who is an assignee on open issues → issues become unassigned automatically.
- Archiving a project with an active sprint → require completing/cancelling the sprint first, or auto-complete it.
- A user is deactivated while they are a project member → they remain in member list but are flagged inactive; their issues become unassigned.

### Epics

- Deleting an epic with linked stories → `409 Conflict` (must unlink stories first).
- Setting `end_date` before `start_date` → `422 Unprocessable Entity`.

### Issues

- Creating a `task` or `bug` with `parent_id` pointing to a non-`story` issue → `422`.
- Creating a `story` with `epic_id` pointing to an epic in a different project → `422`.
- Moving an issue to a sprint that is `completed` → `409 Conflict`.
- Assigning an issue to a user who is not a project member → `422`.
- Attempting a disallowed status transition → `422` with a message listing valid next states.
- Developer attempting to change status of an unassigned issue → `403 Forbidden`.

### Sprints

- Starting a sprint when another sprint is already active in the same project → `409 Conflict`.
- Completing a sprint where all issues are still in `backlog` / `todo` → allowed; all moved to backlog.
- Adding an issue that is already in another active sprint → `409 Conflict`.
- Deleting a planned sprint that has issues already assigned to it → `409 Conflict`.
- Sprint `end_date` in the past when starting → warn but allow (for retroactive data entry).

### Backlog

- Reordering backlog with gaps in rank values → normalize ranks sequentially on write.
- Requesting backlog of an archived project → `410 Gone` or `404`.

### Comments

- Editing a comment on a deleted (soft-deleted) issue → `404 Not Found`.
- Concurrent edits to the same comment → last-write-wins (optimistic approach for simplicity).

---

## 9. Business Rules Summary

1. **Hierarchy**: Epic → Story → Task/Bug. Issues must respect this hierarchy (no circular refs).
2. **Project isolation**: All resources (epics, issues, sprints) are scoped to a single project. Cross-project references are not allowed.
3. **Single active sprint**: Only one sprint per project can be in `active` status at any time.
4. **Sprint completion**: Completing a sprint moves all non-`done` issues back to the project backlog with no sprint assignment.
5. **Soft deletes**: Users are deactivated, not hard-deleted. Projects are archived, not hard-deleted. Issues and comments can be hard-deleted by Admin/PM.
6. **Status audit log**: Every status change on an issue is recorded in `IssueStatusHistory` with the actor and timestamp.
7. **Backlog is a queue**: Issues without a `sprint_id` are considered to be in the backlog, ordered by `backlog_rank`.
8. **Role precedence**: System Admin role supersedes any project role. Admin always has full access across all projects.
9. **Reporter immutability**: The `reporter_id` of an issue is set at creation time and cannot be changed.
10. **Project key immutability**: The project `key` cannot be changed once issues exist under it (used for issue identifiers).
