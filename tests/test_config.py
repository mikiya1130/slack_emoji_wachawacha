"""
Tests for configuration management.
This serves as a basic test to verify TDD infrastructure is working.
"""

import pytest
import os
from unittest.mock import patch
from app.config import Config
import importlib
import app.config


class TestConfig:
    """Test configuration management functionality."""

    def test_config_import(self):
        """Test that config module can be imported."""
        # Config is already imported at the top of the file
        assert Config is not None

    def test_config_environment_variables(self, monkeypatch):
        """Test that config reads environment variables correctly."""
        # Set test environment variables
        monkeypatch.setenv("SLACK_BOT_TOKEN", "test-bot-token")
        monkeypatch.setenv("SLACK_APP_TOKEN", "test-app-token")
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("ENVIRONMENT", "test")

        # Reload config to pick up new environment variables
        importlib.reload(app.config)
        from app.config import Config

        assert Config.SLACK_BOT_TOKEN == "test-bot-token"
        assert Config.SLACK_APP_TOKEN == "test-app-token"
        assert Config.OPENAI_API_KEY == "test-openai-key"
        assert Config.ENVIRONMENT == "test"

    def test_config_validation_success(self):
        """Test config validation with valid values."""
        # Mock valid config values
        with patch.object(Config, "SLACK_BOT_TOKEN", "valid-token"), patch.object(
            Config, "SLACK_APP_TOKEN", "valid-token"
        ), patch.object(Config, "OPENAI_API_KEY", "valid-key"):

            assert Config.validate() is True

    def test_config_validation_failure(self):
        """Test config validation with missing values."""
        # Mock environment variables with empty values
        with patch.dict(
            os.environ,
            {"SLACK_BOT_TOKEN": "", "SLACK_APP_TOKEN": "", "OPENAI_API_KEY": ""},
            clear=True,
        ):
            # Clear cached instance
            Config._instance = None
            Config._loaded = False

            with pytest.raises(ValueError, match="Configuration validation failed"):
                Config.validate()

    def test_config_environment_checks(self):
        """Test environment checking methods."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            Config._instance = None
            Config._loaded = False
            assert Config.is_development() is True
            assert Config.is_production() is False

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            Config._instance = None
            Config._loaded = False
            assert Config.is_development() is False
            assert Config.is_production() is True
