"""
Second Brain Test Suite

This package contains unit and integration tests for the Phase 1 foundation implementation.

Test Structure:
    tests/
    ├── conftest.py          # Shared fixtures and configuration
    ├── unit/                # Unit tests (isolated, no external dependencies)
    │   ├── test_config.py   # Configuration loading tests
    │   ├── test_content_types.py  # Content type registry tests
    │   └── test_redis.py    # Redis utility tests (mocked)
    └── integration/         # Integration tests (require running services)
        ├── test_database.py # PostgreSQL connection and model tests
        ├── test_health.py   # Health endpoint tests
        └── test_vault.py    # Vault validation tests

Running Tests:
    # Run all tests
    pytest tests/ -v

    # Run only unit tests (fast, no dependencies)
    pytest tests/unit/ -v

    # Run only integration tests (requires Docker services)
    pytest tests/integration/ -v

    # Run with coverage
    pytest tests/ --cov=app --cov-report=html
"""
