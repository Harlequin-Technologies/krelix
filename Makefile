.PHONY: help dev dev-services dev-backend dev-worker dev-frontend dev-down lint typecheck test build

COMPOSE_DEV := docker compose -f docker-compose.dev.yml

help:
	@echo "Targets:"
	@echo "  make dev           — start services and print next-step instructions"
	@echo "  make dev-services  — start only Postgres + Redis"
	@echo "  make dev-backend   — run krelix-api locally with reload"
	@echo "  make dev-worker    — run krelix-worker locally"
	@echo "  make dev-frontend  — run Vite dev server"
	@echo "  make dev-down      — stop services"
	@echo "  make lint          — run linters across backend + frontend + agent"
	@echo "  make typecheck     — run type checkers"
	@echo "  make test          — run all test suites"
	@echo "  make build         — build Docker images"

dev: dev-services
	@echo ""
	@echo "Services up. Run these in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-worker"
	@echo "  make dev-frontend"

dev-services:
	$(COMPOSE_DEV) up -d
	@echo "Waiting for postgres + redis to be healthy..."
	@for i in $$(seq 1 60); do \
		pg=$$(docker inspect -f '{{.State.Health.Status}}' krelix-dev-postgres 2>/dev/null || echo starting); \
		rd=$$(docker inspect -f '{{.State.Health.Status}}' krelix-dev-redis 2>/dev/null || echo starting); \
		if [ "$$pg" = "healthy" ] && [ "$$rd" = "healthy" ]; then \
			echo "Services ready."; \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "Timed out waiting for services to become healthy."; \
	$(COMPOSE_DEV) ps; \
	exit 1

dev-backend:
	cd backend && uv run uvicorn krelix.main:app --reload --host 127.0.0.1 --port 8000

dev-worker:
	cd backend && uv run arq krelix.worker.WorkerSettings

dev-frontend:
	cd frontend && pnpm dev

dev-down:
	$(COMPOSE_DEV) down

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint && pnpm format:check
	cd agent && uv run ruff check . && uv run ruff format --check .

typecheck:
	cd backend && uv run mypy src
	cd frontend && pnpm typecheck
	cd agent && uv run mypy src

test:
	cd backend && uv run pytest
	cd frontend && pnpm test
	cd agent && uv run pytest

build:
	docker build -t krelix-control:dev backend/
	docker build -t krelix-agent:dev agent/
