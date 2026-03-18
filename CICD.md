# CI/CD Pipeline Documentation
# Jira Project — Backend + Frontend

**Author:** Development Team
**Date:** 2026-03-18
**Projects:**
- Backend: `D:\wamp64\www\jira-backend` (FastAPI + Python + Docker)
- Frontend: `D:\wamp64\www\jira-frontend` (Next.js + TypeScript + pnpm)

---

## Table of Contents

1. [What is CI/CD?](#1-what-is-cicd)
2. [Our Overall Architecture](#2-our-overall-architecture)
3. [Tools We Use and Why](#3-tools-we-use-and-why)
4. [Backend CI/CD — What Was Done](#4-backend-cicd--what-was-done)
5. [Frontend CI/CD — What Was Done](#5-frontend-cicd--what-was-done)
6. [Apache Reverse Proxy — Serving Both Projects](#6-apache-reverse-proxy--serving-both-projects)
7. [How It All Fits Together](#7-how-it-all-fits-together)
8. [Manual Setup Checklist](#8-manual-setup-checklist)
9. [Day-to-Day Workflow](#9-day-to-day-workflow)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What is CI/CD?

CI/CD stands for **Continuous Integration / Continuous Deployment**. These are two separate but connected concepts:

### Continuous Integration (CI)

Every time a developer pushes code to GitHub, a set of automated checks runs automatically:

- **Code formatting** — Is the code style consistent? (e.g., no mixed tabs/spaces, consistent quote style)
- **Linting** — Does the code follow best practices? (e.g., no unused variables, no bad patterns)
- **Tests** — Does the code work correctly? (run automated tests)
- **Build** — Does the code compile/build without errors?

The goal: **catch problems early, before they reach production.**

Without CI, developers manually check everything before merging. This is slow and error-prone. With CI, the machine checks automatically on every push.

### Continuous Deployment (CD)

When code is merged to the `main` branch, the system automatically:

1. **Builds** the new version
2. **Runs database migrations** (backend)
3. **Restarts the server** with the new version

The goal: **deploy new code automatically, without manual steps.**

Without CD, someone has to SSH into the server, pull the code, restart processes, run migrations — manually every time. With CD, a `git push` to `main` triggers all of that automatically.

### The Flow

```
Developer writes code
        │
        ▼
git push (any branch)
        │
        ▼
CI runs automatically (GitHub cloud)
├── ✅ Format check passes?
├── ✅ Lint passes?
├── ✅ Tests pass?
└── ✅ Build succeeds?
        │
        ▼ (only if merging to main)
CD runs automatically (your local machine)
├── Build Docker image / Next.js bundle
├── Run database migrations
├── Restart the server
└── Health check
```

---

## 2. Our Overall Architecture

### Request Flow (What Happens When Someone Visits the Site)

```
Browser (User)
      │
      ▼
http://localhost:80  (Apache — the "front door")
      │
      ├─── /api/v1/*  ──────────────► FastAPI (port 8000, Docker)
      ├─── /docs       ──────────────► FastAPI Swagger UI
      ├─── /health     ──────────────► FastAPI health check
      │
      └─── everything else ──────────► Next.js (port 3000, pm2)
                                          │
                                          └── calls backend API
                                              via http://localhost:8000/api/v1
```

### What Runs Where

| Service | Technology | Port | How It Runs |
|---|---|---|---|
| **Frontend** | Next.js 16 | 3000 | pm2 process manager (Node.js) |
| **Backend API** | FastAPI | 8000 | Docker container |
| **Database** | PostgreSQL 16 | 5432 | Docker container |
| **Cache** | Redis 7 | 6379 | Docker container |
| **Web Server** | Apache (WAMP) | 80 | WAMP service |

### Why Apache in Front?

Apache acts as a **reverse proxy** — it's the only port exposed to users (port 80). It routes traffic to the correct service behind the scenes. Benefits:

- Users visit `http://localhost` (no port number)
- Apache can add SSL/HTTPS later
- Single entry point for both frontend and backend
- Apache can handle static file caching, compression, etc.

---

## 3. Tools We Use and Why

### Backend Tools

| Tool | Purpose | Why This Tool |
|---|---|---|
| **black** | Python code formatter | The Python standard formatter, enforces consistent style automatically |
| **isort** | Sort Python imports | Keeps import sections clean and consistent |
| **ruff** | Python linter | Fast, modern linter that catches bugs, bad patterns, and security issues |
| **pytest** | Python test runner | The standard Python test framework |
| **GitHub Actions** | CI/CD platform | Free for open source, integrated with GitHub, no extra setup |
| **Docker** | Containerization | Consistent environment, easy to start/stop services |
| **Docker Compose** | Multi-container management | Manages backend + database + Redis together |
| **Alembic** | Database migrations | Tracks schema changes, applies them automatically on deploy |

### Frontend Tools

| Tool | Purpose | Why This Tool |
|---|---|---|
| **Prettier** | Code formatter | The JavaScript/TypeScript standard, formats HTML/CSS/JS/TS |
| **ESLint** | JavaScript/TypeScript linter | Catches bugs, enforces React/Next.js best practices |
| **TypeScript** | Type checking (`tsc`) | Catches type errors before they reach production |
| **pnpm** | Package manager | Faster than npm, uses less disk space, strict dependency resolution |
| **pm2** | Node.js process manager | Keeps Next.js running as a background service, restarts on crash |

---

## 4. Backend CI/CD — What Was Done

### 4.1 Code Quality Tools (Added to `pyproject.toml`)

**File:** `D:\wamp64\www\jira-backend\pyproject.toml`

Three tools were added to the `[project.optional-dependencies] dev` list:

```toml
"black>=24.0.0",   # Code formatter
"isort>=5.13.0",   # Import sorter
"ruff>=0.4.0",     # Linter
```

Configuration sections were added:

```toml
[tool.black]
line-length = 100        # Lines up to 100 chars (matches the project's convention)
target-version = ["py312"]

[tool.isort]
profile = "black"        # isort works in "black-compatible mode"
line_length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP"]   # Rule sets to check
ignore = [
    "E501",   # black already handles line length
    "B008",   # FastAPI's Depends() pattern triggers this — safe to ignore
    "F821",   # SQLAlchemy uses string annotations ("Issue") — false positives
    "UP042",  # StrEnum breaks SQLAlchemy Enum column type — keep str+Enum
    "UP046",  # Generic[T] syntax — SQLAlchemy compatibility
]
```

**What each ruff rule set catches:**
- `E`, `W` — PEP 8 style errors and warnings
- `F` — Pyflakes (undefined names, unused imports)
- `I` — Import sorting violations
- `B` — Bugbear (common bugs and design issues)
- `C4` — Better comprehension patterns
- `UP` — Pyupgrade (modernize Python syntax)

### 4.2 All Existing Code Was Formatted

When we added the tools, we ran them on all existing code:

```bash
# Format all Python files
python -m black app/ tests/ main.py

# Sort all imports
python -m isort app/ tests/ main.py

# Auto-fix lint issues
python -m ruff check app/ tests/ main.py --fix
```

This means the very first CI run will pass cleanly — no formatting failures from old code.

### 4.3 CI Workflow — `.github/workflows/ci.yml`

**File:** `D:\wamp64\www\jira-backend\.github\workflows\ci.yml`

**Triggers:** Every push to any branch, every pull request.
**Runs on:** GitHub-hosted Ubuntu machines (free, no setup needed).

**Steps in order:**

```
1. Checkout the code from GitHub
2. Set up Python 3.12 (with pip cache for speed)
3. Install all dev dependencies: pip install -e ".[dev]"
4. black --check   → Fails if any file needs reformatting
5. isort --check   → Fails if any imports are unsorted
6. ruff check      → Fails if any lint rules are violated
7. pytest tests/unit/ → Runs unit tests (no database needed)
8. Upload coverage report as an artifact
```

**Important:** Unit tests do NOT need a database. They mock all repository calls. That's why this runs on a GitHub cloud machine with no PostgreSQL installed.

**Integration tests** (which need a real database) are NOT in this CI pipeline. They would need a Docker service — that's a future enhancement.

### 4.4 CD Workflow — `.github/workflows/cd.yml`

**File:** `D:\wamp64\www\jira-backend\.github\workflows\cd.yml`

**Triggers:** Only when code is pushed to the `main` branch.
**Runs on:** `self-hosted` — your local Windows machine (must have the GitHub Actions runner installed).

**Steps in order:**

```
1. Checkout the latest code
2. Verify Docker Desktop is running
3. Write .env file (using secrets stored in GitHub, never in code)
4. docker compose build --no-cache app → Build fresh Docker image
5. Run scripts/deploy.sh:
   a. Start PostgreSQL + Redis containers
   b. Wait for PostgreSQL to be ready (polls pg_isready)
   c. Run: alembic upgrade head (apply any new migrations)
   d. docker compose up -d --no-deps app (restart only the app)
   e. docker image prune (clean up old images)
6. Health check: poll http://localhost:8000/health for 60 seconds
```

**Why `--no-deps` in step 5d?** We only want to restart the `app` container, not PostgreSQL or Redis. `--no-deps` tells Docker Compose not to restart containers that `app` depends on.

**Why `--no-cache` in step 4?** Ensures we build from scratch, not from cached layers that might be stale.

### 4.5 Deploy Script — `scripts/deploy.sh`

**File:** `D:\wamp64\www\jira-backend\scripts\deploy.sh`

This is a bash script that contains the actual deployment logic. It's separated from `cd.yml` so you can also run it manually when needed:

```bash
bash scripts/deploy.sh
```

The script uses `set -euo pipefail` — this means:
- `-e` — exit immediately if any command fails
- `-u` — error on undefined variables
- `-o pipefail` — catch errors inside pipes

### 4.6 Files Created/Modified Summary

```
jira-backend/
├── pyproject.toml                 ← MODIFIED: added black, isort, ruff + their configs
├── .gitattributes                 ← CREATED: enforces LF line endings for .sh files
├── .github/
│   └── workflows/
│       ├── ci.yml                 ← CREATED: CI pipeline (format, lint, unit tests)
│       └── cd.yml                 ← CREATED: CD pipeline (build, migrate, deploy)
└── scripts/
    └── deploy.sh                  ← CREATED: deployment script
```

---

## 5. Frontend CI/CD — What Was Done

### 5.1 The Frontend Stack

The frontend is a **Next.js 16** application with:
- **React 19** for the UI
- **TypeScript** for type safety
- **Tailwind CSS 4** for styling
- **shadcn/ui** components (Radix UI primitives)
- **pnpm** as the package manager

It was NOT configured with:
- Any code formatter (no Prettier)
- Any linter config (ESLint script existed but no config file)
- Any CI/CD
- No Docker — runs directly as a Node.js process

### 5.2 Code Quality Tools Added

**Prettier** — JavaScript/TypeScript formatter:

```json
// .prettierrc
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

Why `prettier-plugin-tailwindcss`? It automatically sorts Tailwind CSS class names in the correct order (not just alphabetically, but in the order Tailwind recommends for performance and readability).

**ESLint** — JavaScript/TypeScript linter:

```json
// .eslintrc.json
{
  "extends": [
    "next/core-web-vitals",
    "next/typescript",
    "prettier"
  ]
}
```

- `next/core-web-vitals` — Next.js rules + Core Web Vitals performance rules
- `next/typescript` — TypeScript-specific Next.js rules
- `prettier` — Disables any ESLint rules that conflict with Prettier formatting

### 5.3 Scripts Added to `package.json`

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint . --max-warnings 0",
  "lint:fix": "eslint . --fix",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "type-check": "tsc --noEmit"
}
```

**What each script does:**
- `lint` — Check code quality, fail if any warnings (stricter than default)
- `lint:fix` — Auto-fix fixable lint issues
- `format` — Format all files with Prettier (run locally to fix formatting)
- `format:check` — Check formatting without changing files (used in CI)
- `type-check` — Run TypeScript compiler to find type errors, without generating output files

### 5.4 CI Workflow — `.github/workflows/ci.yml`

**File:** `D:\wamp64\www\jira-frontend\.github\workflows\ci.yml`

**Triggers:** Every push to any branch, every pull request.
**Runs on:** GitHub-hosted Ubuntu machines.

**Steps in order:**

```
1. Checkout code
2. Set up Node.js 20 (LTS)
3. Install pnpm
4. Install dependencies (pnpm install --frozen-lockfile)
5. prettier --check   → Fails if any file needs formatting
6. eslint .           → Fails if any lint rules are violated
7. tsc --noEmit       → Fails if TypeScript type errors exist
8. next build         → Fails if the app cannot compile
```

**Why `--frozen-lockfile`?** In CI, we want to ensure exactly the same versions as in the `pnpm-lock.yaml` file. Without this flag, pnpm might update versions, causing unexpected behavior.

**Note on TypeScript errors:** The project currently has `ignoreBuildErrors: true` in `next.config.mjs`. This was set by the original developer to skip TS errors during `next build`. The `tsc --noEmit` step in CI is separate — it WILL fail on type errors. This forces the team to fix TypeScript errors over time, while not breaking the production build immediately.

### 5.5 CD Workflow — `.github/workflows/cd.yml`

**File:** `D:\wamp64\www\jira-frontend\.github\workflows\cd.yml`

**Triggers:** Push to `main` branch only.
**Runs on:** `self-hosted` — your local Windows machine.

**Steps in order:**

```
1. Checkout latest code
2. Set up Node.js 20
3. Install pnpm
4. Install dependencies
5. Create .env.local (from GitHub secret NEXT_PUBLIC_API_URL)
6. pnpm build → Build the Next.js production bundle
7. pm2 restart jira-frontend (or start if first time)
8. Health check: poll http://localhost:3000 for 60 seconds
```

### 5.6 How Next.js Is Served (pm2)

Next.js is a **Node.js** application. Unlike a static website, it needs a running server process. We use **pm2** (Process Manager 2) to:

- Keep Next.js running in the background
- Automatically restart it if it crashes
- Start it when Windows boots

```
pm2 process: "jira-frontend"
  └── runs: pnpm start
      └── runs: next start
          └── Node.js HTTP server on port 3000
```

pm2 commands you'll use:
```bash
pm2 list                    # See all running processes
pm2 logs jira-frontend      # View live logs
pm2 restart jira-frontend   # Restart the frontend
pm2 stop jira-frontend      # Stop the frontend
pm2 save                    # Save current process list for auto-start
```

### 5.7 Files Created/Modified Summary

```
jira-frontend/
├── package.json                   ← MODIFIED: added new scripts, ESLint/Prettier devDeps
├── .eslintrc.json                 ← CREATED: ESLint configuration
├── .prettierrc                    ← CREATED: Prettier configuration
├── .prettierignore                ← CREATED: Files Prettier should skip
├── .gitattributes                 ← CREATED: LF line endings for .sh files
├── .github/
│   └── workflows/
│       ├── ci.yml                 ← CREATED: CI pipeline (format, lint, type-check, build)
│       └── cd.yml                 ← CREATED: CD pipeline (build, pm2 restart)
└── scripts/
    └── deploy.sh                  ← CREATED: deployment script (install, build, restart)
```

---

## 6. Apache Reverse Proxy — Serving Both Projects

### Why Apache?

You already have WAMP installed, which includes Apache. Apache runs on port 80 (the default HTTP port). Without it, users would have to remember port numbers:
- `http://localhost:3000` for the frontend
- `http://localhost:8000` for the backend

With Apache as a reverse proxy, everything is on `http://localhost`:
- Frontend: `http://localhost/`
- Backend API: `http://localhost:8000/` (direct) or via Apache
- Backend Swagger: `http://localhost:8000/docs` (direct)

### The Proxy Configuration

**File:** `D:\wamp64\alias\jira-api.conf`

```apache
# Backend routes are served from port 8000
ProxyPass /api/  http://127.0.0.1:8000/api/   ← all /api/ requests go to FastAPI
ProxyPass /docs  http://127.0.0.1:8000/docs   ← Swagger UI
ProxyPass /health http://127.0.0.1:8000/health

# Frontend catch-all — everything else goes to Next.js on port 3000
ProxyPass / http://127.0.0.1:3000/            ← must be LAST (catch-all)
```

**Order matters!** Apache processes `ProxyPass` rules in order. The catch-all `/` must come AFTER all the specific backend paths.

### How the Frontend Calls the Backend

The frontend's API URL is configured in `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

This means the browser's JavaScript code calls the backend **directly on port 8000**, bypassing Apache. This is intentional and correct — it avoids a round-trip through Apache for API calls.

```
Browser page load:  Browser → Apache:80 → Next.js:3000
API calls:          Browser → FastAPI:8000 (direct, no Apache)
```

This is fine for local development. In production on a real server, you would change `NEXT_PUBLIC_API_URL` to the real domain.

---

## 7. How It All Fits Together

### Complete System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Windows Machine                      │
│                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────┐  │
│  │  WAMP Apache │    │         Docker Desktop            │  │
│  │   Port: 80   │    │  ┌────────────┐ ┌────────────┐   │  │
│  │              │    │  │  FastAPI   │ │ PostgreSQL │   │  │
│  │  Proxy /api/ ├────┼─►│  Port:8000 │ │ Port:5432  │   │  │
│  │  to :8000    │    │  └────────────┘ └────────────┘   │  │
│  │              │    │  ┌────────────┐                   │  │
│  │  Proxy /     ├──┐ │  │   Redis    │                   │  │
│  │  to :3000    │  │ │  │ Port:6379  │                   │  │
│  └──────────────┘  │ │  └────────────┘                   │  │
│                    │ └──────────────────────────────────┘  │
│  ┌─────────────────┤                                       │
│  │    pm2 (Node)   │                                       │
│  │  Next.js:3000 ◄─┘                                       │
│  └─────────────────┘                                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         GitHub Actions Self-Hosted Runner             │  │
│  │         Runs as a Windows service (C:\actions-runner) │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Two GitHub Repositories

Each project has its own GitHub repo with its own CI/CD:

**jira-backend repo:**
```
Push to any branch → CI (GitHub cloud):
  black check → isort check → ruff lint → pytest unit tests

Push to main → CD (your machine):
  docker build → alembic migrate → docker restart
```

**jira-frontend repo:**
```
Push to any branch → CI (GitHub cloud):
  prettier check → eslint → tsc type-check → next build

Push to main → CD (your machine):
  pnpm install → next build → pm2 restart
```

---

## 8. Manual Setup Checklist

This section lists everything you need to do **one time** to make the CI/CD work.

### A. Backend: One-Time Setup

#### A1. Push Backend to GitHub

If not already done:
```bash
cd D:\wamp64\www\jira-backend
git init
git add .
git commit -m "feat: initial backend with CI/CD"
git remote add origin https://github.com/YOUR_USERNAME/jira-backend.git
git push -u origin main
```

#### A2. Add GitHub Secrets (Backend Repo)

Go to: **GitHub → jira-backend repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | How to Generate | What It's For |
|---|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` | JWT signing key |
| `DB_PASSWORD` | Choose any password (e.g., `jira_secure_2026`) | PostgreSQL password |

#### A3. Set Up GitHub Actions Self-Hosted Runner

This runner is shared by BOTH projects if you create only one. Or you can create two separate runners.

1. GitHub → jira-backend repo → Settings → Actions → Runners → **New self-hosted runner**
2. Select: **Windows**, **x64**
3. Follow the exact commands GitHub shows. They include a one-time token.
4. Run these in **PowerShell as Administrator**:
   ```powershell
   mkdir C:\actions-runner
   cd C:\actions-runner
   # (paste the download + configure commands from GitHub)

   # Install as Windows service so it survives reboots:
   .\svc.cmd install
   .\svc.cmd start
   ```
5. **Fix Docker permissions** (runner needs to access Docker Desktop):
   - Open `services.msc` → find **GitHub Actions Runner** → Properties → **Log On** tab
   - Change from "Local System" to **your Windows user account** (enter your username and password)
   - Click OK → Restart the service
   - Also run (as Admin): `net localgroup docker-users YOUR_WINDOWS_USERNAME /add`
   - **Reboot** for group membership to take effect

#### A4. Enable Apache Proxy Modules (WAMP)

1. Click WAMP tray icon → **Apache** → **Apache modules**
2. Enable: ✅ `proxy_module` and ✅ `proxy_http_module`
3. Open this file in a text editor (run as Administrator):
   `D:\wamp64\bin\apache\apache2.4.62.1\conf\httpd.conf`
4. Find the line `#LoadModule headers_module modules/mod_headers.so`
5. Remove the `#` to uncomment it
6. Save the file
7. Restart Apache via WAMP tray → **Restart All Services**
8. Verify: open a terminal and run:
   ```cmd
   D:\wamp64\bin\apache\apache2.4.62.1\bin\httpd.exe -t
   ```
   Should say: `Syntax OK`

---

### B. Frontend: One-Time Setup

#### B1. Push Frontend to GitHub

```bash
cd D:\wamp64\www\jira-frontend
git init
git add .
git commit -m "feat: initial frontend with CI/CD"
git remote add origin https://github.com/YOUR_USERNAME/jira-frontend.git
git push -u origin main
```

#### B2. Add GitHub Secrets (Frontend Repo)

Go to: **GitHub → jira-frontend repo → Settings → Secrets and variables → Actions**

| Secret Name | Value | What It's For |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Backend API URL for the frontend |

#### B3. Set Up GitHub Actions Self-Hosted Runner (Frontend Repo)

You need to register the runner in the frontend repo too. Options:

**Option A: Create a second runner** (recommended — separate processes):
- GitHub → jira-frontend repo → Settings → Actions → Runners → New self-hosted runner
- Run the setup in a different directory, e.g., `C:\actions-runner-frontend`

**Option B: Use one runner for both repos** (simpler):
- Create an **organization** on GitHub and add both repos to it
- Register the runner at the organization level (Settings → Actions → Runners)
- Both repos share the same runner

#### B4. Install pm2 Globally (for Next.js process management)

Open PowerShell and run:
```powershell
npm install -g pm2
```

Verify: `pm2 --version` should print a version number.

For pm2 to survive Windows reboots, install the startup service:
```powershell
npm install -g pm2-windows-service
pm2-service-install
```

This installs pm2 as a Windows service. Now any process you add to pm2 with `pm2 save` will auto-start on boot.

#### B5. First Frontend Deployment (Manual, One Time)

Before the CD pipeline takes over, do the first deployment manually:

```bash
cd D:\wamp64\www\jira-frontend

# Create the env file (same as what the CD pipeline would create)
echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local

# Install dependencies
pnpm install

# Build the production bundle
pnpm build

# Start with pm2
pm2 start pnpm --name jira-frontend -- start

# Save the pm2 process list (so it auto-starts on reboot)
pm2 save
```

After this, the CD pipeline will handle all future deploys.

#### B6. Update Apache Config for Frontend

The `jira-api.conf` file needs to be updated to also proxy the frontend. Replace the contents of `D:\wamp64\alias\jira-api.conf` with the version that includes both backend and frontend routing.

Restart Apache after the change: WAMP tray → Restart All Services.

---

### C. Verify the Full Setup

Run through these checks in order:

```bash
# 1. Docker containers are running
docker compose ps
# Should show: app, db, redis all "healthy"

# 2. Backend health check (direct)
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# 3. Frontend is running (direct)
curl http://localhost:3000
# Should return: HTML content

# 4. Frontend via Apache
curl http://localhost/
# Should return: HTML content (same as above, through Apache)

# 5. Backend API via direct port
curl http://localhost:8000/api/v1/auth/me
# Should return: 401 (no token) — proving FastAPI is running

# 6. Check pm2 status
pm2 list
# Should show: jira-frontend with status "online"
```

---

## 9. Day-to-Day Workflow

### When You Make a Change

```bash
# 1. Create a feature branch
git checkout -b feature/my-new-feature

# 2. Make your changes
# ... edit files ...

# 3. Run checks locally before pushing (saves time):
#    Backend:
python -m black app/ tests/ main.py
python -m isort app/ tests/ main.py
python -m ruff check app/ tests/ main.py --fix
pytest tests/unit/ -v

#    Frontend:
pnpm format
pnpm lint:fix
pnpm type-check

# 4. Commit and push
git add .
git commit -m "feat(issues): add priority filter to issue list"
git push origin feature/my-new-feature

# 5. Watch CI run:
# GitHub → Actions tab → see your workflow running

# 6. If CI passes, open a Pull Request
# 7. Merge to main → CD automatically deploys
```

### When Something Breaks

**CI fails (red X on GitHub):**
1. Click the failed job
2. Read the error message
3. Fix locally using the same commands CI uses
4. Push again — CI re-runs automatically

**CD fails (deploy fails):**
1. Check GitHub Actions logs for the error
2. On your machine, check Docker logs: `docker compose logs app --tail=50`
3. Check pm2 logs: `pm2 logs jira-frontend`

**App is down after deploy:**
```bash
# Backend
docker compose ps          # Are containers running?
docker compose up -d       # Start if stopped

# Frontend
pm2 list                   # Is it running?
pm2 start pnpm --name jira-frontend -- start   # Start if stopped
```

---

## 10. Troubleshooting

### Common Issues

**"Docker: permission denied"** on the self-hosted runner:
- The runner service must run as your user account, not "Local System"
- Check: `services.msc` → GitHub Actions Runner → Log On tab → This account
- Also run: `net localgroup docker-users YOUR_USERNAME /add` and reboot

**Apache "proxy not found" error (500):**
- Apache can't reach the backend/frontend
- Check: is Docker running? `docker compose ps`
- Check: is pm2 running? `pm2 list`
- Verify ports: `netstat -an | findstr "8000 3000"`

**"pnpm: command not found"** on the runner:
- pnpm needs to be installed on the machine where the runner runs
- The CD workflow installs pnpm automatically via `pnpm/action-setup@v4`
- If that fails, install manually: `npm install -g pnpm`

**Next.js build fails with TypeScript errors:**
- The project has `ignoreBuildErrors: true` in `next.config.mjs` so `next build` won't fail
- But `pnpm type-check` (tsc --noEmit) will surface them
- Fix the TypeScript errors or temporarily remove the `type-check` step from ci.yml

**"black: reformatted X files"** (CI fails on format check):
- Run `python -m black app/ tests/ main.py` locally
- Commit the formatted files
- Push again

**"prettier: X files need formatting"** (CI fails on format check):
- Run `pnpm format` locally (in jira-frontend)
- Commit the formatted files
- Push again

---

## Quick Reference

### Backend Commands
```bash
# Run locally
uvicorn main:app --reload --port 8000

# Run with Docker
docker compose up -d

# Check quality
python -m black --check app/ tests/ main.py
python -m isort --check-only app/ tests/ main.py
python -m ruff check app/ tests/ main.py
pytest tests/unit/ -v

# Format
python -m black app/ tests/ main.py
python -m isort app/ tests/ main.py
python -m ruff check app/ tests/ main.py --fix

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "describe the change"
```

### Frontend Commands
```bash
# Run locally
pnpm dev

# Check quality
pnpm format:check
pnpm lint
pnpm type-check

# Format + fix
pnpm format
pnpm lint:fix

# Build
pnpm build
pnpm start       # starts production server on port 3000

# pm2
pm2 list
pm2 logs jira-frontend
pm2 restart jira-frontend
```

### GitHub Actions Status
```
Backend CI:  https://github.com/YOUR_USERNAME/jira-backend/actions
Frontend CI: https://github.com/YOUR_USERNAME/jira-frontend/actions
```
