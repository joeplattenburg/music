FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra app --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev --no-cache --extra app

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "music.app:app", "--workers", "2"]