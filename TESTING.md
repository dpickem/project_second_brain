# Testing Guide - Second Brain

This document provides comprehensive instructions for running tests across the Second Brain project, including backend (Python/FastAPI) and frontend (React/Vite) tests.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Backend Testing](#backend-testing)
  - [Unit Tests](#unit-tests)
  - [Integration Tests](#integration-tests)
  - [Test Coverage](#test-coverage)
- [Frontend Testing](#frontend-testing)
  - [Unit Tests](#frontend-unit-tests)
  - [E2E Tests (Playwright)](#e2e-tests-playwright)
- [Running All Tests](#running-all-tests)
- [Test Configuration](#test-configuration)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Run all tests with a single command
python scripts/run_all_tests.py

# Or run specific test suites
python scripts/run_all_tests.py --backend-unit         # Backend unit tests only
python scripts/run_all_tests.py --backend-integration  # Backend integration tests only
python scripts/run_all_tests.py --frontend             # Frontend unit tests only
python scripts/run_all_tests.py --frontend-e2e         # Frontend e2e tests only (Playwright)
python scripts/run_all_tests.py --frontend --frontend-e2e  # All frontend tests
```

---

## Prerequisites

### Python Dependencies

```bash
# From project root, install backend dependencies
cd backend
pip install -r requirements.txt
```

Key testing packages:
- `pytest>=8.0.0` - Test framework
- `pytest-asyncio>=0.23.4` - Async test support
- `pytest-cov>=4.1.0` - Coverage reporting
- `pytest-mock>=3.12.0` - Mocking utilities

### Node.js Dependencies

```bash
# From project root, install frontend dependencies
cd frontend
npm install
```

### Optional Test Dependencies

Some tests have optional dependencies and will be **automatically skipped** if those dependencies are not available. This allows running a subset of tests without a full environment setup.

| Dependency | Tests Skipped When Missing | Required For |
|------------|---------------------------|--------------|
| `NEO4J_URI` env var | `test_vault_sync.py` (all) | Neo4j knowledge graph sync tests |
| Docker | `TestCodeSandboxIntegration` in `test_code_sandbox.py` | Code sandbox execution tests |
| OpenAPI snapshot | `test_schema_*` in `test_openapi_contract.py` | API contract verification |
| Sample PDF file | PDF tests in `test_pipelines.py` | PDF processing pipeline tests |

**Running tests without optional dependencies:**

```bash
# Run all tests (skipped tests will show as "SKIPPED" not "FAILED")
pytest tests/ -v

# Run only tests that don't require optional dependencies
pytest tests/ -v -m "not integration"

# See which tests would be skipped
pytest tests/ --collect-only -q
```

**Setting up optional dependencies:**

```bash
# Neo4j (for vault sync tests)
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# Docker (for code sandbox tests)
# Ensure Docker daemon is running

# OpenAPI snapshot (for contract tests)
cd backend && make snapshot  # Creates openapi_snapshot.json
```

### Docker Services (for Integration Tests)

Integration tests require PostgreSQL, Redis, and Neo4j. You have two options:

#### Option 1: Standalone Test Database (Recommended)

```bash
# Start a dedicated test database container
docker run -d --name test-postgres \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16-alpine

# Optionally start Redis (if testing Redis-dependent features)
docker run -d --name test-redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Option 2: Docker Compose

```bash
# Start all services
docker-compose up -d postgres redis neo4j

# Wait for services to be healthy
docker-compose ps
```

---

## Backend Testing

Backend tests are located in `backend/tests/` and organized into:
- `unit/` - Tests that don't require external services
- `integration/` - Tests that require running databases/services

### Unit Tests

Unit tests are fast, isolated, and don't require any external services. They use mocks for all dependencies.

```bash
# Navigate to backend directory
cd backend

# Run all unit tests
pytest tests/unit/ -v

# Run with short output
pytest tests/unit/

# Run a specific test file
pytest tests/unit/test_config.py -v

# Run a specific test class
pytest tests/unit/test_config.py::TestSettings -v

# Run a specific test method
pytest tests/unit/test_config.py::TestSettings::test_default_values -v

# Run tests matching a pattern
pytest tests/unit/ -k "config"
```

**Unit Test Categories:**

| Directory | Description |
|-----------|-------------|
| `unit/` | Core service tests (config, models, pipelines) |
| `unit/obsidian/` | Obsidian vault operations (frontmatter, links, sync) |

### Integration Tests

Integration tests verify the system works correctly with real databases and services.

> ⚠️ **Important:** Integration tests use dedicated test credentials (`testuser`/`testpass`/`testdb`) that are separate from your `.env` configuration.

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific integration test
pytest tests/integration/test_database.py -v

# Run with verbose assertions
pytest tests/integration/ -vv
```

**Integration Test Categories:**

| File | Description |
|------|-------------|
| `test_database.py` | PostgreSQL model and ORM tests |
| `test_health.py` | Health endpoint verification |
| `test_vault.py` | Obsidian vault validation |
| `test_pipelines.py` | Content processing pipelines |
| `test_processing.py` | LLM processing workflows |
| `test_learning_api.py` | Learning system endpoints |
| `test_knowledge_api.py` | Knowledge management endpoints |
| `test_vault_api.py` | Vault API endpoints |
| `test_vault_sync.py` | Vault synchronization |
| `test_reconciliation.py` | Data reconciliation |

### Test Coverage

Generate coverage reports to identify untested code:

```bash
# Run with HTML coverage report
pytest tests/ --cov=app --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html

# Coverage for specific module
pytest tests/ --cov=app.services --cov-report=term-missing

# Generate XML coverage for CI
pytest tests/ --cov=app --cov-report=xml

# Coverage with minimum threshold (fails if below)
pytest tests/ --cov=app --cov-fail-under=70
```

---

## Frontend Testing

Frontend tests are split into two categories:
- **Unit Tests**: Fast, isolated tests using Vitest + React Testing Library
- **E2E Tests**: Integration tests using Playwright that test the full application

### Frontend Unit Tests

Unit tests use Vitest with React Testing Library for component, hook, and utility testing.

```bash
cd frontend

# Run all unit tests
npm test

# Run tests in watch mode (development)
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- src/components/common/Button.test.jsx
```

#### Test File Structure

Frontend tests follow the convention:
- Component tests: `ComponentName.test.jsx`
- Hook tests: `useHookName.test.js`
- Utility tests: `utilName.test.js`

```
frontend/src/
├── components/
│   ├── common/
│   │   ├── Button.jsx
│   │   └── Button.test.jsx    # Component test
│   └── ...
├── hooks/
│   ├── useLocalStorage.js
│   └── useLocalStorage.test.js  # Hook test
└── utils/
    ├── animations.js
    └── animations.test.js     # Utility test
```

### E2E Tests (Playwright)

End-to-end tests use Playwright to test the full application in a real browser.

#### Setup

```bash
cd frontend

# Install Playwright (already in devDependencies)
npm install

# Install browser binaries (required once)
npx playwright install
```

#### Running E2E Tests

```bash
cd frontend

# Run all e2e tests (headless)
npm run test:e2e

# Run with interactive UI (great for debugging)
npm run test:e2e:ui

# Run with visible browser
npm run test:e2e:headed

# View HTML test report
npm run test:e2e:report

# Run specific test file
npx playwright test e2e/dashboard.spec.js

# Run tests in debug mode
npx playwright test --debug
```

#### E2E Test Structure

E2E tests are located in `frontend/e2e/`:

```
frontend/e2e/
├── dashboard.spec.js      # Dashboard page tests
├── practice-flow.spec.js  # Practice session flow (TODO)
├── review-flow.spec.js    # Review queue flow (TODO)
└── search.spec.js         # Search/command palette (TODO)
```

#### Example E2E Test

```javascript
import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should load the dashboard page', async ({ page }) => {
    await expect(page).toHaveURL('/')
    await expect(page.locator('main')).toBeVisible()
  })

  test('should navigate to practice page', async ({ page }) => {
    const practiceCard = page.getByRole('link', { name: /practice/i })
    await practiceCard.click()
    await expect(page).toHaveURL('/practice')
  })
})
```

#### Playwright Configuration

The `playwright.config.js` file configures:
- Test directory: `./e2e`
- Base URL: `http://localhost:3000`
- Auto-starts dev server before tests
- Screenshots/videos on failure
- HTML reporter for test results

---

## Running All Tests

Use the unified test runner script to execute all tests:

```bash
# From project root
python scripts/run_all_tests.py
```

### Command-Line Options

```bash
# Run all tests (default - excludes e2e by default)
python scripts/run_all_tests.py

# Run specific test suites
python scripts/run_all_tests.py --backend-unit
python scripts/run_all_tests.py --backend-integration
python scripts/run_all_tests.py --frontend          # Frontend unit tests
python scripts/run_all_tests.py --frontend-e2e      # Frontend e2e tests (Playwright)
python scripts/run_all_tests.py --backend           # Both backend unit and integration

# Run all frontend tests (unit + e2e)
python scripts/run_all_tests.py --frontend --frontend-e2e

# Run with coverage
python scripts/run_all_tests.py --coverage

# Stop on first failure
python scripts/run_all_tests.py --fail-fast

# Run in parallel (faster)
python scripts/run_all_tests.py --parallel

# Verbose output
python scripts/run_all_tests.py --verbose

# Run e2e tests with visible browser
python scripts/run_all_tests.py --frontend-e2e --e2e-headed
```

---

## Test Configuration

### Backend (pytest.ini)

The `backend/pytest.ini` file configures pytest behavior:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto

markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (requires running services)
    slow: Tests that take a long time to run
    database: Tests that require PostgreSQL
    redis: Tests that require Redis
    vault: Tests that require a vault directory
```

### Test Environment Variables

Tests use isolated configuration. The test suite automatically sets:

| Variable | Test Value |
|----------|------------|
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `testuser` |
| `POSTGRES_PASSWORD` | `testpass` |
| `POSTGRES_DB` | `testdb` |
| `REDIS_URL` | `redis://localhost:6379/1` |
| `NEO4J_URI` | `bolt://localhost:7687` |
| `OBSIDIAN_VAULT_PATH` | `/tmp/test_vault` |

To override (advanced), set environment variables before running:

```bash
export POSTGRES_TEST_USER=custom_user
export POSTGRES_TEST_PASSWORD=custom_pass
export POSTGRES_TEST_DB=custom_db
pytest tests/integration/ -v
```

### Running Tests by Marker

```bash
# Run only database tests
pytest tests/ -m database

# Run only unit tests
pytest tests/ -m unit

# Skip slow tests
pytest tests/ -m "not slow"

# Combine markers
pytest tests/ -m "database and not slow"
```

---

## Writing Tests

### Test Naming Convention

```
test_<method_name>_<scenario>_<expected_result>

Examples:
- test_get_folder_returns_correct_path
- test_create_session_stores_data_with_ttl
- test_validation_fails_for_missing_template
```

### Unit Test Template

```python
"""
Unit Tests for [Module Name]

Tests [component] functionality with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestClassName:
    """Test suite for [component]."""

    def test_something_works(self) -> None:
        """Description of what this test verifies."""
        # Arrange
        input_data = "test"
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_operation(self) -> None:
        """Test an async function."""
        result = await async_function()
        assert result is not None
```

### Integration Test Template

```python
"""
Integration Tests for [Feature]

Tests [feature] with real database connections.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestFeatureIntegration:
    """Integration tests for [feature]."""

    @pytest.mark.asyncio
    async def test_creates_record(self, clean_db: AsyncSession) -> None:
        """Test creating a record in the database."""
        # Arrange
        data = {"name": "test"}
        
        # Act
        record = await create_record(clean_db, data)
        
        # Assert
        assert record.id is not None
        assert record.name == "test"
```

### Available Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `sample_yaml_config` | function | Sample YAML configuration dict |
| `mock_redis` | function | Mocked Redis client |
| `mock_db_session` | function | Mocked database session |
| `temp_vault` | function | Complete temporary vault directory |
| `incomplete_vault` | function | Incomplete vault for failure tests |
| `db_session` | function | Real database session (integration) |
| `clean_db` | function | Database session with cleaned tables |
| `redis_client` | function | Real Redis client (integration) |
| `test_client` | function | FastAPI TestClient |
| `async_test_client` | function | Async HTTP client for API tests |

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run unit tests
        run: |
          cd backend
          pytest tests/unit/ -v --cov=app --cov-report=xml
      
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration/ -v

  frontend-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run unit tests
        run: |
          cd frontend
          npm test -- --coverage

  frontend-e2e-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Install Playwright browsers
        run: |
          cd frontend
          npx playwright install --with-deps
      
      - name: Run e2e tests
        run: |
          cd frontend
          npm run test:e2e
      
      - name: Upload Playwright report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30
```

---

## Troubleshooting

### Common Issues

#### "Integration test services not available"

Start Docker services:
```bash
docker-compose up -d postgres redis neo4j
# Or use standalone containers
docker run -d --name test-postgres -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=testdb -p 5432:5432 postgres:16-alpine
```

#### "Module not found" errors

Install dependencies:
```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

#### Tests hanging

Check if services are healthy:
```bash
docker-compose ps
docker-compose logs postgres
```

#### Database connection refused

Ensure PostgreSQL is running with test credentials:
```bash
# Check if test database is running
docker ps | grep test-postgres

# Verify connection
psql -h localhost -U testuser -d testdb
```

#### "SAFETY CHECK FAILED" error

This means tests detected production database credentials. Ensure you're using test credentials:
```bash
export POSTGRES_TEST_USER=testuser
export POSTGRES_TEST_PASSWORD=testpass
export POSTGRES_TEST_DB=testdb
```

### Debugging Tests

```bash
# Show print statements
pytest tests/ -v -s

# Drop into debugger on failure
pytest tests/ --pdb

# Show local variables in tracebacks
pytest tests/ -l

# Verbose output with detailed assertions
pytest tests/ -vv

# Run last failed tests only
pytest tests/ --lf

# Stop on first failure
pytest tests/ -x
```

### Cleaning Up

```bash
# Stop and remove test containers
docker stop test-postgres test-redis && docker rm test-postgres test-redis

# Or with docker-compose
docker-compose down -v  # -v removes volumes
```

---

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest](https://vitest.dev/)
- Backend tests README: `backend/tests/README.md`
- Implementation plan: `docs/implementation_plan/00_foundation_implementation.md` Section 4
