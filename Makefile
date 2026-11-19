.DEFAULT_GOAL := help

MBAKE ?= uvx mbake@1.5.0

.PHONY: help setup serve dev-backend dev-frontend format format-check lint test test-backend test-frontend build check

help:
	@printf '%s\n' \
		'  make setup          Install locked backend and frontend dependencies' \
		'  make serve          Build and serve the website and API on port 8000' \
		'  make dev-backend    Start FastAPI on port 8000' \
		'  make dev-frontend   Start Vite on port 5173 in a second terminal' \
		'  make format         Format the source and Makefile' \
		'  make format-check   Check formatting' \
		'  make lint           Lint the code and validate the Makefile' \
		'  make test           Run both test suites' \
		'  make test-backend   Run pytest with an in-memory SQLite database' \
		'  make test-frontend  Run Vitest' \
		'  make build          Type-check and build the frontend' \
		'  make check          Run format, lint, test, and build checks'

setup:
	cd backend && uv sync --locked
	npm --prefix frontend ci

serve: build
	cd backend && SCENTFOLIO_SERVE_UI=1 uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000

dev-backend:
	./backend/run.sh

dev-frontend:
	npm --prefix frontend run dev -- --strictPort

format:
	$(MBAKE) format Makefile
	cd backend && uv run --locked ruff format .
	npm --prefix frontend run format

format-check:
	$(MBAKE) format --check Makefile
	cd backend && uv run --locked ruff format --check .
	npm --prefix frontend run format:check

lint:
	$(MBAKE) validate Makefile
	cd backend && uv run --locked ruff check .
	npm --prefix frontend run lint

test: test-backend test-frontend

test-backend:
	cd backend && SCENTFOLIO_DB_URL=sqlite:///:memory: PYTHON_DOTENV_DISABLED=1 uv run --locked pytest

test-frontend:
	npm --prefix frontend test

build:
	npm --prefix frontend run build

check: format-check lint test build
