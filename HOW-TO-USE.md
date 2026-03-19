# HOW TO USE — Jira Full-Stack (Backend + Frontend)

This guide covers everything from first-time setup to day-to-day usage. Read it top to bottom
on a fresh machine. On an existing machine, jump to the section you need.

---

## Table of Contents

1. [Prerequisites Checklist](#1-prerequisites-checklist)
2. [Start the Full Stack](#2-start-the-full-stack)
3. [Verify Everything Is Running](#3-verify-everything-is-running)
4. [Using the App](#4-using-the-app)
5. [Run CI / CD Pipelines](#5-run-ci--cd-pipelines)
6. [Stop / Restart Services](#6-stop--restart-services)
7. [Troubleshooting](#7-troubleshooting)
8. [Quick Reference](#8-quick-reference)

---

## 1. Prerequisites Checklist

Run through this once. If everything is already installed and configured, skip to Section 2.

### Required Software

| Software | How to Check | Install If Missing |
|---|---|---|
| Docker Desktop | `docker version` | See CICD.md §A0 |
| Node.js 20+ | `node --version` | https://nodejs.org (LTS) |
| pnpm 10 | `pnpm --version` | `npm install -g pnpm` |
| pm2 | `pm2 --version` | `npm install -g pm2` |
| WAMP (Apache) | WAMP tray icon is green | https://wampserver.com |

### Required Configuration

| Item | How to Check | How to Fix |
|---|---|---|
| Docker Desktop is running | Whale icon in system tray is green | Open Docker Desktop |
| Apache proxy modules enabled | `httpd.exe -t` says `Syntax OK` | See CICD.md §A4 |
| `jira-api.conf` is in `D:\wamp64\alias\` | `ls D:\wamp64\alias\jira-api.conf` | Already there — see CICD.md §A4 |
| Backend `.env` exists | `ls D:\wamp64\www\jira-backend\.env` | `cp .env.example .env` |
| Frontend `.env.local` exists | `ls D:\wamp64\www\jira-frontend\.env.local` | `echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local` |

### GitHub Secrets (for CD pipeline)

These are needed only to trigger CD from GitHub. Not needed to run locally.

| Repo | Secret | Value |
|---|---|---|
| jira-backend | `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| jira-backend | `DB_PASSWORD` | Any strong password, e.g. `jira_secure_2026` |
| jira-frontend | `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` |

---

## 2. Start the Full Stack

Do these steps **every time** you want the full site running.

### Step 1 — Start Docker Desktop

Make sure the whale icon in the Windows system tray shows green ("Engine running"). If not,
open Docker Desktop and wait for it to start.

### Step 2 — Start the Backend (FastAPI + PostgreSQL + Redis)

Open a terminal in the backend folder:

```bash
cd D:\wamp64\www\jira-backend
docker compose up -d
```

This starts three containers:
- `app` — FastAPI on port 8000
- `db` — PostgreSQL 16 on port 5432
- `redis` — Redis 7 on port 6379

Wait ~10–15 seconds for all containers to become healthy. Check with:

```bash
docker compose ps
```

All three should show `healthy` or `running`. Example:

```
NAME              STATUS
jira-backend-app-1    Up 15 seconds (healthy)
jira-backend-db-1     Up 15 seconds (healthy)
jira-backend-redis-1  Up 15 seconds (healthy)
```

**First time only** — run migrations after the containers start:

```bash
docker compose exec app alembic upgrade head
```

### Step 3 — Start the Frontend (Next.js via pm2)

Open a terminal:

```bash
cd D:\wamp64\www\jira-frontend
pm2 start pnpm --name jira-frontend -- start
pm2 save
```

If `jira-frontend` is already in pm2 (from a previous run), just restart it:

```bash
pm2 restart jira-frontend
```

Check that it started:

```bash
pm2 list
```

The `jira-frontend` row should show `online` status.

### Step 4 — Start WAMP / Apache

- Click the WAMP tray icon and ensure it is **green** (all services running).
- If WAMP is not running, left-click the tray icon → **Start All Services**.
- Apache will pick up `jira-api.conf` automatically and proxy traffic to both services.

---

## 3. Verify Everything Is Running

Run these checks in order. Each one should succeed before moving to the next.

### 3.1 Docker containers

```bash
docker compose -f D:/wamp64/www/jira-backend/docker-compose.yml ps
```

Expected: `app`, `db`, `redis` all healthy.

### 3.2 Backend direct health check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok"}
```

### 3.3 Backend via Apache proxy

```bash
curl http://localhost/health
```

Expected: same `{"status":"ok"}`. If this fails but 8000 works, check Apache.

### 3.4 Frontend direct

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

Expected: `200`

### 3.5 Frontend via Apache proxy

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost
```

Expected: `200`

### 3.6 API authentication endpoint

```bash
curl -s http://localhost:8000/api/v1/auth/me
```

Expected: `401` (no token) — this proves FastAPI is routing correctly.

### 3.7 Swagger UI (optional)

Open in a browser: http://localhost:8000/docs

You should see the interactive API documentation.

### 3.8 pm2 status

```bash
pm2 list
```

Expected: `jira-frontend` shows `online`.

---

## 4. Using the App

Open a browser and go to: **http://localhost**

### 4.1 Register an Account

1. You will be redirected to `http://localhost/auth/login`
2. Click **Register** or go to `http://localhost/auth/register`
3. Fill in your name, email, and password
4. Submit — you will be logged in automatically

> **Note:** The first user registered does **not** automatically become an Admin. Admin role
> must be assigned via the API. See §4.7 for how to create an Admin using the API directly.

### 4.2 Log In

1. Go to `http://localhost/auth/login`
2. Enter your email and password
3. Click **Log In** — you will be taken to the dashboard

### 4.3 Dashboard

URL: `http://localhost/dashboard`

Shows your assigned issues, recent activity, and project overview.

### 4.4 Create a Project

1. Go to `http://localhost/projects`
2. Click **New Project** (requires Project Manager or Admin role)
3. Enter a project name and description
4. Click **Create**

### 4.5 Manage Project Members

1. Open a project → **Settings** (`/projects/{id}/settings`)
2. Add members by email
3. Assign roles: **Project Manager** or **Developer**

### 4.6 Create and Manage Issues

Navigate to a project, then:

| Page | URL | What You Can Do |
|---|---|---|
| Issues | `/projects/{id}/issues/{issueId}` | View, edit, assign, change status |
| Backlog | `/projects/{id}/backlog` | Order and prioritize backlog items |
| Board | `/projects/{id}/board` | Drag-and-drop sprint board |
| Epics | `/projects/{id}/epics` | Manage epics (groups of stories) |

**Issue types:** Story, Task, Bug
**Issue statuses:** `todo` → `in_progress` → `in_review` → `done`

### 4.7 Admin Operations (via Swagger UI)

Some operations require Admin role and must be done through the API directly:

1. Open http://localhost:8000/docs
2. Click **Authorize** → enter your JWT token (obtained from `/api/v1/auth/login`)
3. Use `PATCH /api/v1/users/{user_id}` to set `system_role: "admin"`

Admin can:
- Manage all users
- Access all projects
- Archive/delete projects

---

## 5. Run CI / CD Pipelines

### CI (Continuous Integration) — Runs Automatically

CI runs on **GitHub cloud** every time you push any branch. No local setup needed.

**What CI checks:**

| Project | Checks |
|---|---|
| Backend | black format, isort imports, ruff lint, pytest unit tests |
| Frontend | prettier format, eslint, TypeScript type-check, next build |

**Watch CI run:**
- Go to GitHub → your repo → **Actions** tab
- Click the running workflow to see live logs

**If CI fails:**
1. Click the failed step to see the error
2. Fix it locally (see Section 8 for quick-fix commands)
3. Push again — CI re-runs automatically

### CD (Continuous Deployment) — Runs on Push to Main

CD runs on **your local machine** (self-hosted runner) when code is pushed to `main`.

**Requirements before CD works:**
1. GitHub Actions self-hosted runner must be installed and running (see CICD.md §A3)
2. Docker Desktop must be running
3. GitHub Secrets must be configured (see Section 1)

**What CD does:**

| Project | What Happens |
|---|---|
| Backend | Builds Docker image → runs `alembic upgrade head` → restarts containers |
| Frontend | Runs `pnpm install` + `pnpm build` → `pm2 restart jira-frontend` |

**To trigger CD manually** (without pushing code):
- GitHub → your repo → Actions → **CD** → **Run workflow** → **Run workflow**

**Watch CD run:**
- GitHub → Actions tab → click the CD workflow run
- On your machine: `docker compose logs app --tail=50` (backend) or `pm2 logs jira-frontend` (frontend)

---

## 6. Stop / Restart Services

### Stop everything

```bash
# Backend containers
cd D:\wamp64\www\jira-backend
docker compose down

# Frontend (stop but keep in pm2)
pm2 stop jira-frontend

# Apache — via WAMP tray → Stop All Services
```

### Restart everything

```bash
# Backend
cd D:\wamp64\www\jira-backend
docker compose up -d

# Frontend
pm2 restart jira-frontend

# Apache — via WAMP tray → Restart All Services
```

### Restart only the backend app (not the database)

```bash
cd D:\wamp64\www\jira-backend
docker compose restart app
```

### View live logs

```bash
# Backend app logs
docker compose logs app -f

# Database logs
docker compose logs db -f

# Frontend logs
pm2 logs jira-frontend
```

---

## 7. Troubleshooting

### Backend doesn't start

**Symptom:** `docker compose ps` shows `app` as exited or unhealthy.

```bash
# See why it failed
docker compose logs app --tail=50
```

Common causes:
- `.env` file missing → `cp .env.example .env`
- `SECRET_KEY` not set → add a real key to `.env`
- Port 8000 already in use → `netstat -an | findstr 8000` → kill the process

---

### Database won't start

**Symptom:** `db` container is not healthy.

```bash
docker compose logs db --tail=20
```

Common causes:
- Port 5432 already in use (another PostgreSQL running, e.g. WAMP's PostgreSQL)
- Corrupt data volume → `docker compose down -v` (WARNING: deletes all DB data)

---

### CORS errors in the browser

**Symptom:** Browser console shows `CORS error` when the frontend calls the API.

**Cause:** The `.env` file is missing `http://localhost` in `CORS_ORIGINS`.

**Fix:**

```bash
# Open D:\wamp64\www\jira-backend\.env and ensure:
CORS_ORIGINS=["http://localhost:3000","http://localhost","http://localhost:80"]
```

Then restart the backend:

```bash
docker compose restart app
```

---

### Frontend shows blank page or 500 error

**Symptom:** `http://localhost` loads but shows errors.

```bash
pm2 logs jira-frontend --lines 50
```

Common causes:
- `.env.local` missing or has wrong API URL → recreate:
  ```bash
  echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > D:\wamp64\www\jira-frontend\.env.local
  pm2 restart jira-frontend
  ```
- pm2 process crashed → `pm2 restart jira-frontend`
- Build not done → `cd D:\wamp64\www\jira-frontend && pnpm build && pm2 restart jira-frontend`

---

### Apache shows 503 Bad Gateway

**Symptom:** `http://localhost` returns 503.

Apache can reach its ports but the service behind it isn't running.

```bash
# Is backend up?
curl http://localhost:8000/health

# Is frontend up?
curl http://localhost:3000

# Fix: start whatever is down
docker compose up -d        # backend
pm2 restart jira-frontend   # frontend
```

---

### Apache shows 500 error (proxy module not found)

**Symptom:** Apache error log says `proxy_module not loaded`.

- WAMP tray → Apache → Apache modules → enable `proxy_module` and `proxy_http_module`
- Restart Apache

---

### "pm2 not found" after Windows reboot

pm2 might not be in PATH if the terminal was opened before Node was installed or if
pm2-windows-service is not installed.

```bash
npm install -g pm2
pm2 resurrect    # restore last saved process list
```

Or, if you haven't set up auto-start yet:

```bash
npm install -g pm2-windows-service
pm2-service-install
pm2 start pnpm --name jira-frontend -- start
pm2 save
```

---

### Migrations fail during CD

**Symptom:** CD log shows `alembic upgrade head` error.

```bash
# Run migrations manually
cd D:\wamp64\www\jira-backend
docker compose exec app alembic upgrade head

# See migration history
docker compose exec app alembic history
```

---

### Secret key is the placeholder value

**Symptom:** App starts but JWTs may be weak.

The `.env` file ships with:
```
SECRET_KEY=change-me-to-a-very-long-random-string-at-least-32-chars
```

Generate a real one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace the value in `.env`, then restart:

```bash
docker compose restart app
```

---

## 8. Quick Reference

### Start Full Stack (Daily)

```bash
# 1. Make sure Docker Desktop is running (whale icon = green)

# 2. Backend
cd D:\wamp64\www\jira-backend
docker compose up -d

# 3. Frontend
pm2 restart jira-frontend   # or: pm2 start pnpm --name jira-frontend -- start

# 4. WAMP tray → green (Apache running)

# 5. Open browser: http://localhost
```

### Service URLs

| URL | What It Is |
|---|---|
| http://localhost | Full app (via Apache — use this) |
| http://localhost:3000 | Frontend direct (Next.js) |
| http://localhost:8000/health | Backend health check |
| http://localhost:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:8000/redoc | ReDoc API docs |
| http://localhost:5432 | PostgreSQL (connect with `psql` or pgAdmin) |

### Credentials (default local dev)

| Service | User | Password |
|---|---|---|
| PostgreSQL | `jira` | `jira` |
| Redis | _(no auth)_ | — |
| App admin | _(create via API)_ | — |

### Backend Commands

```bash
# Start containers
docker compose up -d

# Stop containers
docker compose down

# View logs
docker compose logs app -f

# Run migrations
docker compose exec app alembic upgrade head

# Generate new migration
docker compose exec app alembic revision --autogenerate -m "describe the change"

# Run unit tests locally
pip install -e ".[dev]"
pytest tests/unit/ -v

# Format + lint locally
python -m black app/ tests/ main.py
python -m isort app/ tests/ main.py
python -m ruff check app/ tests/ main.py --fix
```

### Frontend Commands

```bash
# Run dev server (hot reload, for development)
cd D:\wamp64\www\jira-frontend
pnpm dev

# Build production bundle
pnpm build

# pm2 commands
pm2 list                    # see all processes
pm2 restart jira-frontend   # restart after a build
pm2 stop jira-frontend      # stop
pm2 logs jira-frontend      # live logs

# Format + lint locally
pnpm format
pnpm lint:fix
pnpm type-check
```

### Git Workflow (to trigger CI/CD)

```bash
# Feature branch → triggers CI only
git checkout -b feature/my-change
# ... make changes ...
git add .
git commit -m "feat: my change"
git push origin feature/my-change
# GitHub Actions CI runs → check Actions tab

# Merge to main → triggers CI + CD
git checkout main
git merge feature/my-change
git push origin main
# CI + CD both run → check Actions tab
# CD deploys automatically to your local machine
```
