# Cheat Sheet — Run, Stop, and Access the Jira Project

Quick reference. No explanations — just commands.

---

## START EVERYTHING

### 1. Start Docker Desktop
Make sure the whale icon in the Windows system tray is **green (solid)**.
If not: open Docker Desktop from the Start menu and wait.

### 2. Start the Backend (FastAPI + PostgreSQL + Redis)
```bash
cd D:\wamp64\www\jira-backend
docker compose up -d
```
Check status:
```bash
docker compose ps
```
All three containers should show `Up` or `healthy`:
```
jira-backend-app-1    Up  (port 8000)
jira-backend-db-1     Up  (healthy) (port 5432)
jira-backend-redis-1  Up  (healthy) (port 6379)
```

First time only — run migrations:
```bash
docker compose exec app alembic upgrade head
```

### 3. Start the Frontend (Next.js)
```bash
pm2 restart jira-frontend
```
First time ever (never started before):
```bash
cd D:\wamp64\www\jira-frontend
pm2 start pnpm --name jira-frontend -- start
pm2 save
```

### 4. Start Apache (WAMP)
Click WAMP tray icon → **Start All Services** (icon turns green).

---

## VERIFY EVERYTHING IS RUNNING

```bash
# Backend health
curl http://localhost:8000/health
# Expected: {"status":"ok"}

# Frontend health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200

# Full site via Apache
curl -s -o /dev/null -w "%{http_code}" http://localhost
# Expected: 200

# pm2 status
pm2 list
# jira-frontend should show: online
```

Open in browser: **http://localhost**

---

## STOP EVERYTHING

### Stop the Backend
```bash
cd D:\wamp64\www\jira-backend
docker compose down
```
This stops and removes all three containers (app, db, redis).
Data in PostgreSQL is NOT lost — it's stored in a Docker volume.

### Stop the Frontend
```bash
pm2 stop jira-frontend
```

### Stop Apache
WAMP tray icon → **Stop All Services**

---

## RESTART (without full stop/start)

### Restart only the backend app (not db/redis)
```bash
cd D:\wamp64\www\jira-backend
docker compose restart app
```

### Restart the frontend
```bash
pm2 restart jira-frontend
```

### Restart Apache
WAMP tray → **Restart All Services**

---

## VIEW LOGS

### Backend app logs (live)
```bash
cd D:\wamp64\www\jira-backend
docker compose logs app -f
```
Press `Ctrl+C` to stop watching.

### Backend db logs
```bash
docker compose logs db --tail=30
```

### Frontend logs (live)
```bash
pm2 logs jira-frontend
```
Press `Ctrl+C` to stop watching.

---

## DATABASE ACCESS

### Connection Details (Docker PostgreSQL)

| Field    | Value       |
|----------|-------------|
| Host     | `localhost` |
| Port     | `5432`      |
| Database | `jira_db`   |
| Username | `jira`      |
| Password | `jira`      |

> Make sure Docker containers are running before connecting.
> If another PostgreSQL is running on port 5432, stop it first:
> ```powershell
> Get-Service | Where-Object {$_.DisplayName -like "*postgres*"}
> net stop <service-name>
> ```

### Connect in DBeaver

1. New Connection → PostgreSQL
2. Host: `localhost` | Port: `5432`
3. Database: `jira_db`
4. Username: `jira` | Password: `jira`
5. Test Connection → Finish

### Connect via terminal (inside Docker)
```bash
docker compose exec db psql -U jira -d jira_db
```

Useful psql commands:
```sql
\dt                        -- list all tables
\d users                   -- describe users table
SELECT * FROM users;       -- see all users
SELECT * FROM projects;    -- see all projects
\q                         -- quit
```

### Create Admin User (SQL — run in DBeaver)

First generate a fresh password hash (replace `YourPassword` with what you want):
```bash
docker compose exec app python -c "import bcrypt; h = bcrypt.hashpw(b'YourPassword', bcrypt.gensalt()); print(h.decode())"
```

Then run in DBeaver:
```sql
INSERT INTO users (id, name, email, password_hash, system_role, is_active, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'Admin',
    'admin@admin.com',
    '<paste hash here>',
    'admin',
    true,
    now(),
    now()
);
```

---

## URLS

| URL | What It Is |
|-----|-----------|
| http://localhost | Full app (use this) |
| http://localhost/auth/login | Login page |
| http://localhost/auth/register | Register page |
| http://localhost/dashboard | Dashboard |
| http://localhost/projects | Projects list |
| http://localhost:8000/health | Backend health check |
| http://localhost:8000/docs | Swagger UI (interactive API docs) |
| http://localhost:8000/redoc | ReDoc API docs |

---

## CI/CD

### Watch CI (runs on every push — GitHub cloud)
GitHub → your repo → **Actions** tab → click the running workflow

### Trigger CD manually (deploys to local machine)
GitHub → your repo → **Actions** → **CD** → **Run workflow** → **Run workflow**

### CD runs automatically when you push to main
```bash
git checkout main
git merge feature/my-branch
git push origin main
# CD starts automatically on your machine via the self-hosted runner
```

---

## QUICK FIXES

### App returns 500 / CORS error
```bash
# Add http://localhost to CORS in .env then restart
docker compose restart app
```

### Frontend shows old version after deploy
```bash
cd D:\wamp64\www\jira-frontend
pnpm build
pm2 restart jira-frontend
```

### Database changes not applied
```bash
cd D:\wamp64\www\jira-backend
docker compose exec app alembic upgrade head
```

### Everything is broken — full restart
```bash
# Backend
cd D:\wamp64\www\jira-backend
docker compose down
docker compose up -d

# Frontend
pm2 restart jira-frontend

# Apache: WAMP tray → Restart All Services
```

### Check if port 5432 is conflicted
```powershell
netstat -ano | findstr :5432
tasklist | findstr <PID>
```
If two processes are on 5432, stop the non-Docker one.
