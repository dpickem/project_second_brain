.PHONY: up down build test clean logs help setup db-shell neo4j-shell redis-cli backend-shell frontend-shell

# Default target
help:
	@echo "Second Brain - Personal Knowledge Management System"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "  Development:"
	@echo "    up              - Start all services with hot reload"
	@echo "    up-d            - Start all services detached"
	@echo "    down            - Stop all services"
	@echo "    build           - Build all Docker images"
	@echo "    clean           - Stop services and remove volumes"
	@echo "    logs            - View logs from all services"
	@echo ""
	@echo "  Testing:"
	@echo "    test            - Run all tests"
	@echo "    test-backend    - Run backend tests only"
	@echo "    test-frontend   - Run frontend tests only"
	@echo "    test-e2e        - Run end-to-end tests"
	@echo ""
	@echo "  Database:"
	@echo "    db-shell        - Open PostgreSQL shell"
	@echo "    neo4j-shell     - Open Neo4j Cypher shell"
	@echo "    redis-cli       - Open Redis CLI"
	@echo "    db-migrate      - Run database migrations"
	@echo ""
	@echo "  Shells:"
	@echo "    backend-shell   - Open shell in backend container"
	@echo "    frontend-shell  - Open shell in frontend container"
	@echo "    celery-shell    - Open shell in Celery worker container"
	@echo ""
	@echo "  Pipelines:"
	@echo "    ingest-article  - Ingest article from URL (url=<URL>)"
	@echo "    ingest-pdf      - Ingest PDF file (file=<PATH>)"
	@echo "    process-pending - Process all pending content"
	@echo ""
	@echo "  Utilities:"
	@echo "    setup           - Interactive project setup"
	@echo "    setup-vault     - Setup Obsidian vault structure"
	@echo "    lint            - Run linters on backend and frontend"
	@echo "    format          - Format code in backend and frontend"

# =============================================================================
# Development
# =============================================================================

# Start development environment
up:
	docker compose up --build

# Start detached
up-d:
	docker compose up --build -d

# Stop services
down:
	docker compose down

# Build only
build:
	docker compose build

# Clean up (removes volumes)
clean:
	docker compose down -v
	docker system prune -f

# View logs
logs:
	docker compose logs -f

# View specific service logs
logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-celery:
	docker compose logs -f celery-worker

logs-neo4j:
	docker compose logs -f neo4j

# =============================================================================
# Testing
# =============================================================================

# Common volume mounts for backend tests (backend code + scripts for integration tests)
BACKEND_TEST_VOLUMES := -v ./backend:/app -v ./scripts:/scripts

# Allow integration tests to run against dev database (local development only)
# Set ALLOW_PROD_DB_TESTS=0 to enforce separate test database
BACKEND_TEST_ENV := -e ALLOW_PROD_DB_TESTS=1

# Run all tests
test:
	@echo "Running backend tests..."
	docker compose run --rm $(BACKEND_TEST_VOLUMES) $(BACKEND_TEST_ENV) backend pytest -v
	@echo "Running frontend tests..."
	docker compose run --rm frontend npm test

# Run backend tests only
test-backend:
	docker compose run --rm $(BACKEND_TEST_VOLUMES) $(BACKEND_TEST_ENV) backend pytest -v

# Run backend unit tests only (fast, no external dependencies)
test-unit:
	docker compose run --rm $(BACKEND_TEST_VOLUMES) backend pytest tests/unit -v

# Run backend integration tests only (requires running services)
test-integration:
	docker compose run --rm $(BACKEND_TEST_VOLUMES) $(BACKEND_TEST_ENV) backend pytest tests/integration -v

# Run frontend tests only
test-frontend:
	docker compose run --rm frontend npm test

# Run end-to-end tests
test-e2e:
	docker compose run --rm frontend npm run test:e2e

# Run tests with coverage
test-coverage:
	docker compose run --rm $(BACKEND_TEST_VOLUMES) $(BACKEND_TEST_ENV) backend pytest -v --cov=app --cov-report=html

# Update OpenAPI snapshot (run after intentional API changes)
snapshot:
	docker compose run --rm $(BACKEND_TEST_VOLUMES) -e PYTHONPATH=/app backend python scripts/update_openapi_snapshot.py

# =============================================================================
# Database
# =============================================================================

# PostgreSQL shell (loads credentials from .env)
db-shell:
	@source .env && docker compose exec postgres psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"

# Neo4j Cypher shell
neo4j-shell:
	@source .env && docker compose exec neo4j cypher-shell -u neo4j -p "$$NEO4J_PASSWORD"

# Redis CLI
redis-cli:
	docker compose exec redis redis-cli

# Run database migrations
db-migrate:
	docker compose exec backend alembic upgrade head

# Create new migration
db-migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# Show migration status
db-current:
	docker compose exec backend alembic current

# Rollback one migration
db-downgrade:
	docker compose exec backend alembic downgrade -1

# =============================================================================
# Shells
# =============================================================================

# Backend shell
backend-shell:
	docker compose exec backend /bin/bash

# Frontend shell
frontend-shell:
	docker compose exec frontend /bin/sh

# Celery worker shell
celery-shell:
	docker compose exec celery-worker /bin/bash

# =============================================================================
# Pipelines
# =============================================================================

# Ingest article from URL
ingest-article:
ifndef url
	$(error url is required. Usage: make ingest-article url=https://example.com/article)
endif
	docker compose exec backend python -m scripts.pipelines.run_pipeline article "$(url)"

# Ingest PDF file
ingest-pdf:
ifndef file
	$(error file is required. Usage: make ingest-pdf file=/path/to/file.pdf)
endif
	docker compose exec backend python -m scripts.pipelines.run_pipeline pdf "$(file)"

# Ingest book photos
ingest-book:
ifndef file
	$(error file is required. Usage: make ingest-book file=/path/to/photo.jpg)
endif
	docker compose exec backend python -m scripts.pipelines.run_pipeline book "$(file)"

# Process all pending content
process-pending:
	docker compose exec backend python -m scripts.run_processing process-pending

# =============================================================================
# Setup & Utilities
# =============================================================================

# Interactive setup
setup:
	python scripts/setup_project.py

# Non-interactive setup with defaults
setup-quick:
	python scripts/setup_project.py --non-interactive

# Setup Obsidian vault structure
setup-vault:
	python scripts/setup/setup_vault.py

# Validate vault structure
validate-vault:
	python scripts/setup/validate_vault.py

# Create .env from example
env:
	cp .env.example .env
	@echo "Created .env from .env.example"
	@echo "Please edit .env with your API keys and configuration"

# =============================================================================
# Code Quality
# =============================================================================

# Lint backend
lint-backend:
	docker compose run --rm backend ruff check .

# Lint frontend
lint-frontend:
	docker compose run --rm frontend npm run lint

# Lint all
lint: lint-backend lint-frontend

# Format backend
format-backend:
	docker compose run --rm backend ruff format .

# Format frontend
format-frontend:
	docker compose run --rm frontend npm run format

# Format all
format: format-backend format-frontend

# =============================================================================
# Shortcuts
# =============================================================================

# Restart backend (useful during development)
restart-backend:
	docker compose restart backend

# Restart celery worker
restart-celery:
	docker compose restart celery-worker

# Quick status check
status:
	docker compose ps

# Health check all services
health:
	@echo "Checking service health..."
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
