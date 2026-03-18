# Manual Testing Checklist

> Base URL: `http://localhost:8000/api/v1`
> Tool: Swagger UI at `http://localhost:8000/docs` or any REST client (Postman, curl, etc.)
>
> You already have:
> - **Admin** user
> - **Developer A** (Project Manager role on the project)
> - **Developer B** (Developer role on the project)
> - **Project** created
> - **Epic** created inside the project
> - **Story** created inside the project (linked to the epic)
>
> Collect and keep these IDs as you go — you'll need them in later steps.

---

## Step 0 — Login & Collect Tokens

### 0.1 Login as Admin
```
POST /auth/login
{
  "email": "<admin email>",
  "password": "<admin password>"
}
```
- Expected: `200` with `access_token` and `refresh_token`
- Save: `ADMIN_TOKEN = access_token`

### 0.2 Login as Developer A (Project Manager)
```
POST /auth/login
{
  "email": "<dev-a email>",
  "password": "<dev-a password>"
}
```
- Expected: `200`
- Save: `DEV_A_TOKEN = access_token`

### 0.3 Login as Developer B (Developer role)
```
POST /auth/login
{
  "email": "<dev-b email>",
  "password": "<dev-b password>"
}
```
- Expected: `200`
- Save: `DEV_B_TOKEN = access_token`

---

## Step 1 — Confirm Existing Setup

### 1.1 Get Project details
```
GET /projects
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: `200` with your project in the list
- Save: `PROJECT_ID`

### 1.2 Get Epic details
```
GET /projects/{PROJECT_ID}/epics
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: `200` with your epic in the list
- Save: `EPIC_ID`

### 1.3 Confirm the Story exists
```
GET /projects/{PROJECT_ID}/issues?type=story
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: `200` with the story you already created
- Save: `STORY_ID = id of that story`
- Confirm: `epic_id` on the story matches `EPIC_ID`

---

## Step 2 — Issue Hierarchy Explained

```
Epic
 ├── Story  (epic_id = EPIC_ID, parent_id = null)
 │    ├── Task  (parent_id = STORY_ID, epic_id = optional)
 │    └── Bug   (parent_id = STORY_ID, epic_id = optional)
 └── Task    (epic_id = EPIC_ID, parent_id = null)  ← direct task on epic
```

**`epic_id`** — links any issue (story/task/bug) directly to an epic
**`parent_id`** — links a task/bug as a child of a story (must be a valid issue ID in the same project)

---

## Step 3 — Create a Task Directly Under the Epic (No Story parent)

> This is the fix that was applied today. Previously only stories could have `epic_id`.

### 3.1 Happy path — Task linked to Epic (as Project Manager)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Direct epic task",
  "type": "task",
  "priority": "medium",
  "epic_id": "<EPIC_ID>"
}
```
- Expected: `201`
- Confirm response has `type: "task"`, `epic_id = EPIC_ID`, `parent_id: null`
- Save: `DIRECT_EPIC_TASK_ID`

### 3.2 Happy path — Bug linked to Epic
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Direct epic bug",
  "type": "bug",
  "priority": "high",
  "epic_id": "<EPIC_ID>"
}
```
- Expected: `201` with `type: "bug"`, `epic_id = EPIC_ID`

### 3.3 Failure — Epic linked to another Epic (must still fail)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Bad nested epic",
  "type": "epic",
  "priority": "low",
  "epic_id": "<EPIC_ID>"
}
```
- Expected: `422` with `"Epics cannot be linked to other epics"`

---

## Step 4 — Create a Task as Child of a Story (parent_id)

### 4.1 Happy path — Task under Story (as Project Manager)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Story child task",
  "type": "task",
  "priority": "medium",
  "parent_id": "<STORY_ID>"
}
```
- Expected: `201` with `parent_id = STORY_ID`
- Save: `CHILD_TASK_ID`

### 4.2 Happy path — Task under Story AND Epic (both ids set)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Story child task with epic",
  "type": "task",
  "priority": "low",
  "parent_id": "<STORY_ID>",
  "epic_id": "<EPIC_ID>"
}
```
- Expected: `201` with both `parent_id` and `epic_id` set

### 4.3 Failure — Story with a parent_id (stories cannot have parents)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Bad story",
  "type": "story",
  "priority": "medium",
  "parent_id": "<STORY_ID>"
}
```
- Expected: `422` with `"Stories cannot have a parent issue"`

### 4.4 Failure — parent_id pointing to a non-existent issue
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Orphan task",
  "type": "task",
  "priority": "medium",
  "parent_id": "00000000-0000-0000-0000-000000000000"
}
```
- Expected: `404` with `"Parent issue not found"`

---

## Step 5 — Create the Original Failing Payload (should now work)

```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "create claude.md",
  "type": "task",
  "priority": "medium",
  "description": "create a claude.md documentation",
  "epic_id": "<EPIC_ID>",
  "parent_id": "<STORY_ID>",
  "story_points": 5,
  "assignee_id": "<DEV_B_USER_ID>"
}
```
- Expected: `201`
- Confirm: `type: "task"`, `epic_id` set, `parent_id` set, `assignee_id` set

> Note: `story_points` max is 100 — your original payload had `100` which is the ceiling, so that's fine.

---

## Step 6 — Sprint Assignment

> Only do this if you have a sprint created. Skip if not.

### 6.1 Create a Sprint (as Project Manager)
```
POST /projects/{PROJECT_ID}/sprints
Authorization: Bearer <DEV_A_TOKEN>
{
  "name": "Sprint 1",
  "start_date": "2026-03-10",
  "end_date": "2026-03-24"
}
```
- Expected: `201`
- Save: `SPRINT_ID`

### 6.2 Start the Sprint
```
POST /projects/{PROJECT_ID}/sprints/{SPRINT_ID}/start
Authorization: Bearer <DEV_A_TOKEN>
```
- Expected: `200` with `status: "active"`

### 6.3 Create a Task in the Sprint + Epic
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_A_TOKEN>
{
  "title": "Sprint task in epic",
  "type": "task",
  "priority": "medium",
  "epic_id": "<EPIC_ID>",
  "sprint_id": "<SPRINT_ID>",
  "assignee_id": "<DEV_B_USER_ID>"
}
```
- Expected: `201` with `sprint_id` set, `epic_id` set

---

## Step 7 — Authorization Checks

### 7.1 Developer cannot create an issue without being assigned (just creates it)
```
POST /projects/{PROJECT_ID}/issues
Authorization: Bearer <DEV_B_TOKEN>
{
  "title": "Dev B task",
  "type": "task",
  "priority": "low"
}
```
- Expected: `201` (developers can create issues)

### 7.2 Unauthenticated request fails
```
POST /projects/{PROJECT_ID}/issues
(no Authorization header)
{
  "title": "no token task",
  "type": "task",
  "priority": "low"
}
```
- Expected: `401`

### 7.3 Developer can only update their own assigned issue
```
PATCH /projects/{PROJECT_ID}/issues/{CHILD_TASK_ID}
Authorization: Bearer <DEV_B_TOKEN>
{
  "priority": "high"
}
```
- If `DEV_B` is NOT the assignee of `CHILD_TASK_ID` → Expected: `403`
- If `DEV_B` IS the assignee → Expected: `200`

---

## Step 8 — Read Back & Verify

### 8.1 List all tasks in the project
```
GET /projects/{PROJECT_ID}/issues?type=task
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: `200` with all tasks you created above

### 8.2 Filter tasks by epic
```
GET /projects/{PROJECT_ID}/issues?type=task&epic_id=<EPIC_ID>
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: tasks with `epic_id = EPIC_ID`

### 8.3 Get a single issue
```
GET /projects/{PROJECT_ID}/issues/{DIRECT_EPIC_TASK_ID}
Authorization: Bearer <ADMIN_TOKEN>
```
- Expected: `200` with full issue details

---

## Quick ID Reference (fill in as you go)

| Name | ID |
|---|---|
| PROJECT_ID | |
| EPIC_ID | |
| STORY_ID | |
| SPRINT_ID | |
| DIRECT_EPIC_TASK_ID | |
| CHILD_TASK_ID | |
| ADMIN_USER_ID | |
| DEV_A_USER_ID | |
| DEV_B_USER_ID | |
| ADMIN_TOKEN | |
| DEV_A_TOKEN | |
| DEV_B_TOKEN | |
