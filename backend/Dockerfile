# syntax=docker/dockerfile:1.7

# Builder stage: install uv, resolve the locked dep set, and compile the package.
FROM python:3.12-slim-bookworm AS builder

ENV UV_VERSION=0.11.14 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

ADD --chmod=755 https://astral.sh/uv/${UV_VERSION}/install.sh /uv-installer.sh
RUN /uv-installer.sh && mv /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Runtime stage: copy venv + source, drop to non-root, expose API port.
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN useradd --create-home --uid 1000 krelix

WORKDIR /app
COPY --from=builder --chown=krelix:krelix /app /app

USER krelix
EXPOSE 8000

CMD ["krelix-api"]
