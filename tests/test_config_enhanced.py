"""Tests for enhanced configuration management."""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from app.config import (
    Config,
    SlackConfig,
    OpenAIConfig,
    DatabaseConfig,
    EmojiConfig,
    LoggingConfig,
    MonitoringConfig,
)


class TestEnhancedConfig:
    """Test enhanced configuration functionality."""

    def teardown_method(self):
        """Reset singleton instance after each test."""
        Config._instance = None
        Config._loaded = False

    def test_singleton_pattern(self):
        """Test that Config uses singleton pattern."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_default_configuration(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {"ENVIRONMENT": "default"}, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

        # Check default values
        assert config.ENVIRONMENT == "default"
        assert config.slack.socket_mode_enabled is True
        assert config.slack.request_timeout == 30
        assert config.openai.model == "text-embedding-3-small"
        assert config.openai.embedding_dimension == 1536
        assert config.database.pool_size == 10
        assert config.emoji.default_reaction_count == 3
        assert config.logging.level == "INFO"
        assert config.monitoring.enabled is True

    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            "SLACK_BOT_TOKEN": "test-bot-token",
            "SLACK_APP_TOKEN": "test-app-token",
            "OPENAI_API_KEY": "test-api-key",
            "DATABASE_URL": "postgresql://test:test@testhost:5432/testdb",
            "LOG_LEVEL": "DEBUG",
            "EMOJI_CACHE_TTL": "7200",
            "MAX_CONCURRENT_REACTIONS": "20",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

            assert config.slack.bot_token == "test-bot-token"
            assert config.slack.app_token == "test-app-token"
            assert config.openai.api_key == "test-api-key"
            assert config.database.url == "postgresql://test:test@testhost:5432/testdb"
            assert config.logging.level == "DEBUG"
            assert config.emoji.cache_ttl == 7200
            assert config.emoji.max_concurrent_reactions == 20

    def test_config_file_loading(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "slack": {"request_timeout": 45, "max_retries": 5},
            "openai": {"base_delay": 2.0},
            "emoji": {"cache_ttl": 7200},
        }

        mock_file_content = json.dumps(config_data)

        with patch.dict(
            os.environ, {"CONFIG_FILE": "/tmp/test_config.json"}, clear=True
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=mock_file_content)):
                    Config._instance = None
                    Config._loaded = False
                    config = Config()

                    # File config should override defaults
                    assert config.slack.request_timeout == 45
                    assert config.slack.max_retries == 5
                    assert config.openai.base_delay == 2.0
                    assert config.emoji.cache_ttl == 7200

    def test_environment_specific_overrides(self):
        """Test environment-specific configuration overrides."""
        # Test production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

            assert config.logging.level == "WARNING"
            assert config.logging.format == "json"
            assert config.logging.use_colors is False
            assert config.monitoring.enabled is True

        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

            assert config.logging.use_colors is True
            assert config.monitoring.enabled is False

    def test_legacy_field_compatibility(self):
        """Test backward compatibility with legacy fields."""
        env_vars = {
            "SLACK_BOT_TOKEN": "legacy-bot-token",
            "OPENAI_API_KEY": "legacy-api-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

            # Legacy fields should be updated
            assert config.SLACK_BOT_TOKEN == "legacy-bot-token"
            assert config.slack.bot_token == "legacy-bot-token"
            assert config.OPENAI_API_KEY == "legacy-api-key"
            assert config.openai.api_key == "legacy-api-key"

    def test_config_validation_success(self):
        """Test successful configuration validation."""
        env_vars = {
            "SLACK_BOT_TOKEN": "valid-token",
            "SLACK_APP_TOKEN": "valid-token",
            "OPENAI_API_KEY": "valid-key",
            "DATABASE_URL": "postgresql://valid:valid@host:5432/db",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            Config._instance = None
            Config._loaded = False
            assert Config.validate() is True

    def test_config_validation_missing_required(self):
        """Test configuration validation with missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            Config._instance = None
            Config._loaded = False

            with pytest.raises(ValueError) as exc_info:
                Config.validate()

            error_msg = str(exc_info.value)
            assert "SLACK_BOT_TOKEN is required" in error_msg
            assert "SLACK_APP_TOKEN is required" in error_msg
            assert "OPENAI_API_KEY is required" in error_msg

    def test_config_validation_invalid_values(self):
        """Test configuration validation with invalid values."""
        env_vars = {
            "SLACK_BOT_TOKEN": "valid",
            "SLACK_APP_TOKEN": "valid",
            "OPENAI_API_KEY": "valid",
            "DATABASE_URL": "valid",
            "LOG_LEVEL": "INVALID_LEVEL",
            "OPENAI_EMBEDDING_DIM": "9999",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            Config._instance = None
            Config._loaded = False

            with pytest.raises(ValueError) as exc_info:
                Config.validate()

            error_msg = str(exc_info.value)
            assert "Invalid log level: INVALID_LEVEL" in error_msg
            assert "Invalid embedding dimension: 9999" in error_msg

    def test_environment_check_methods(self):
        """Test environment checking methods."""
        # Development
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            Config._instance = None
            Config._loaded = False
            assert Config.is_development() is True
            assert Config.is_production() is False
            assert Config.is_testing() is False

        # Production
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            Config._instance = None
            Config._loaded = False
            assert Config.is_development() is False
            assert Config.is_production() is True
            assert Config.is_testing() is False

        # Testing
        with patch.dict(os.environ, {"ENVIRONMENT": "testing"}, clear=True):
            Config._instance = None
            Config._loaded = False
            assert Config.is_development() is False
            assert Config.is_production() is False
            assert Config.is_testing() is True

    def test_config_summary_with_masking(self):
        """Test configuration summary with sensitive data masking."""
        env_vars = {
            "SLACK_BOT_TOKEN": "xoxb-1234567890-abcdefghijk",
            "OPENAI_API_KEY": "sk-1234567890abcdefghijk",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/db",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            Config._instance = None
            Config._loaded = False
            config = Config()

            summary = config.get_config_summary()

            # Check that sensitive data is masked
            assert summary["slack"]["bot_token"] == "xoxb...hijk"
            assert summary["openai"]["api_key"] == "sk-1...hijk"
            assert "password" not in summary["database"]["url"]
            assert "****" in summary["database"]["url"]

    def test_mask_sensitive_values(self):
        """Test sensitive value masking."""
        config = Config()

        # Test various masking scenarios
        assert config._mask_sensitive("") == "<not_set>"
        assert config._mask_sensitive("short") == "*****"
        assert config._mask_sensitive("1234567890") == "1234...7890"
        assert config._mask_sensitive("verylongsecretkey123") == "very...y123"

    def test_mask_database_url(self):
        """Test database URL masking."""
        config = Config()

        # Test various URL formats
        assert config._mask_database_url("") == "<not_set>"

        url1 = "postgresql://user:pass@localhost:5432/db"
        masked1 = config._mask_database_url(url1)
        assert "pass" not in masked1
        assert "****" in masked1
        assert "localhost:5432/db" in masked1

        url2 = "sqlite:///path/to/db.sqlite"
        masked2 = config._mask_database_url(url2)
        assert "sqlite:///" in masked2

    def test_export_config(self):
        """Test configuration export functionality."""
        config = Config()

        with patch("builtins.open", mock_open()) as mock_file:
            config.export_config("/tmp/config_export.json", include_sensitive=False)

            mock_file.assert_called_once_with(Path("/tmp/config_export.json"), "w")

            # Check that data was written
            written_data = ""
            for call in mock_file().write.call_args_list:
                written_data += call[0][0]

            # Parse and verify structure
            exported = json.loads(written_data)
            assert "environment" in exported
            assert "slack" in exported
            assert "openai" in exported

            # Sensitive data should be masked
            assert "****" not in exported["slack"].get("bot_token", "")

    def test_config_dataclasses(self):
        """Test individual configuration dataclasses."""
        # Test SlackConfig
        slack_config = SlackConfig(
            bot_token="test-token",
            app_token="test-app",
            socket_mode_enabled=False,
            request_timeout=60,
        )
        assert slack_config.bot_token == "test-token"
        assert slack_config.socket_mode_enabled is False

        # Test OpenAIConfig
        openai_config = OpenAIConfig(
            api_key="test-key", model="gpt-3.5-turbo", embedding_dimension=3072
        )
        assert openai_config.model == "gpt-3.5-turbo"
        assert openai_config.embedding_dimension == 3072

        # Test DatabaseConfig
        db_config = DatabaseConfig(url="postgresql://test", pool_size=20)
        assert db_config.pool_size == 20

        # Test EmojiConfig
        emoji_config = EmojiConfig(default_reaction_count=5, cache_enabled=False)
        assert emoji_config.default_reaction_count == 5
        assert emoji_config.cache_enabled is False

        # Test LoggingConfig
        log_config = LoggingConfig(level="DEBUG", format="json", use_colors=False)
        assert log_config.level == "DEBUG"
        assert log_config.format == "json"

        # Test MonitoringConfig
        monitor_config = MonitoringConfig(enabled=False, metrics_port=8080)
        assert monitor_config.enabled is False
        assert monitor_config.metrics_port == 8080
