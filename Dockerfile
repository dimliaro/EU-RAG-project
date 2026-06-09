FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Cache dependency installation separately from source changes
COPY day_09/pyproject.toml day_09/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY day_09/ .
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "src.day_09.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
