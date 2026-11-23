# ---------------------------------------------------------
# Stage 1: Builder
# ---------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv from official binary image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency definition files first for optimal Docker layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies without root project
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and build project
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------
# Stage 2: Runtime
# ---------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source, migrations and configuration
COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini
COPY pyproject.toml /app/pyproject.toml

# Set environment variables for runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Automatically run database migrations before starting the ASGI server
CMD ["sh", "-c", "alembic upgrade head && uvicorn taskhub.main:app --host 0.0.0.0 --port 8000"]
