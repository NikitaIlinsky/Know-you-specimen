# syntax=docker/dockerfile:1

# ---- Base image ----
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

# ---- Security: non-root user ----
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.know_your_specimen.server:app", "--host", "0.0.0.0", "--port", "8000"]
