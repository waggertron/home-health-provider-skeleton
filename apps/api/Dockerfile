# API image: Django + Celery share this image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# uv installed via the official image.
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /usr/local/bin/

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (better layer cache).
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/.python-version ./
RUN uv sync --frozen --extra dev --no-install-project

# Copy the app.
COPY apps/api/ .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
