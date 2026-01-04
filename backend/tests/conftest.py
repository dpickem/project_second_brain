"""
Shared Test Fixtures and Configuration

This module provides pytest fixtures used across unit and integration tests.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from dotenv import load_dotenv

# Add the backend directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file from project root BEFORE any fixtures run
# This ensures POSTGRES_TEST_* variables are available
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    # Try backend directory
    _backend_env = Path(__file__).parent.parent / ".env"
    if _backend_env.exists():
        load_dotenv(_backend_env)


# ============================================================================
# Async Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.

    This fixture is required for async tests and is scoped to the session
    to avoid creating a new loop for each test.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Configuration
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> Generator[None, None, None]:
    """
    Set up test environment variables before any tests run.

    This ensures tests run with predictable configuration, overriding
    any values from .env files to ensure test isolation.
    """
    # Store original environment
    original_env = os.environ.copy()

    # Forcefully set test environment variables (override .env values)
    # Test database credentials come from POSTGRES_TEST_* env vars if set,
    # otherwise fall back to defaults for CI environments
    test_env = {
        "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "POSTGRES_USER": os.environ.get("POSTGRES_TEST_USER", "testuser"),
        "POSTGRES_PASSWORD": os.environ.get("POSTGRES_TEST_PASSWORD", "testpass"),
        "POSTGRES_DB": os.environ.get("POSTGRES_TEST_DB", "testdb"),
        "REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        "NEO4J_URI": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "NEO4J_USER": os.environ.get("NEO4J_USER", "neo4j"),
        "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "testpass"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", "test-api-key"),
        "OBSIDIAN_VAULT_PATH": os.environ.get("OBSIDIAN_VAULT_PATH", "/tmp/test_vault"),
        "DEBUG": "true",
    }
    os.environ.update(test_env)

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# Sample Configuration Data
# ============================================================================


@pytest.fixture
def sample_yaml_config() -> dict[str, Any]:
    """
    Provide a sample YAML configuration for testing.

    This matches the structure of config/default.yaml.
    """
    return {
        "app": {
            "name": "Test Second Brain",
            "debug": True,
        },
        "database": {
            "pool_size": 3,
            "max_overflow": 5,
            "pool_timeout": 10,
        },
        "redis": {
            "session_ttl": 1800,
            "cache_ttl": 120,
        },
        "obsidian": {
            "vault_path": "/vault",
            "system_folders": [
                "topics",
                "concepts",
                "exercises/by-topic",
                "exercises/daily",
                "reviews/due",
                "reviews/archive",
                "daily",
                "templates",
                "meta",
                "assets/images",
                "assets/pdfs",
            ],
            "meta": {
                "folder": "meta",
                "tag_taxonomy_file": "tag-taxonomy.md",
            },
        },
        "content_types": {
            "paper": {
                "folder": "sources/papers",
                "template": "templates/paper.md",
                "jinja_template": "paper.md.j2",
                "description": "Academic papers",
                "icon": "📄",
                "file_types": ["pdf"],
            },
            "article": {
                "folder": "sources/articles",
                "template": "templates/article.md",
                "jinja_template": "article.md.j2",
                "description": "Blog posts",
                "icon": "📰",
                "file_types": ["url", "html"],
            },
            "book": {
                "folder": "sources/books",
                "template": "templates/book.md",
                "jinja_template": "book.md.j2",
                "description": "Book notes",
                "icon": "📚",
                "file_types": ["pdf", "epub"],
            },
            "concept": {
                "folder": "concepts",
                "template": "templates/concept.md",
                "jinja_template": "concept.md.j2",
                "description": "Atomic concepts",
                "icon": "🧩",
                "system": True,
            },
            "daily": {
                "folder": "daily",
                "template": "templates/daily.md",
                "jinja_template": "daily.md.j2",
                "description": "Daily notes",
                "icon": "📅",
                "system": True,
            },
        },
    }


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_redis() -> MagicMock:
    """
    Create a mock Redis client for unit testing.

    This allows testing Redis-dependent code without a real Redis server.
    """
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    mock.ping = AsyncMock(return_value=True)
    mock.keys = AsyncMock(return_value=[])
    mock.rpush = AsyncMock(return_value=1)
    mock.lpop = AsyncMock(return_value=None)
    mock.blpop = AsyncMock(return_value=None)
    mock.llen = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_db_session() -> MagicMock:
    """
    Create a mock database session for unit testing.
    """
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    mock.close = AsyncMock()
    return mock


# ============================================================================
# Temporary Vault Fixture
# ============================================================================


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """
    Create a temporary vault directory structure for testing.

    Creates a minimal vault structure that can be used for
    vault validation and file operation tests.
    """
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()

    # Create system folders
    folders = [
        "topics",
        "concepts",
        "exercises/by-topic",
        "exercises/daily",
        "reviews/due",
        "reviews/archive",
        "daily",
        "templates",
        "meta",
        "assets/images",
        "assets/pdfs",
        "sources/papers",
        "sources/articles",
        "sources/books",
        "sources/ideas",
    ]

    for folder in folders:
        (vault_path / folder).mkdir(parents=True, exist_ok=True)

    # Create .obsidian configuration directory
    obsidian_dir = vault_path / ".obsidian"
    obsidian_dir.mkdir()

    # Create app.json
    app_config = {
        "alwaysUpdateLinks": True,
        "newFileLocation": "folder",
        "newFileFolderPath": "sources/ideas",
        "attachmentFolderPath": "assets",
    }
    (obsidian_dir / "app.json").write_text(json.dumps(app_config))

    # Create core-plugins.json
    core_plugins = [
        "file-explorer",
        "global-search",
        "switcher",
        "graph",
        "backlink",
        "daily-notes",
        "templates",
    ]
    (obsidian_dir / "core-plugins.json").write_text(json.dumps(core_plugins))

    # Create sample templates
    paper_template = """---
type: paper
title: "{{title}}"
authors: []
year: {{date:YYYY}}
tags: []
status: unread
created: {{date:YYYY-MM-DD}}
---

## Summary

## Key Findings
"""
    (vault_path / "templates" / "paper.md").write_text(paper_template)

    article_template = """---
type: article
title: "{{title}}"
source: ""
tags: []
status: unread
created: {{date:YYYY-MM-DD}}
---

## Summary

## Key Takeaways
"""
    (vault_path / "templates" / "article.md").write_text(article_template)

    book_template = """---
type: book
title: "{{title}}"
author: ""
tags: []
status: reading
---

## Overview

## Key Themes
"""
    (vault_path / "templates" / "book.md").write_text(book_template)

    concept_template = """---
type: concept
name: "{{title}}"
domain: ""
tags: []
---

## Definition

## Why It Matters
"""
    (vault_path / "templates" / "concept.md").write_text(concept_template)

    daily_template = """---
type: daily
date: {{date:YYYY-MM-DD}}
---

# {{date:dddd, MMMM D, YYYY}}

## Inbox

## Tasks
"""
    (vault_path / "templates" / "daily.md").write_text(daily_template)

    # Create meta files
    dashboard_content = """---
type: meta
title: "Dashboard"
---

# Second Brain Dashboard

## Quick Stats
"""
    (vault_path / "meta" / "dashboard.md").write_text(dashboard_content)

    return vault_path


@pytest.fixture
def incomplete_vault(tmp_path: Path) -> Path:
    """
    Create an incomplete vault for testing validation failures.

    This vault is missing several required folders and templates.
    """
    vault_path = tmp_path / "incomplete_vault"
    vault_path.mkdir()

    # Create only a few folders (incomplete)
    (vault_path / "topics").mkdir()
    (vault_path / "templates").mkdir()

    # Create a template with missing type field
    bad_template = """---
title: "{{title}}"
---

# Content
"""
    (vault_path / "templates" / "bad.md").write_text(bad_template)

    return vault_path
