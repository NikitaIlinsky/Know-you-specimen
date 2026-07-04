# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — Build frontend (Vue.js / Vite)
# ---------------------------------------------------------------------------
FROM node:22-slim AS frontend-builder

WORKDIR /frontend

# Cache dependencies separately
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 — Backend (Python + FastAPI)
# ---------------------------------------------------------------------------
# python:3.14-slim may not be available as stable yet.
# Swap to python:3.14-slim once it is released.
FROM python:3.13-slim

# ---- System dependencies (OpenCV) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ---- Install uv ----
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# ---- Dependencies (cached layer) ----
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Application code ----
COPY src/ ./src/

# ---- Frontend static files (from stage 1) ----
COPY --from=frontend-builder /frontend/dist/ ./frontend/dist/

# ---- Runtime directories (match .env defaults) ----
RUN mkdir -p /app/input_images /app/output

# ---- Security: non-root user ----
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Declare runtime data paths as volumes so Docker knows these
# contain persistent data that should survive container restarts.
VOLUME ["/app/input_images", "/app/output"]

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "know_your_specimen.server:app", "--host", "0.0.0.0", "--port", "8000"]
