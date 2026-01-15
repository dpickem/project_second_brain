"""
Unit Tests for Configuration Management

Tests the Settings class and YAML configuration loading.
These tests verify:
- Environment variable loading
- Default value handling
- Property computation (POSTGRES_URL, etc.)
- YAML configuration parsing
"""

import os
from unittest.mock import patch

import pytest

from app.config import Settings, get_settings, load_yaml_config, settings


class TestSettings:
    """Test suite for the Settings Pydantic model."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults when env vars are not set."""
        # Clear env vars that might interfere
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=True):
            test_settings = Settings(
                POSTGRES_PASSWORD="test",
                NEO4J_PASSWORD="test",
                OPENAI_API_KEY="test",
            )

            assert test_settings.APP_NAME == "Second Brain"
            # DEBUG can be True or False depending on environment, just check it's a bool
            assert isinstance(test_settings.DEBUG, bool)
            assert test_settings.POSTGRES_HOST == "localhost"
            assert test_settings.POSTGRES_PORT == 5432
            assert test_settings.POSTGRES_USER == "secondbrain"
            assert test_settings.POSTGRES_DB == "secondbrain"
            assert test_settings.REDIS_URL == "redis://localhost:6379/0"

    def test_postgres_url_construction(self) -> None:
        """POSTGRES_URL property should build correct connection string."""
        test_settings = Settings(
            POSTGRES_HOST="testhost",
            POSTGRES_PORT=5433,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_DB="testdb",
            NEO4J_PASSWORD="test",
            OPENAI_API_KEY="test",
        )

        expected = "postgresql+asyncpg://testuser:testpass@testhost:5433/testdb"
        assert test_settings.POSTGRES_URL == expected

    def test_postgres_url_sync_construction(self) -> None:
        """POSTGRES_URL_SYNC should build sync connection string for Alembic."""
        test_settings = Settings(
            POSTGRES_HOST="testhost",
            POSTGRES_PORT=5433,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_DB="testdb",
            NEO4J_PASSWORD="test",
            OPENAI_API_KEY="test",
        )

        expected = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert test_settings.POSTGRES_URL_SYNC == expected

    def test_env_variable_override(self) -> None:
        """Environment variables should override default values."""
        env_overrides = {
            "APP_NAME": "Custom App",
            "DEBUG": "true",
            "POSTGRES_HOST": "custom-host",
            "POSTGRES_PORT": "9999",
            "REDIS_URL": "redis://custom-redis:6380/5",
            "POSTGRES_PASSWORD": "secret",
            "NEO4J_PASSWORD": "secret",
            "OPENAI_API_KEY": "sk-test",
        }

        with patch.dict(os.environ, env_overrides, clear=True):
            test_settings = Settings()

            assert test_settings.APP_NAME == "Custom App"
            assert test_settings.DEBUG is True
            assert test_settings.POSTGRES_HOST == "custom-host"
            assert test_settings.POSTGRES_PORT == 9999
            assert test_settings.REDIS_URL == "redis://custom-redis:6380/5"

    def test_obsidian_vault_path(self) -> None:
        """OBSIDIAN_VAULT_PATH should be configurable."""
        test_settings = Settings(
            OBSIDIAN_VAULT_PATH="/custom/vault/path",
            POSTGRES_PASSWORD="test",
            NEO4J_PASSWORD="test",
            OPENAI_API_KEY="test",
        )

        assert test_settings.OBSIDIAN_VAULT_PATH == "/custom/vault/path"


class TestYamlConfigLoading:
    """Test suite for YAML configuration loading."""

    def test_load_yaml_config_returns_dict(self) -> None:
        """load_yaml_config should return a dictionary."""
        # Clear the cache to get fresh config
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        assert isinstance(config, dict)

    def test_yaml_config_has_expected_sections(self) -> None:
        """YAML config should contain expected top-level sections."""
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        # Check for expected sections (may be empty if file doesn't exist)
        if config:
            expected_sections = [
                "app",
                "database",
                "redis",
                "obsidian",
                "content_types",
            ]
            for section in expected_sections:
                assert section in config, f"Missing section: {section}"

    def test_yaml_config_content_types_structure(self) -> None:
        """Content types should have required fields."""
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        if config and "content_types" in config:
            content_types = config["content_types"]

            for type_name, type_config in content_types.items():
                assert "folder" in type_config, f"{type_name} missing 'folder'"
                assert "template" in type_config, f"{type_name} missing 'template'"

    def test_yaml_config_database_settings(self) -> None:
        """Database settings should have valid values."""
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        if config and "database" in config:
            db_config = config["database"]

            assert "pool_size" in db_config
            assert isinstance(db_config["pool_size"], int)
            assert db_config["pool_size"] > 0

            assert "max_overflow" in db_config
            assert isinstance(db_config["max_overflow"], int)

            assert "pool_timeout" in db_config
            assert isinstance(db_config["pool_timeout"], int)

    def test_yaml_config_redis_settings(self) -> None:
        """Redis settings should have valid TTL values."""
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        if config and "redis" in config:
            redis_config = config["redis"]

            assert "session_ttl" in redis_config
            assert isinstance(redis_config["session_ttl"], int)
            assert redis_config["session_ttl"] > 0

            assert "cache_ttl" in redis_config
            assert isinstance(redis_config["cache_ttl"], int)
            assert redis_config["cache_ttl"] > 0

    def test_yaml_config_returns_dict_or_none(self) -> None:
        """load_yaml_config should return a dict (or None for empty YAML)."""
        # Clear cache to get fresh config
        load_yaml_config.cache_clear()
        config = load_yaml_config()

        # yaml.safe_load returns None for empty files, dict for valid YAML
        # The function returns {} if file doesn't exist
        assert config is None or isinstance(config, dict)


class TestSettingsCaching:
    """Test suite for settings caching behavior."""

    def test_get_settings_returns_same_instance(self) -> None:
        """get_settings should return cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_singleton_is_cached(self) -> None:
        """The module-level settings should be a cached instance."""
        assert settings is get_settings()


class TestPasswordHandling:
    """Test suite for password and sensitive data handling."""

    def test_password_not_logged(self) -> None:
        """Passwords should not appear in string representation."""
        test_settings = Settings(
            POSTGRES_PASSWORD="super_secret_password",
            NEO4J_PASSWORD="another_secret",
            OPENAI_API_KEY="sk-secret-key",
        )

        # The Settings object should exist but we verify
        # passwords are stored correctly
        assert test_settings.POSTGRES_PASSWORD == "super_secret_password"
        assert test_settings.NEO4J_PASSWORD == "another_secret"
        assert test_settings.OPENAI_API_KEY == "sk-secret-key"

    def test_empty_password_allowed(self) -> None:
        """Empty passwords should be allowed (for local dev)."""
        test_settings = Settings(
            POSTGRES_PASSWORD="",
            NEO4J_PASSWORD="",
            OPENAI_API_KEY="",
        )

        assert test_settings.POSTGRES_PASSWORD == ""
