# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed by some compiled wheels (e.g. bcrypt, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the project metadata first so this layer is cached when only
# source code changes (not dependency declarations).
COPY pyproject.toml .

# Create a minimal package stub so setuptools can resolve the project root
# without needing the full source tree during the dependency-install step.
RUN mkdir -p app && touch app/__init__.py

# Install all runtime dependencies into an isolated prefix.
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install libpq runtime library required by asyncpg/psycopg at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so the container does not run as root.
RUN groupadd --system appgroup && useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

# Pull in the pre-built dependency tree from the builder stage.
COPY --from=builder /install /usr/local

# Copy application source (excludes everything in .dockerignore).
COPY . .

# Hand ownership of the working directory to the non-root user.
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
