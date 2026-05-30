FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/

FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN useradd --create-home appuser

COPY --from=builder /app /app

RUN mkdir -p /app/cache /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uv", "run", "python", "src/main.py"]
