# Second Brain Test Suite

This directory contains unit and integration tests for the Phase 1 foundation implementation.

## Quick Start

```bash
# From the backend directory
cd backend

# Run all unit tests (fast, no services needed)
pytest tests/unit/ -v

# Run all tests (requires Docker services)
pytest tests/ -v
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # Pytest settings
│
├── unit/                    # Unit tests (no external dependencies)
│   ├── test_config.py       # Configuration loading tests
│   ├── test_content_types.py # Content type registry tests
│   └── test_redis.py        # Redis utilities tests (mocked)
│
└── integration/             # Integration tests (require services)
    ├── conftest.py          # Integration-specific fixtures
    ├── test_database.py     # PostgreSQL model tests
    ├── test_health.py       # Health endpoint tests
    └── test_vault.py        # Vault validation tests
```

## Running Tests

### Unit Tests Only (No Services Required)

Unit tests use mocks and don't need any external services:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific unit test file
pytest tests/unit/test_config.py -v

# Run specific test class
pytest tests/unit/test_config.py::TestSettings -v

# Run specific test method
pytest tests/unit/test_config.py::TestSettings::test_default_values -v
```

### Integration Tests (Services Required)

Integration tests require PostgreSQL, Redis, and Neo4j to be running.

**Important:** Integration tests use dedicated test credentials (`testuser`/`testpass`/`testdb`) 
that are separate from your `.env` configuration. This ensures tests don't affect your 
development database and don't require modifying your `.env` file.

#### Option 1: Standalone Test Database (Recommended)

Run a dedicated PostgreSQL container for tests:

```bash
# Start a test database container
docker run -d --name test-postgres \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16-alpine

# Run integration tests (tables are created automatically)
pytest tests/integration/ -v

# Stop and remove when done
docker stop test-postgres && docker rm test-postgres
```

**Note:** Database tables are created automatically when tests start. No manual migration needed.

#### Option 2: Use Docker Compose Services

If you want to test against the full stack:

```bash
# Start services with Docker Compose
docker-compose up -d postgres redis neo4j

# Wait for services to be healthy
docker-compose ps

# Run integration tests (uses test credentials, not .env)
pytest tests/integration/ -v

# Run specific integration test file
pytest tests/integration/test_database.py -v

# Stop services when done
docker-compose down
```

**Note:** When using docker-compose, the tests still use their own test credentials. 
If your docker-compose PostgreSQL uses different credentials, you'll need to either:
- Create a `testuser` in your PostgreSQL, or
- Use the standalone test database (Option 1)

### All Tests

```bash
# Run everything
pytest tests/ -v

# Run with short output
pytest tests/

# Stop on first failure
pytest tests/ -x

# Run last failed tests only
pytest tests/ --lf
```

## Test Coverage

```bash
# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html

# Coverage for specific module
pytest tests/ --cov=app.config --cov-report=term-missing

# Generate XML coverage for CI
pytest tests/ --cov=app --cov-report=xml
```

## Debugging Tests

```bash
# Show print statements
pytest tests/ -v -s

# Drop into debugger on failure
pytest tests/ --pdb

# Show local variables in tracebacks
pytest tests/ -l

# Verbose output with detailed assertions
pytest tests/ -vv
```

## Running Tests by Marker

```bash
# Run only database tests
pytest tests/ -m database

# Run only unit tests
pytest tests/ -m unit

# Skip slow tests
pytest tests/ -m "not slow"
```

## Environment Variables

**Tests use their own isolated configuration** - you don't need to modify your `.env` file.

The test suite automatically sets these credentials:

| Variable | Test Value |
|----------|------------|
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `testuser` |
| `POSTGRES_PASSWORD` | `testpass` |
| `POSTGRES_DB` | `testdb` |
| `REDIS_URL` | `redis://localhost:6379/1` |
| `NEO4J_URI` | `bolt://localhost:7687` |
| `NEO4J_USER` | `neo4j` |
| `NEO4J_PASSWORD` | `testpass` |
| `OBSIDIAN_VAULT_PATH` | `/tmp/test_vault` |

To override these (advanced), set environment variables before running pytest:

```bash
export POSTGRES_HOST=custom-host
pytest tests/integration/ -v
```

## Test Fixtures

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

### Using Fixtures

```python
# In your test file
def test_something(temp_vault, sample_yaml_config):
    """Test using fixtures."""
    assert temp_vault.exists()
    assert "content_types" in sample_yaml_config
```

## Writing New Tests

### Naming Convention

```
test_<method_name>_<scenario>_<expected_result>

Examples:
- test_get_folder_returns_correct_path
- test_create_session_stores_data_with_ttl
- test_validation_fails_for_missing_template
```

### Test Template

```python
"""
Unit/Integration Tests for [Module Name]

Brief description of what's being tested.
"""

import pytest
from typing import Any


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

## Common Issues

### "Integration test services not available"

Start Docker services:
```bash
docker-compose up -d
```

### "Module not found" errors

Install dependencies:
```bash
pip install -r requirements.txt
```

### Tests hanging

Check if services are healthy:
```bash
docker-compose ps
docker-compose logs postgres
```

### Database connection refused

Ensure a PostgreSQL instance is running with test credentials:
```bash
# Check if test database is running
docker ps | grep test-postgres

# Or start a test database
docker run -d --name test-postgres \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -e POSTGRES_DB=testdb \
  -p 5432:5432 \
  postgres:16-alpine

# Verify connection
psql -h localhost -U testuser -d testdb
```

## CI/CD

Tests can be run in CI with:

```yaml
# GitHub Actions example
- name: Run unit tests
  run: |
    cd backend
    pytest tests/unit/ -v --cov=app --cov-report=xml

- name: Run integration tests
  run: |
    cd backend
    pytest tests/integration/ -v
```

## More Information

See `docs/implementation_plan/00_foundation_implementation.md` Section 4 for the complete testing strategy.

