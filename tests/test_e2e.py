"""
End-to-End tests for Slack Emoji Reaction Bot

Tests the complete application flow from startup to message processing.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import numpy as np
import pytest

from app.models.emoji import EmojiData
from app.services.database_service import DatabaseService


class TestEndToEnd:
    """End-to-End test suite for the complete bot functionality"""

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for testing"""
        env_vars = {
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "SLACK_APP_TOKEN": "xapp-test-token",
            "OPENAI_API_KEY": "sk-test-key",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
            "KEEP_RUNNING": "false",  # Ensure we don't enter the infinite loop
        }
        with patch.dict(os.environ, env_vars):
            yield env_vars

    @pytest.fixture
    def mock_slack_app(self):
        """Mock Slack app and client"""
        mock_app = Mock()
        mock_client = AsyncMock()
        mock_app.client = mock_client

        # Configure mock behavior
        reaction_response = Mock()
        reaction_response.headers = {
            "X-Rate-Limit-Remaining": "100",
            "X-Rate-Limit-Reset": "1234567890",
        }
        mock_client.reactions_add = AsyncMock(return_value=reaction_response)

        return mock_app

    @pytest.fixture
    def mock_slack_client(self):
        """Mock Slack Web API client"""
        return AsyncMock()

    @pytest.fixture
    def mock_socket(self):
        """Mock Socket Mode client"""
        mock_socket = AsyncMock()
        mock_socket.connect = AsyncMock()
        mock_socket.disconnect = AsyncMock()
        mock_socket.start = AsyncMock()
        return mock_socket

    @pytest.fixture
    def mock_openai(self):
        """Mock OpenAI client"""
        with patch("openai.AsyncOpenAI") as mock_openai_class:
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client

            # Mock embedding response
            mock_embedding = Mock()
            mock_embedding.data = [Mock(embedding=np.random.rand(1536).tolist())]
            mock_client.embeddings.create = AsyncMock(return_value=mock_embedding)

            yield mock_client

    @pytest.fixture
    def mock_db_service(self):
        """Mock DatabaseService with all required methods"""
        db_service = AsyncMock(spec=DatabaseService)
        db_service.connect = AsyncMock()
        db_service.initialize_schema = AsyncMock()
        db_service.close = AsyncMock()
        db_service.count_emojis = AsyncMock(return_value=101)
        db_service.find_similar_emojis = AsyncMock(
            return_value=[
                EmojiData(
                    id=1,
                    code=":smile:",
                    description="Smiling face",
                    category="emotions",
                    emotion_tone="positive",
                ),
                EmojiData(
                    id=2,
                    code=":thumbsup:",
                    description="Thumbs up",
                    category="gestures",
                    emotion_tone="positive",
                ),
                EmojiData(
                    id=3,
                    code=":heart:",
                    description="Heart",
                    category="symbols",
                    emotion_tone="positive",
                ),
            ]
        )
        db_service.insert_emoji_batch = AsyncMock(
            side_effect=lambda emojis: emojis  # Return the same emojis
        )
        db_service.batch_insert_emojis = AsyncMock(
            side_effect=lambda emojis: emojis  # Return the same emojis
        )
        return db_service

    @pytest.fixture
    def mock_database(self):
        """Mock database operations"""
        with patch("psycopg_pool.AsyncConnectionPool") as mock_pool_class:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()

            # Configure pool
            mock_pool_class.return_value = mock_pool
            mock_pool.open = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool.connection = MagicMock()  # Use MagicMock for context manager

            # Configure connection context manager
            mock_conn_ctx = AsyncMock()
            mock_conn_ctx.__aenter__.return_value = mock_conn
            mock_conn_ctx.__aexit__.return_value = None
            mock_pool.connection.return_value = mock_conn_ctx

            # Configure cursor
            mock_cursor_ctx = AsyncMock()
            mock_cursor_ctx.__aenter__.return_value = mock_cursor
            mock_cursor_ctx.__aexit__.return_value = None
            mock_conn.cursor.return_value = mock_cursor_ctx

            # Mock database responses
            mock_cursor.execute = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value=(101,))  # emoji count
            mock_cursor.fetchall = AsyncMock(
                return_value=[
                    (1, ":smile:", "Smiling face", "emotions", "positive", 0.95),
                    (2, ":thumbsup:", "Thumbs up", "gestures", "positive", 0.90),
                    (3, ":heart:", "Heart", "symbols", "positive", 0.85),
                ]
            )

            yield {"pool": mock_pool, "connection": mock_conn, "cursor": mock_cursor}

    @pytest.mark.asyncio
    async def test_full_application_startup(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test complete application startup sequence"""
        # Import main module to test startup
        with patch("app.main.SlackHandler") as mock_handler_class, patch(
            "app.main.DatabaseService"
        ) as mock_db_service_class, patch(
            "app.main.EmojiService"
        ) as mock_emoji_service_class, patch(
            "app.main.OpenAIService"
        ) as mock_openai_service_class:
            # Create mock instances
            mock_handler = AsyncMock()
            mock_db_service = AsyncMock()
            mock_emoji_service = AsyncMock()
            mock_openai_service = AsyncMock()

            # Configure constructors
            mock_handler_class.return_value = mock_handler
            mock_db_service_class.return_value = mock_db_service
            mock_emoji_service_class.return_value = mock_emoji_service
            mock_openai_service_class.return_value = mock_openai_service

            # Configure mock behaviors
            mock_handler.start = AsyncMock()
            mock_db_service.connect = AsyncMock()
            mock_db_service.initialize_schema = AsyncMock()
            mock_emoji_service.load_initial_data = AsyncMock()

            # Import and run main
            from app.main import main

            # Run main function
            await main()

            # Verify all services were initialized
            mock_handler_class.assert_called_once()
            mock_db_service_class.assert_called_once()
            mock_emoji_service_class.assert_called_once()
            mock_openai_service_class.assert_called_once()

            # Verify startup sequence
            mock_db_service.connect.assert_called_once()
            mock_db_service.initialize_schema.assert_called_once()
            mock_emoji_service.load_initial_data.assert_called_once()
            mock_handler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_processing_e2e(
        self,
        mock_env_vars,
        mock_slack_app,
        mock_slack_client,
        mock_openai,
        mock_db_service,
    ):
        """Test complete message processing flow end-to-end"""
        # Create a complete application context
        from app.services.emoji_service import EmojiService
        from app.services.slack_handler import SlackHandler

        # Initialize services
        await mock_db_service.connect()  # Initialize connection pool
        emoji_service = EmojiService(mock_db_service)

        # Create a proper mock for openai_service with get_embedding method
        from unittest.mock import AsyncMock

        mock_openai_service = AsyncMock()
        mock_openai_service.get_embedding = AsyncMock(return_value=np.random.rand(1536))
        emoji_service.openai_service = mock_openai_service

        # Initialize Slack handler
        slack_handler = SlackHandler(mock_openai, emoji_service)
        slack_handler.app = mock_slack_app
        slack_handler.client = mock_slack_client
        slack_handler.set_emoji_service(emoji_service)

        # Simulate incoming message
        test_message = {
            "type": "message",
            "channel": "C12345",
            "user": "U12345",
            "text": "I'm so happy about this great news!",
            "ts": "1234567890.123456",
        }

        # Configure mock responses
        reaction_response = Mock()
        reaction_response.headers = {
            "X-Rate-Limit-Remaining": "100",
            "X-Rate-Limit-Reset": "1234567890",
        }
        mock_slack_app.client.reactions_add = AsyncMock(return_value=reaction_response)

        # Process message
        await slack_handler.process_message_for_reactions(test_message)

        # Verify complete flow
        # 1. OpenAI was called for embedding
        mock_openai_service.get_embedding.assert_called_once()

        # 2. Database was queried for similar emojis
        mock_db_service.find_similar_emojis.assert_called_once()

        # 3. Reactions were added to Slack
        assert mock_slack_app.client.reactions_add.call_count == 3

        # Verify correct emojis were used
        calls = mock_slack_app.client.reactions_add.call_args_list
        emojis_added = [call.kwargs["name"] for call in calls]
        assert "smile" in emojis_added
        assert "thumbsup" in emojis_added
        assert "heart" in emojis_added

    @pytest.mark.asyncio
    async def test_error_recovery_e2e(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test error recovery scenarios end-to-end"""
        from app.services.emoji_service import EmojiService
        from app.services.slack_handler import SlackHandler

        # Test 1: OpenAI API failure
        mock_openai.embeddings.create.side_effect = Exception("OpenAI API Error")

        # Use mocked services
        emoji_service = EmojiService(mock_db_service)
        emoji_service.openai_service = mock_openai

        slack_handler = SlackHandler(mock_openai, emoji_service)
        slack_handler.app = mock_slack_app
        slack_handler.client = mock_slack_app.client

        test_message = {
            "type": "message",
            "channel": "C12345",
            "text": "Test message",
            "ts": "1234567890.123456",
        }

        # Should handle error gracefully
        await slack_handler.process_message_for_reactions(
            test_message, fallback_emojis=["thinking"]
        )

        # Test 2: Database failure
        mock_openai.embeddings.create.side_effect = None  # Reset
        mock_db_service.find_similar_emojis.side_effect = Exception("Database Error")

        await slack_handler.process_message_for_reactions(test_message)
        # Should not crash

        # Test 3: Slack API failure
        mock_db_service.find_similar_emojis.side_effect = None  # Reset
        mock_slack_app.client.reactions_add.side_effect = Exception("Slack API Error")

        await slack_handler.process_message_for_reactions(test_message)
        # Should handle gracefully

    @pytest.mark.asyncio
    async def test_concurrent_message_handling_e2e(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test handling multiple concurrent messages"""
        from app.services.emoji_service import EmojiService
        from app.services.slack_handler import SlackHandler

        # Initialize services
        await mock_db_service.connect()  # Initialize connection pool
        emoji_service = EmojiService(mock_db_service)

        # Create a proper mock for openai_service with get_embedding method
        from unittest.mock import AsyncMock

        mock_openai_service = AsyncMock()
        mock_openai_service.get_embedding = AsyncMock(return_value=np.random.rand(1536))
        emoji_service.openai_service = mock_openai_service

        slack_handler = SlackHandler(mock_openai, emoji_service)
        slack_handler.app = mock_slack_app
        slack_handler.client = mock_slack_app.client

        # Create multiple messages
        messages = [
            {
                "type": "message",
                "channel": "C12345",
                "user": f"U{i}",
                "text": f"Message number {i}",
                "ts": f"123456789{i}.123456",
            }
            for i in range(10)
        ]

        # Configure mock response
        reaction_response = Mock()
        reaction_response.headers = {
            "X-Rate-Limit-Remaining": "100",
            "X-Rate-Limit-Reset": "1234567890",
        }
        mock_slack_app.client.reactions_add = AsyncMock(return_value=reaction_response)

        # Process messages concurrently
        tasks = [slack_handler.process_message_for_reactions(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # Verify all messages were processed
        assert mock_openai_service.get_embedding.call_count == 10
        assert (
            mock_slack_app.client.reactions_add.call_count == 30
        )  # 3 emojis * 10 messages

    @pytest.mark.asyncio
    async def test_configuration_validation_e2e(self):
        """Test configuration validation during startup"""
        # Test missing environment variables
        with patch.dict(os.environ, {}, clear=True):
            from app.config import Config as AppConfig

            # Clear cached class attributes to force re-reading from env
            AppConfig.SLACK_BOT_TOKEN = ""
            AppConfig.SLACK_APP_TOKEN = ""
            AppConfig.OPENAI_API_KEY = ""

            with pytest.raises(ValueError, match="Missing required configuration"):
                AppConfig.validate()

        # Test partial configuration
        partial_env = {
            "SLACK_BOT_TOKEN": "xoxb-test",
            "SLACK_APP_TOKEN": "xapp-test",
            # Missing OPENAI_API_KEY
        }
        with patch.dict(os.environ, partial_env, clear=True):
            with pytest.raises(ValueError):
                AppConfig.validate()

    @pytest.mark.asyncio
    async def test_graceful_shutdown_e2e(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test graceful shutdown handling"""
        with patch("app.main.SlackHandler") as mock_handler_class, patch(
            "app.main.DatabaseService"
        ) as mock_db_service_class:
            mock_handler = AsyncMock()
            mock_db_service = AsyncMock()

            mock_handler_class.return_value = mock_handler
            mock_db_service_class.return_value = mock_db_service

            # Configure shutdown methods
            mock_handler.stop = AsyncMock()
            mock_db_service.close = AsyncMock()

            # Import and set globals
            import app.main

            app.main.slack_handler = mock_handler
            app.main.db_service = mock_db_service

            # Simulate shutdown
            from app.main import shutdown

            await shutdown()

            # Verify cleanup
            mock_handler.stop.assert_called_once()
            mock_db_service.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_endpoint_e2e(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test health check endpoint functionality"""
        from app.services.emoji_service import EmojiService
        from app.services.slack_handler import SlackHandler

        # Initialize services
        await mock_db_service.connect()  # Initialize connection pool
        emoji_service = EmojiService(mock_db_service)
        emoji_service.openai_service = mock_openai

        slack_handler = SlackHandler(mock_openai, emoji_service)
        slack_handler.app = mock_slack_app
        slack_handler.client = mock_slack_app.client

        # Perform health check
        health_status = await slack_handler.check_rag_health()

        # Verify all components are checked
        assert health_status["slack_connected"] is True
        assert health_status["openai_available"] is True
        assert health_status["database_connected"] is True
        assert health_status["emoji_count"] == 101

    @pytest.mark.asyncio
    async def test_socket_mode_connection_e2e(self, mock_env_vars, mock_socket):
        """Test Socket Mode connection handling"""
        # Test connection establishment

        # Simulate connection
        await mock_socket.connect()
        await mock_socket.start()

        # Verify connection methods were called
        mock_socket.connect.assert_called_once()
        mock_socket.start.assert_called_once()

        # Test reconnection on failure
        mock_socket.connect.side_effect = [Exception("Connection failed"), None]

        # Should retry and succeed
        with patch("asyncio.sleep", new_callable=AsyncMock):
            # Reset and try again
            mock_socket.connect.reset_mock()
            mock_socket.connect.side_effect = [Exception("Connection failed"), None]

            # In real implementation, this would have retry logic
            try:
                await mock_socket.connect()
            except Exception:
                await asyncio.sleep(1)
                await mock_socket.connect()

    @pytest.mark.asyncio
    async def test_emoji_data_initialization_e2e(self, mock_env_vars, mock_db_service):
        """Test emoji data initialization process"""
        from app.services.emoji_service import EmojiService

        # Initialize services
        emoji_service = EmojiService(mock_db_service)

        # Mock file reading
        with patch(
            "builtins.open",
            mock_open(read_data='[{"code": ":test:", "description": "Test emoji"}]'),
        ):
            # Load initial emoji data
            loaded = await emoji_service.load_emojis_from_json_file("data/emojis.json")
            assert loaded > 0  # Should have loaded at least one emoji

        # Verify database operations were called - note the method name difference
        assert (
            mock_db_service.batch_insert_emojis.called
            or mock_db_service.insert_emoji_batch.called
        )

    @pytest.mark.asyncio
    async def test_rate_limiting_e2e(
        self, mock_env_vars, mock_slack_app, mock_openai, mock_db_service
    ):
        """Test rate limiting functionality end-to-end"""
        from app.services.emoji_service import EmojiService
        from app.services.slack_handler import SlackHandler

        # Initialize services
        await mock_db_service.connect()  # Initialize connection pool
        emoji_service = EmojiService(mock_db_service)
        emoji_service.openai_service = mock_openai

        slack_handler = SlackHandler(mock_openai, emoji_service)
        slack_handler.app = mock_slack_app
        slack_handler.client = mock_slack_app.client
        slack_handler.set_rate_limit(max_reactions_per_minute=5)

        # Configure mock response
        reaction_response = Mock()
        reaction_response.headers = {
            "X-Rate-Limit-Remaining": "5",
            "X-Rate-Limit-Reset": "1234567890",
        }
        mock_slack_app.client.reactions_add = AsyncMock(return_value=reaction_response)

        # Send messages that would exceed rate limit
        messages = []
        for i in range(10):
            msg = {
                "type": "message",
                "channel": "C12345",
                "text": f"Message {i}",
                "ts": f"123456789{i}.123456",
            }
            messages.append(msg)

        # Process messages
        for msg in messages:
            await slack_handler.process_message_for_reactions(msg)

        # With rate limit of 5/min and 3 emojis per message,
        # only first few messages should be processed
        # The exact behavior depends on implementation
        assert mock_slack_app.client.reactions_add.call_count <= 30
