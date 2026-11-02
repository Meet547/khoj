UV ?= uv

.PHONY: help install frontend-dev backend-dev frontend-check backend-check check build test-e2e

help:
	@echo "install         Install both applications from their lockfiles"
	@echo "frontend-dev    Start the Next.js demo on port 3000"
	@echo "backend-dev     Start FastAPI on port 8000 (services/migrations required)"
	@echo "check           Run frontend and backend checks; database tests need test URLs"
	@echo "frontend-check  Type generation, TypeScript, ESLint and frontend unit tests"
	@echo "backend-check   Ruff, formatting, mypy and backend tests"
	@echo "build           Build the frontend for production"
	@echo "test-e2e        Run frontend browser tests (Chromium required)"

install:
	npm --prefix frontend ci
	cd khoj-backend && $(UV) sync --extra dev --frozen

frontend-dev:
	npm --prefix frontend run dev

backend-dev:
	cd khoj-backend && $(UV) run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers

frontend-check:
	npm --prefix frontend run typecheck
	npm --prefix frontend run lint
	npm --prefix frontend test

backend-check:
	$(MAKE) -C khoj-backend check UV="$(UV)"

check: frontend-check backend-check

build:
	npm --prefix frontend run build

test-e2e:
	npm --prefix frontend run test:e2e
