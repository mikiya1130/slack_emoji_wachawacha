"""
Pytest configuration and shared fixtures for Slack Emoji Bot tests.

This module provides common fixtures and configuration for all tests,
following TDD best practices with proper mocking and test isolation.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

# Import when dependencies are available
# from app.config import Config
# from app.services.database_service import DatabaseService
# from app.services.openai_service import OpenAIService
# from app.services.emoji_service import EmojiService
# from app.services.slack_handler import SlackHandler


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = Mock()
    config.SLACK_BOT_TOKEN = "xoxb-test-token"
    config.SLACK_APP_TOKEN = "xapp-test-token"
    config.OPENAI_API_KEY = "sk-test-key"
    config.DATABASE_URL = "postgresql://test:test@localhost:5432/test_db"
    config.EMBEDDING_MODEL = "text-embedding-3-small"
    config.EMBEDDING_DIMENSION = 1536
    config.DEFAULT_REACTION_COUNT = 3
    config.ENVIRONMENT = "test"
    config.LOG_LEVEL = "WARNING"
    return config


@pytest.fixture
def mock_database_service():
    """Mock DatabaseService for testing."""
    service = AsyncMock()
    service.execute_query = AsyncMock()
    service.vector_similarity_search = AsyncMock()
    return service


@pytest.fixture
def mock_openai_service():
    """Mock OpenAIService for testing."""
    service = AsyncMock()
    service.get_embedding = AsyncMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def mock_emoji_service():
    """Mock EmojiService for testing."""
    from app.services.emoji_service import EmojiService

    mock_db_service = AsyncMock()
    service = EmojiService(database_service=mock_db_service)

    return service


@pytest.fixture
def mock_slack_handler():
    """Mock SlackHandler for testing."""
    handler = Mock()
    handler.handle_message = AsyncMock()
    handler.add_reactions = AsyncMock()
    return handler


@pytest.fixture
def sample_slack_message():
    """Sample Slack message for testing."""
    return {
        "type": "message",
        "text": "今日はいい天気ですね！",
        "user": "U123456789",
        "channel": "C123456789",
        "ts": "1234567890.123456",
    }


@pytest.fixture
def sample_emoji_data():
    """Sample emoji data for testing."""
    return [
        {
            "id": 1,
            "code": ":smile:",
            "description": "Happy, joyful, pleased expression",
            "category": "emotion",
            "emotion_tone": "positive",
            "usage_scene": "greeting, celebration, good news",
            "priority": 5,
            "embedding": [0.1] * 1536,
        },
        {
            "id": 2,
            "code": ":sunny:",
            "description": "Bright, sunny, good weather",
            "category": "weather",
            "emotion_tone": "positive",
            "usage_scene": "weather, outdoor activities",
            "priority": 3,
            "embedding": [0.2] * 1536,
        },
    ]


@pytest.fixture
def sample_embedding_vector():
    """Sample embedding vector for testing."""
    return [0.1] * 1536


@pytest.fixture
def test_database_service():
    """Create a mocked database service for testing without external dependencies."""
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def test_emoji_service(test_database_service):
    """Create a mocked emoji service for testing without external dependencies"""
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing."""
    client = Mock()
    client.reactions_add = AsyncMock()
    client.chat_postMessage = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = Mock()
    client.embeddings = Mock()
    client.embeddings.create = AsyncMock()
    return client


# Environment setup fixtures
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


# Error simulation fixtures
@pytest.fixture
def mock_openai_error():
    """Mock OpenAI API error for testing error handling."""

    def side_effect(*args, **kwargs):
        raise Exception("OpenAI API Error")

    return side_effect


@pytest.fixture
def mock_slack_error():
    """Mock Slack API error for testing error handling."""

    def side_effect(*args, **kwargs):
        raise Exception("Slack API Error")

    return side_effect


@pytest.fixture
def mock_database_error():
    """Mock database error for testing error handling."""

    def side_effect(*args, **kwargs):
        raise Exception("Database Error")

    return side_effect
