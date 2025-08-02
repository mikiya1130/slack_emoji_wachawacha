"""
Tests for Vector Similarity Search functionality
TDD Phase 3 - Task 3.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np
import json

from app.services.database_service import DatabaseService
from app.services.emoji_service import EmojiService
from app.models.emoji import EmojiData


class TestVectorSimilaritySearch:
    """Test suite for vector similarity search"""

    def setup_mock_db_connection(self, db_service, mock_results):
        """Helper method to properly mock database connection"""
        # Create a proper mock connection pool
        mock_pool = MagicMock()

        # Create mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall = AsyncMock(return_value=mock_results)
        mock_cursor.execute = AsyncMock()

        # Make cursor an async context manager
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=None)

        # Create mock connection
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Make connection an async context manager
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        # Setup connection pool to return the mock connection as async context manager
        mock_pool_conn_ctx = MagicMock()
        mock_pool_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool_conn_ctx.__aexit__ = AsyncMock(return_value=None)

        # connection() should return the context manager
        mock_pool.connection.return_value = mock_pool_conn_ctx

        # Set the pool on the service
        db_service.connection_pool = mock_pool

        return mock_pool, mock_conn, mock_cursor

    @pytest.fixture
    def mock_emoji_data_with_embeddings(self):
        """Create mock emoji data with embeddings"""
        return [
            EmojiData(
                id=1,
                code=":smile:",
                description="A happy smiling face",
                category="emotions",
                emotion_tone="positive",
                usage_scene="greeting",
                priority=1,
                embedding=[0.1] * 1536,  # Similar vector
            ),
            EmojiData(
                id=2,
                code=":laugh:",
                description="Laughing face with tears of joy",
                category="emotions",
                emotion_tone="positive",
                usage_scene="funny",
                priority=2,
                embedding=[0.11] * 1536,  # Very similar vector
            ),
            EmojiData(
                id=3,
                code=":sad:",
                description="Sad face with tear",
                category="emotions",
                emotion_tone="negative",
                usage_scene="disappointment",
                priority=1,
                embedding=[0.9] * 1536,  # Different vector
            ),
            EmojiData(
                id=4,
                code=":angry:",
                description="Angry red face",
                category="emotions",
                emotion_tone="negative",
                usage_scene="frustration",
                priority=1,
                embedding=[0.8] * 1536,  # Different vector
            ),
            EmojiData(
                id=5,
                code=":heart:",
                description="Red heart symbol",
                category="symbols",
                emotion_tone="positive",
                usage_scene="love",
                priority=3,
                embedding=[0.15] * 1536,  # Somewhat similar vector
            ),
        ]

    @pytest.fixture
    def query_vector(self):
        """Create a query vector for testing"""
        return [0.1] * 1536  # Similar to :smile: emoji

    @pytest.mark.asyncio
    async def test_find_similar_emojis_basic(
        self, mock_emoji_data_with_embeddings, query_vector
    ):
        """Test basic vector similarity search"""
        # This should work with the existing DatabaseService
        db_service = DatabaseService()

        # Mock the query results
        mock_results = [
            (
                1,
                ":smile:",
                "A happy smiling face",
                "emotions",
                "positive",
                "greeting",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.99,
            ),  # High similarity
            (
                2,
                ":laugh:",
                "Laughing face with tears of joy",
                "emotions",
                "positive",
                "funny",
                2,
                json.dumps([0.11] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.95,
            ),  # Good similarity
            (
                5,
                ":heart:",
                "Red heart symbol",
                "symbols",
                "positive",
                "love",
                3,
                json.dumps([0.15] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.85,
            ),  # Lower similarity
        ]

        # Setup mock database connection
        self.setup_mock_db_connection(db_service, mock_results)

        # Execute search
        results = await db_service.find_similar_emojis(query_vector, limit=3)

        # Verify results
        assert len(results) == 3
        assert results[0].code == ":smile:"
        assert results[1].code == ":laugh:"
        assert results[2].code == ":heart:"

        # Check similarity scores are attached
        assert hasattr(results[0], "similarity_score")
        assert results[0].similarity_score == 0.99
        assert results[1].similarity_score == 0.95
        assert results[2].similarity_score == 0.85

    @pytest.mark.asyncio
    async def test_find_similar_emojis_with_filters(self, query_vector):
        """Test vector similarity search with category and emotion filters"""
        db_service = DatabaseService()

        # Mock results filtered by category
        mock_results = [
            (
                1,
                ":smile:",
                "A happy smiling face",
                "emotions",
                "positive",
                "greeting",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.99,
            ),
            (
                2,
                ":laugh:",
                "Laughing face with tears of joy",
                "emotions",
                "positive",
                "funny",
                2,
                json.dumps([0.11] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.95,
            ),
        ]

        # Setup mock database connection
        self.setup_mock_db_connection(db_service, mock_results)

        # Execute search with filters
        filters = {"category": "emotions", "emotion_tone": "positive"}
        results = await db_service.find_similar_emojis(
            query_vector, limit=5, filters=filters
        )

        # Verify filtered results
        assert len(results) == 2
        assert all(emoji.category == "emotions" for emoji in results)
        assert all(emoji.emotion_tone == "positive" for emoji in results)

    @pytest.mark.asyncio
    async def test_find_similar_emojis_empty_results(self, query_vector):
        """Test vector similarity search with no results"""
        db_service = DatabaseService()

        # Mock empty results
        mock_results = []

        # Setup mock database connection
        self.setup_mock_db_connection(db_service, mock_results)

        # Execute search
        results = await db_service.find_similar_emojis(query_vector)

        # Verify empty results
        assert results == []

    @pytest.mark.asyncio
    async def test_find_similar_emojis_invalid_dimension(self):
        """Test vector similarity search with invalid vector dimension"""
        from app.services.database_service import DatabaseOperationError

        db_service = DatabaseService()

        # Create invalid vector (wrong dimension)
        invalid_vector = [0.1] * 1000  # Should be 1536

        # Should raise DatabaseOperationError
        with pytest.raises(DatabaseOperationError, match="Invalid vector dimension"):
            await db_service.find_similar_emojis(invalid_vector)

    @pytest.mark.asyncio
    async def test_find_similar_emojis_ordering(self, query_vector):
        """Test that results are ordered by similarity score descending"""
        db_service = DatabaseService()

        # Mock results with different similarity scores
        mock_results = [
            (
                1,
                ":smile:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.99,
            ),
            (
                2,
                ":laugh:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.95,
            ),
            (
                3,
                ":grin:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.90,
            ),
            (
                4,
                ":joy:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.85,
            ),
        ]

        # Setup mock database connection
        self.setup_mock_db_connection(db_service, mock_results)

        # Execute search
        results = await db_service.find_similar_emojis(query_vector, limit=10)

        # Verify ordering
        assert len(results) == 4
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_emoji_service_search_by_text(self):
        """Test EmojiService search by text functionality"""
        # This requires OpenAI service integration
        from app.services.openai_service import OpenAIService
        from app.services.database_service import DatabaseService

        # Create services
        db_service = DatabaseService()
        db_service.connection_pool = AsyncMock()  # Mock the pool

        emoji_service = EmojiService(database_service=db_service)
        openai_service = OpenAIService(api_key="test-key")

        # Set up services
        emoji_service.openai_service = openai_service

        # Mock OpenAI embedding generation
        mock_embedding = np.array([0.1] * 1536, dtype=np.float32)
        openai_service.get_embedding = AsyncMock(return_value=mock_embedding)

        # Mock database search
        mock_results = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Happy face",
                category="emotions",
                emotion_tone="positive",
            ),
            EmojiData(
                id=2,
                code=":laugh:",
                description="Laughing",
                category="emotions",
                emotion_tone="positive",
            ),
        ]
        for i, emoji in enumerate(mock_results):
            setattr(emoji, "similarity_score", 0.99 - i * 0.05)

        emoji_service._db_service.find_similar_emojis = AsyncMock(
            return_value=mock_results
        )

        # Execute search
        results = await emoji_service.search_by_text("I'm so happy!")

        # Verify
        assert len(results) == 2
        assert results[0].code == ":smile:"
        openai_service.get_embedding.assert_called_once_with("I'm so happy!")
        emoji_service._db_service.find_similar_emojis.assert_called_once()

    @pytest.mark.asyncio
    async def test_emoji_service_search_by_text_empty(self):
        """Test EmojiService search with empty text"""
        from app.services.database_service import DatabaseService

        db_service = DatabaseService()
        db_service.connection_pool = AsyncMock()  # Mock the pool
        emoji_service = EmojiService(database_service=db_service)

        with pytest.raises(ValueError, match="Search text cannot be empty"):
            await emoji_service.search_by_text("")

    @pytest.mark.asyncio
    async def test_emoji_service_search_with_filters(self):
        """Test EmojiService search with category and emotion filters"""
        from app.services.openai_service import OpenAIService
        from app.services.database_service import DatabaseService

        # Create services
        db_service = DatabaseService()
        db_service.connection_pool = AsyncMock()  # Mock the pool

        emoji_service = EmojiService(database_service=db_service)
        openai_service = OpenAIService(api_key="test-key")
        emoji_service.openai_service = openai_service

        # Mock embedding
        mock_embedding = np.array([0.1] * 1536, dtype=np.float32)
        openai_service.get_embedding = AsyncMock(return_value=mock_embedding)

        # Mock filtered results
        mock_results = [
            EmojiData(
                id=1,
                code=":smile:",
                description="Happy",
                category="emotions",
                emotion_tone="positive",
            )
        ]
        setattr(mock_results[0], "similarity_score", 0.95)

        emoji_service._db_service.find_similar_emojis = AsyncMock(
            return_value=mock_results
        )

        # Execute filtered search
        await emoji_service.search_by_text(
            "happy", category="emotions", emotion_tone="positive", limit=5
        )

        # Verify filter parameters were passed
        emoji_service._db_service.find_similar_emojis.assert_called_once()
        call_args = emoji_service._db_service.find_similar_emojis.call_args
        assert call_args[1]["limit"] == 5
        assert call_args[1]["filters"]["category"] == "emotions"
        assert call_args[1]["filters"]["emotion_tone"] == "positive"

    @pytest.mark.asyncio
    async def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation in pgvector"""
        # pgvector uses <=> operator for cosine distance
        # similarity = 1 - cosine_distance

        # Test vectors
        v1 = np.array([1.0, 0.0, 0.0] * 512)  # 1536 dimensions
        v2 = np.array([1.0, 0.0, 0.0] * 512)  # Same vector
        v3 = np.array([0.0, 1.0, 0.0] * 512)  # Orthogonal vector
        v4 = np.array([-1.0, 0.0, 0.0] * 512)  # Opposite vector

        # Normalize vectors (pgvector expects normalized vectors for cosine similarity)
        v1 = v1 / np.linalg.norm(v1)
        v2 = v2 / np.linalg.norm(v2)
        v3 = v3 / np.linalg.norm(v3)
        v4 = v4 / np.linalg.norm(v4)

        # Calculate expected similarities
        # Same vectors should have similarity ~1.0
        similarity_same = 1 - np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        assert abs(similarity_same) < 0.001  # Should be ~0 distance, ~1 similarity

        # Orthogonal vectors should have similarity ~0.5
        similarity_orthogonal = 1 - np.dot(v1, v3) / (
            np.linalg.norm(v1) * np.linalg.norm(v3)
        )
        assert (
            abs(similarity_orthogonal - 1.0) < 0.001
        )  # Should be ~1 distance, ~0 similarity

        # Opposite vectors should have similarity ~0
        similarity_opposite = 1 - np.dot(v1, v4) / (
            np.linalg.norm(v1) * np.linalg.norm(v4)
        )
        assert (
            abs(similarity_opposite - 2.0) < 0.001
        )  # Should be ~2 distance, ~-1 similarity

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, query_vector):
        """Test filtering results by minimum similarity threshold"""
        db_service = DatabaseService()

        # Mock results with various similarity scores
        mock_results = [
            (
                1,
                ":smile:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.95,
            ),
            (
                2,
                ":laugh:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.85,
            ),
            (
                3,
                ":grin:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.75,
            ),
            (
                4,
                ":joy:",
                "desc",
                "cat",
                "positive",
                "scene",
                1,
                json.dumps([0.1] * 1536),
                "2024-01-01",
                "2024-01-01",
                0.65,
            ),
        ]

        # Setup mock database connection
        self.setup_mock_db_connection(db_service, mock_results)

        # Get results and filter by threshold
        results = await db_service.find_similar_emojis(query_vector, limit=10)

        # Filter by minimum similarity of 0.8
        filtered_results = [r for r in results if r.similarity_score >= 0.8]

        assert len(filtered_results) == 2
        assert all(r.similarity_score >= 0.8 for r in filtered_results)

    @pytest.mark.asyncio
    async def test_batch_vector_search(self):
        """Test batch vector search for multiple queries"""
        from app.services.database_service import DatabaseService

        # Create services
        db_service = DatabaseService()
        db_service.connection_pool = AsyncMock()  # Mock the pool

        emoji_service = EmojiService(database_service=db_service)
        from app.services.openai_service import OpenAIService

        openai_service = OpenAIService(api_key="test-key")
        emoji_service.openai_service = openai_service

        # Mock batch embeddings
        mock_embeddings = [
            np.array([0.1] * 1536, dtype=np.float32),
            np.array([0.2] * 1536, dtype=np.float32),
            np.array([0.3] * 1536, dtype=np.float32),
        ]
        openai_service.get_embeddings_batch = AsyncMock(return_value=mock_embeddings)

        # Mock search results for each query
        mock_results = [
            [EmojiData(id=1, code=":smile:", description="Happy")],
            [EmojiData(id=2, code=":laugh:", description="Funny")],
            [EmojiData(id=3, code=":heart:", description="Love")],
        ]

        emoji_service._db_service.find_similar_emojis = AsyncMock(
            side_effect=mock_results
        )

        # Execute batch search
        texts = ["I'm happy", "That's funny", "I love it"]
        batch_results = await emoji_service.search_batch(texts, limit=1)

        # Verify
        assert len(batch_results) == 3
        assert batch_results[0][0].code == ":smile:"
        assert batch_results[1][0].code == ":laugh:"
        assert batch_results[2][0].code == ":heart:"

        openai_service.get_embeddings_batch.assert_called_once_with(texts)
