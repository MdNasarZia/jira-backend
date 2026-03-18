#!/usr/bin/env bash
# deploy.sh — runs on the self-hosted runner after docker build succeeds.
# Called from the project root by cd.yml.
#
# Required env var: DB_PASSWORD (injected by the CD workflow)
# Reads: docker-compose.yml, docker-compose.prod.yml, .env (written by cd.yml step)

set -euo pipefail

# Resolve project root regardless of where the script is called from
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Deploy started at $(date) ==="
echo "Working directory: $PROJECT_ROOT"

# ── Step 1: Start infrastructure (db + redis) ────────────────────────────────
echo "--- Starting infrastructure services (db, redis) ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db redis

# ── Step 2: Wait for PostgreSQL to be ready ───────────────────────────────────
echo "--- Waiting for database to be ready ---"
for i in $(seq 1 20); do
    if docker compose exec -T db pg_isready -U jira -d jira_db >/dev/null 2>&1; then
        echo "Database is ready."
        break
    fi
    echo "Attempt $i/20: database not ready, waiting 3s..."
    sleep 3
    if [ "$i" = "20" ]; then
        echo "ERROR: Database did not become ready after 60 seconds."
        docker compose logs db --tail=20
        exit 1
    fi
done

# ── Step 3: Run Alembic migrations ───────────────────────────────────────────
echo "--- Running database migrations ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm \
    -e DATABASE_URL="postgresql+asyncpg://jira:${DB_PASSWORD:-jira}@db:5432/jira_db" \
    app alembic upgrade head

# ── Step 4: Deploy the app container ─────────────────────────────────────────
echo "--- Deploying application ---"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps app

# ── Step 5: Clean up dangling images ─────────────────────────────────────────
echo "--- Cleaning up old images ---"
docker image prune -f

echo "=== Deploy complete at $(date) ==="
