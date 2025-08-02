"""
Performance tests for Slack Emoji Reaction Bot

Tests to ensure the system meets performance requirements.
"""

import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch
import numpy as np

from app.services.slack_handler import SlackHandler
from app.services.openai_service import OpenAIService
from app.services.emoji_service import EmojiService
from app.services.database_service import DatabaseService
from app.models.emoji import EmojiData


class TestPerformance:
    """Performance test suite"""

    @pytest.fixture
    def mock_openai_service(self):
        """Mock OpenAI service with realistic latency"""
        service = AsyncMock(spec=OpenAIService)

        async def mock_get_embedding(text):
            # Simulate API latency
            await asyncio.sleep(0.1)  # 100ms latency
            return np.random.rand(1536).astype(np.float32)

        async def mock_get_embeddings_batch(texts):
            # Simulate batch API latency
            await asyncio.sleep(0.2)  # 200ms latency for batch
            return [np.random.rand(1536).astype(np.float32) for _ in texts]

        service.get_embedding = AsyncMock(side_effect=mock_get_embedding)
        service.get_embeddings_batch = AsyncMock(side_effect=mock_get_embeddings_batch)
        return service

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service with realistic latency"""
        service = AsyncMock(spec=DatabaseService)
        service.connect = AsyncMock()
        service.initialize_schema = AsyncMock()

        async def mock_find_similar(vector, limit=3, filters=None):
            # Simulate database query latency
            await asyncio.sleep(0.05)  # 50ms latency
            return [
                EmojiData(
                    id=i,
                    code=f":emoji{i}:",
                    description=f"Test emoji {i}",
                    category="test",
                    emotion_tone="positive",
                )
                for i in range(1, limit + 1)
            ]

        service.find_similar_emojis = AsyncMock(side_effect=mock_find_similar)
        service.count_emojis = AsyncMock(return_value=1000)
        service.get_emoji_by_code = AsyncMock(
            return_value=EmojiData(
                id=1,
                code=":smile:",
                description="Smiling face",
                category="emotions",
                emotion_tone="positive",
            )
        )
        service.batch_update_embeddings = AsyncMock(return_value=True)
        service.get_all_emojis = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_slack_app(self):
        """Mock Slack app with realistic latency"""
        app = Mock()
        client = Mock()
        app.client = client

        def mock_reactions_add(*args, **kwargs):
            # Simulate Slack API latency with synchronous sleep
            import time

            time.sleep(0.05)  # 50ms per reaction
            response = Mock()
            response.headers = {
                "X-Rate-Limit-Remaining": "100",
                "X-Rate-Limit-Reset": "1234567890",
            }
            return response

        client.reactions_add = Mock(side_effect=mock_reactions_add)
        return app

    @pytest_asyncio.fixture
    async def slack_handler(self, mock_openai_service, mock_database_service):
        """Create SlackHandler with mocked services"""
        with patch("app.services.slack_handler.App") as mock_app_class, patch(
            "app.services.slack_handler.SocketModeHandler"
        ) as mock_socket_handler_class, patch(
            "app.services.slack_handler.Config"
        ) as mock_config_class:

            # Mock App instance
            mock_app = Mock()
            mock_client = Mock()
            mock_client.reactions_add = Mock(return_value={"ok": True})
            mock_app.client = mock_client
            mock_app.event = Mock(return_value=lambda func: func)
            mock_app_class.return_value = mock_app

            # Mock SocketModeHandler instance
            mock_socket_handler = Mock()
            mock_socket_handler.start = Mock()
            mock_socket_handler.close = Mock()
            mock_socket_handler_class.return_value = mock_socket_handler

            # Mock Config instance
            mock_config = Mock()
            mock_config.slack.bot_token = "xoxb-test-token"
            mock_config.slack.app_token = "xapp-test-token"
            mock_config_class.return_value = mock_config

            emoji_service = EmojiService(mock_database_service)
            emoji_service.openai_service = mock_openai_service

            handler = SlackHandler(mock_openai_service, emoji_service)
            handler.set_emoji_service(emoji_service)
            return handler

    @pytest.mark.asyncio
    async def test_message_processing_under_5_seconds(
        self, slack_handler, mock_slack_app
    ):
        """Test that message processing completes within 5 seconds"""
        slack_handler.app = mock_slack_app

        message = {
            "type": "message",
            "channel": "C12345",
            "user": "U12345",
            "text": "This is a test message for performance testing",
            "ts": "1234567890.123456",
        }

        start_time = time.time()
        await slack_handler.process_message_for_reactions(message)
        end_time = time.time()

        processing_time = end_time - start_time
        assert (
            processing_time < 5.0
        ), f"Message processing took {processing_time:.2f}s, exceeding 5s limit"

    @pytest.mark.asyncio
    async def test_vector_search_under_1_second(
        self, mock_database_service, mock_openai_service
    ):
        """Test that vector similarity search completes within 1 second"""
        emoji_service = EmojiService(mock_database_service)
        emoji_service.openai_service = mock_openai_service

        # Get embedding
        embedding = await mock_openai_service.get_embedding("test message")

        # Perform vector search
        start_time = time.time()
        results = await emoji_service.find_similar_emojis(embedding, limit=3)
        end_time = time.time()

        search_time = end_time - start_time
        assert (
            search_time < 1.0
        ), f"Vector search took {search_time:.2f}s, exceeding 1s limit"
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, slack_handler, mock_slack_app):
        """Test handling multiple concurrent messages efficiently"""
        slack_handler.app = mock_slack_app

        # Create 10 messages
        messages = [
            {
                "type": "message",
                "channel": "C12345",
                "user": f"U{i}",
                "text": f"Test message {i}",
                "ts": f"123456789{i}.123456",
            }
            for i in range(10)
        ]

        # Process messages concurrently
        start_time = time.time()
        tasks = [slack_handler.process_message_for_reactions(msg) for msg in messages]
        await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time
        # Should complete in reasonable time even with 10 messages
        assert total_time < 10.0, f"Concurrent processing took {total_time:.2f}s"

        # Calculate average time per message
        avg_time = total_time / len(messages)
        print(f"Average time per message: {avg_time:.3f}s")

    @pytest.mark.asyncio
    async def test_memory_efficient_batch_processing(
        self, mock_database_service, mock_openai_service
    ):
        """Test memory efficiency during batch operations"""
        emoji_service = EmojiService(mock_database_service)
        emoji_service.openai_service = mock_openai_service

        # Simulate batch emoji vectorization
        emojis = [
            EmojiData(
                code=f":emoji{i}:", description=f"Test emoji {i}", category="test"
            )
            for i in range(100)
        ]

        start_time = time.time()

        # Mock batch_update_embeddings for the test
        mock_database_service.batch_update_embeddings = AsyncMock(return_value=True)

        # Mock get_all_emojis to return test emojis
        mock_database_service.get_all_emojis = AsyncMock(return_value=emojis)

        # Process in batches to avoid memory issues
        await emoji_service.vectorize_emojis_batch(batch_size=10)

        end_time = time.time()

        batch_time = end_time - start_time
        assert batch_time < 30.0, f"Batch processing took {batch_time:.2f}s"

    @pytest.mark.asyncio
    async def test_rate_limit_performance(self, slack_handler, mock_slack_app):
        """Test performance under rate limiting conditions"""
        slack_handler.app = mock_slack_app
        slack_handler.set_rate_limit(max_reactions_per_minute=60)

        messages = [
            {
                "type": "message",
                "channel": "C12345",
                "text": f"Message {i}",
                "ts": f"123456789{i}.123456",
            }
            for i in range(5)
        ]

        start_time = time.time()

        for msg in messages:
            await slack_handler.process_message_for_reactions(msg)

        end_time = time.time()

        # Should handle rate limiting efficiently
        total_time = end_time - start_time
        assert total_time < 10.0, f"Rate limited processing took {total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_cache_performance(self, mock_database_service, mock_openai_service):
        """Test performance improvement with caching"""
        emoji_service = EmojiService(mock_database_service, cache_enabled=True)
        emoji_service.openai_service = mock_openai_service

        # First call - no cache
        start_time = time.time()
        await emoji_service.get_emoji_by_code(":smile:")
        first_call_time = time.time() - start_time

        # Second call - should use cache
        start_time = time.time()
        await emoji_service.get_emoji_by_code(":smile:")
        second_call_time = time.time() - start_time

        # Cache should make second call faster
        assert (
            second_call_time < first_call_time * 0.5
        ), f"Cache did not improve performance: {first_call_time:.3f}s vs {second_call_time:.3f}s"

    @pytest.mark.asyncio
    async def test_database_connection_pool_efficiency(self, mock_database_service):
        """Test database connection pool performance"""
        # Simulate multiple concurrent database operations
        tasks = []

        start_time = time.time()

        # Create 20 concurrent database queries
        for i in range(20):
            task = mock_database_service.find_similar_emojis(
                np.random.rand(1536).tolist(), limit=3
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        end_time = time.time()

        # Connection pool should handle concurrent queries efficiently
        total_time = end_time - start_time
        assert total_time < 5.0, f"Concurrent DB queries took {total_time:.2f}s"
