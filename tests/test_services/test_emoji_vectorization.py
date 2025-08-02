"""Tests for emoji vectorization processing"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
import numpy as np

from app.services.emoji_service import EmojiService
from app.services.openai_service import OpenAIService
from app.services.database_service import DatabaseService
from app.models.emoji import EmojiData


class TestEmojiVectorization:
    """Test emoji vectorization functionality"""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service"""
        return AsyncMock(spec=DatabaseService)

    @pytest.fixture
    def mock_openai_service_local(self):
        """Mock OpenAI service"""
        mock = AsyncMock(spec=OpenAIService)
        # Mock embedding generation - use numpy arrays as AsyncMock return values
        mock.get_embedding = AsyncMock(
            return_value=np.array([0.1] * 1536, dtype=np.float32)
        )
        mock.get_embeddings_batch = AsyncMock(
            return_value=[np.array([0.1] * 1536, dtype=np.float32) for _ in range(3)]
        )
        mock.get_embedding_with_metadata = AsyncMock(
            return_value=(
                np.array([0.1] * 1536, dtype=np.float32),
                {"model": "test-model"},
            )
        )
        return mock

    @pytest_asyncio.fixture
    async def emoji_service(self, mock_database_service, mock_openai_service_local):
        """Create EmojiService with mocked dependencies"""
        service = EmojiService(mock_database_service)
        service.openai_service = mock_openai_service_local
        return service

    @pytest.mark.asyncio
    async def test_vectorize_single_emoji(
        self, emoji_service, mock_openai_service_local
    ):
        """Test vectorizing a single emoji"""
        # Create test emoji
        emoji = EmojiData(
            id=1,
            code=":smile:",
            description="Smiling face expressing happiness and joy",
            category="emotions",
            emotion_tone="positive",
            usage_scene="greeting",
        )

        # Call vectorize method (to be implemented)
        result = await emoji_service.vectorize_emoji(emoji)

        # Verify OpenAI service was called with the description
        mock_openai_service_local.get_embedding.assert_called_once_with(
            emoji.description
        )

        # Verify result contains embedding
        assert result is not None
        assert "embedding" in result
        assert len(result["embedding"]) == 1536

    @pytest.mark.asyncio
    async def test_vectorize_emoji_batch(
        self, emoji_service, mock_openai_service_local, mock_database_service
    ):
        """Test vectorizing multiple emojis in batch"""
        # Create test emojis
        emojis = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Smiling face expressing happiness",
                category="emotions",
            ),
            EmojiData(
                id=2,
                code=":thumbsup:",
                description="Thumbs up gesture showing approval",
                category="gestures",
            ),
            EmojiData(
                id=3,
                code=":heart:",
                description="Red heart symbol representing love",
                category="symbols",
            ),
        ]

        # Mock get_all_emojis to return test emojis
        mock_database_service.get_all_emojis.return_value = emojis

        # Call batch vectorize method (to be implemented)
        await emoji_service.vectorize_emojis_batch(batch_size=2)

        # Verify OpenAI service was called with batches
        assert mock_openai_service_local.get_embeddings_batch.call_count > 0

        # Verify database update was called
        assert mock_database_service.batch_update_embeddings.called

    @pytest.mark.asyncio
    async def test_vectorize_emojis_without_embeddings(
        self, emoji_service, mock_database_service
    ):
        """Test vectorizing only emojis without existing embeddings"""
        # Create emojis with and without embeddings
        emojis = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Smiling face",
                embedding=None,  # No embedding
            ),
            EmojiData(
                id=2,
                code=":heart:",
                description="Heart",
                embedding=[0.1] * 1536,  # Has embedding
            ),
            EmojiData(
                id=3,
                code=":thumbsup:",
                description="Thumbs up",
                embedding=None,  # No embedding
            ),
        ]

        mock_database_service.get_all_emojis.return_value = emojis

        # Call vectorize method with skip_existing=True (to be implemented)
        result = await emoji_service.vectorize_all_emojis(skip_existing=True)

        # Verify only emojis without embeddings were processed
        assert result["processed"] == 2
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_vectorize_with_progress_callback(
        self, emoji_service, mock_database_service
    ):
        """Test vectorization with progress callback"""
        progress_updates = []

        def progress_callback(current: int, total: int, emoji_code: str):
            progress_updates.append(
                {"current": current, "total": total, "emoji_code": emoji_code}
            )

        emojis = [
            EmojiData(id=i, code=f":emoji{i}:", description=f"Emoji {i}")
            for i in range(5)
        ]
        mock_database_service.get_all_emojis.return_value = emojis

        # Call vectorize with progress callback (to be implemented)
        await emoji_service.vectorize_all_emojis(progress_callback=progress_callback)

        # Verify progress was reported
        assert len(progress_updates) == 5
        assert progress_updates[-1]["current"] == 5
        assert progress_updates[-1]["total"] == 5

    @pytest.mark.asyncio
    async def test_vectorize_error_handling(
        self, emoji_service, mock_openai_service_local, mock_database_service
    ):
        """Test error handling during vectorization"""
        # Mock OpenAI service to raise error
        mock_openai_service_local.get_embedding.side_effect = Exception("API Error")

        emoji = EmojiData(id=1, code=":error:", description="This will cause an error")

        # Call vectorize and expect error handling
        result = await emoji_service.vectorize_emoji(emoji, skip_on_error=True)

        # Verify error was handled gracefully
        assert result is None or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_vectorize_batch_partial_failure(
        self, emoji_service, mock_openai_service_local, mock_database_service
    ):
        """Test batch vectorization with partial failures"""
        # Mock to fail on second batch
        mock_openai_service_local.get_embeddings_batch.side_effect = [
            [np.random.rand(1536) for _ in range(2)],  # First batch succeeds
            Exception("API Error"),  # Second batch fails
            [np.random.rand(1536) for _ in range(2)],  # Third batch succeeds
        ]

        emojis = [
            EmojiData(id=i, code=f":emoji{i}:", description=f"Emoji {i}")
            for i in range(6)
        ]
        mock_database_service.get_all_emojis.return_value = emojis

        # Call batch vectorize with continue_on_error=True (to be implemented)
        result = await emoji_service.vectorize_emojis_batch(
            batch_size=2, continue_on_error=True
        )

        # Verify partial success
        assert result["successful"] == 4
        assert result["failed"] == 2

    @pytest.mark.asyncio
    async def test_update_emoji_embeddings_in_database(
        self, emoji_service, mock_database_service
    ):
        """Test updating emoji embeddings in database"""
        # Create embedding updates
        embedding_updates = {
            1: [0.1] * 1536,
            2: [0.2] * 1536,
            3: [0.3] * 1536,
        }

        # Call update method (to be implemented)
        result = await emoji_service.update_emoji_embeddings(embedding_updates)

        # Verify database service was called
        mock_database_service.batch_update_embeddings.assert_called_once_with(
            embedding_updates
        )

        # Verify result
        assert result is True

    @pytest.mark.asyncio
    async def test_vectorize_with_custom_model(
        self, emoji_service, mock_openai_service_local
    ):
        """Test vectorization with custom embedding model"""
        emoji = EmojiData(id=1, code=":custom:", description="Custom emoji for testing")

        # Mock custom model embedding
        custom_embedding = np.array([0.1] * 1536, dtype=np.float32)
        mock_openai_service_local.get_embedding_with_metadata.return_value = (
            custom_embedding,
            {
                "model": "text-embedding-3-large",
                "usage": {"prompt_tokens": 10},
            },
        )

        # Call vectorize with custom model (to be implemented)
        result = await emoji_service.vectorize_emoji(
            emoji, model="text-embedding-3-large"
        )

        # Verify custom model was used
        mock_openai_service_local.get_embedding_with_metadata.assert_called_once()
        assert result["model"] == "text-embedding-3-large"

    @pytest.mark.asyncio
    async def test_dry_run_vectorization(self, emoji_service, mock_database_service):
        """Test dry run mode without database updates"""
        emojis = [
            EmojiData(id=i, code=f":emoji{i}:", description=f"Emoji {i}")
            for i in range(3)
        ]
        mock_database_service.get_all_emojis.return_value = emojis

        # Call vectorize in dry run mode (to be implemented)
        result = await emoji_service.vectorize_all_emojis(dry_run=True)

        # Verify embeddings were NOT generated and not saved (dry run)
        assert not emoji_service.openai_service.get_embedding.called
        assert not emoji_service.openai_service.get_embeddings_batch.called
        assert not mock_database_service.batch_update_embeddings.called
        assert result["dry_run"] is True
        assert result["would_process"] == 3

    @pytest.mark.asyncio
    async def test_vectorize_with_filters(self, emoji_service, mock_database_service):
        """Test vectorization with category/emotion filters"""
        emojis = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Smile",
                category="emotions",
                emotion_tone="positive",
            ),
            EmojiData(
                id=2,
                code=":sad:",
                description="Sad",
                category="emotions",
                emotion_tone="negative",
            ),
            EmojiData(
                id=3,
                code=":car:",
                description="Car",
                category="objects",
                emotion_tone="neutral",
            ),
        ]
        mock_database_service.get_all_emojis.return_value = emojis

        # Call vectorize with filters (to be implemented)
        result = await emoji_service.vectorize_all_emojis(
            category="emotions", emotion_tone="positive"
        )

        # Verify only filtered emojis were processed
        assert result["processed"] == 1
        assert result["filtered_out"] == 2
