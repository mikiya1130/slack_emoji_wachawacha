"""
Tests for OpenAI Service
TDD Phase 3 - Task 3.1
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from app.services.openai_service import OpenAIService


class TestOpenAIService:
    """Test suite for OpenAI Service"""

    @pytest.fixture
    def openai_service(self):
        """Create OpenAIService instance"""
        return OpenAIService(api_key="test-api-key")

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        with patch("app.services.openai_service.AsyncOpenAI") as mock_client:
            yield mock_client

    def test_service_initialization(self):
        """Test service initialization with API key"""
        service = OpenAIService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "text-embedding-3-small"
        assert service.dimensions == 1536
        assert service.max_retries == 3
        assert service.base_delay == 1.0

    def test_service_initialization_without_api_key(self):
        """Test service initialization without API key raises error"""
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIService(api_key=None)

    @pytest.mark.asyncio
    async def test_get_embedding_success(self, openai_service, mock_openai_client):
        """Test successful embedding generation"""
        # Mock response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dimensions

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        # Initialize service with mocked client
        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        result = await service.get_embedding("test text")

        assert isinstance(result, np.ndarray)
        assert result.shape == (1536,)
        assert result.dtype == np.float32
        mock_client_instance.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input="test text", dimensions=1536
        )

    @pytest.mark.asyncio
    async def test_get_embedding_empty_text(self, openai_service):
        """Test embedding generation with empty text"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await openai_service.get_embedding("")

    @pytest.mark.asyncio
    async def test_get_embedding_whitespace_text(self, openai_service):
        """Test embedding generation with whitespace-only text"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await openai_service.get_embedding("   ")

    @pytest.mark.asyncio
    async def test_get_embeddings_batch(self, openai_service, mock_openai_client):
        """Test batch embedding generation"""
        # Mock response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3] * 512),  # 1536 dimensions
            Mock(embedding=[0.4, 0.5, 0.6] * 512),
            Mock(embedding=[0.7, 0.8, 0.9] * 512),
        ]

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        texts = ["text1", "text2", "text3"]
        results = await service.get_embeddings_batch(texts)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, np.ndarray)
            assert result.shape == (1536,)
            assert result.dtype == np.float32

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_empty_list(self, openai_service):
        """Test batch embedding with empty list"""
        result = await openai_service.get_embeddings_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_embeddings_batch_with_empty_strings(self, openai_service):
        """Test batch embedding with some empty strings"""
        with pytest.raises(ValueError, match="Text at index 1 cannot be empty"):
            await openai_service.get_embeddings_batch(["text1", "", "text3"])

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self, openai_service, mock_openai_client):
        """Test exponential backoff retry on rate limit error"""
        from openai import RateLimitError

        mock_client_instance = AsyncMock()
        # First two calls raise RateLimitError, third succeeds
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]

        # Create mock response and body for RateLimitError
        mock_http_response = Mock()
        mock_http_response.status_code = 429
        mock_body = {"error": {"message": "Rate limit exceeded"}}

        mock_client_instance.embeddings.create = AsyncMock(
            side_effect=[
                RateLimitError(
                    "Rate limit exceeded", response=mock_http_response, body=mock_body
                ),
                RateLimitError(
                    "Rate limit exceeded", response=mock_http_response, body=mock_body
                ),
                mock_response,
            ]
        )
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance
        service.base_delay = 0.1  # Speed up test

        start_time = time.time()
        result = await service.get_embedding("test text")
        elapsed_time = time.time() - start_time

        assert isinstance(result, np.ndarray)
        assert mock_client_instance.embeddings.create.call_count == 3
        # Should have delays of 0.1 and 0.2 seconds (exponential backoff)
        assert elapsed_time >= 0.3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, openai_service, mock_openai_client):
        """Test max retries exceeded raises error"""
        from openai import RateLimitError

        # Create mock response and body for RateLimitError
        mock_http_response = Mock()
        mock_http_response.status_code = 429
        mock_body = {"error": {"message": "Rate limit exceeded"}}

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded", response=mock_http_response, body=mock_body
            )
        )
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance
        service.base_delay = 0.01  # Speed up test

        with pytest.raises(Exception, match="Max retries .* exceeded"):
            await service.get_embedding("test text")

        assert (
            mock_client_instance.embeddings.create.call_count == 4
        )  # Initial + 3 retries

    @pytest.mark.asyncio
    async def test_api_error_handling(self, openai_service, mock_openai_client):
        """Test handling of general API errors"""
        from openai import APIError

        # Create mock request for APIError
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.openai.com/v1/embeddings"

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(
            side_effect=APIError(
                "API Error",
                request=mock_request,
                body={"error": {"message": "API Error"}},
            )
        )
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        with pytest.raises(APIError):
            await service.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_authentication_error(self, openai_service, mock_openai_client):
        """Test handling of authentication errors"""
        from openai import AuthenticationError

        # Create mock response and body for AuthenticationError
        mock_http_response = Mock()
        mock_http_response.status_code = 401
        mock_body = {"error": {"message": "Invalid API key"}}

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(
            side_effect=AuthenticationError(
                "Invalid API key", response=mock_http_response, body=mock_body
            )
        )
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        with pytest.raises(AuthenticationError):
            await service.get_embedding("test text")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, openai_service, mock_openai_client):
        """Test handling concurrent embedding requests"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        # Create multiple concurrent requests
        tasks = [service.get_embedding(f"text {i}") for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(isinstance(r, np.ndarray) for r in results)
        assert mock_client_instance.embeddings.create.call_count == 5

    @pytest.mark.asyncio
    async def test_text_preprocessing(self, openai_service, mock_openai_client):
        """Test text preprocessing before embedding"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        # Test with text that needs preprocessing
        text_with_extra_spaces = "  Hello   World  \n\t"
        await service.get_embedding(text_with_extra_spaces)

        # Should normalize whitespace
        mock_client_instance.embeddings.create.assert_called_with(
            model="text-embedding-3-small", input="Hello World", dimensions=1536
        )

    @pytest.mark.asyncio
    async def test_embedding_caching(self, openai_service, mock_openai_client):
        """Test embedding caching for repeated texts"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        # Enable caching
        service.enable_cache(max_size=100)

        # First call
        result1 = await service.get_embedding("test text")
        # Second call with same text
        result2 = await service.get_embedding("test text")

        # Should only call API once due to caching
        assert mock_client_instance.embeddings.create.call_count == 1
        assert np.array_equal(result1, result2)

    @pytest.mark.asyncio
    async def test_get_embedding_with_metadata(
        self, openai_service, mock_openai_client
    ):
        """Test embedding generation with metadata tracking"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage = Mock(total_tokens=50)

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        result, metadata = await service.get_embedding_with_metadata("test text")

        assert isinstance(result, np.ndarray)
        assert "tokens_used" in metadata
        assert metadata["tokens_used"] == 50
        assert "model" in metadata
        assert metadata["model"] == "text-embedding-3-small"

    def test_validate_embedding_dimensions(self, openai_service):
        """Test embedding dimension validation"""
        valid_embedding = np.array([0.1] * 1536, dtype=np.float32)
        assert openai_service.validate_embedding(valid_embedding) is True

        invalid_embedding = np.array([0.1] * 1000, dtype=np.float32)
        assert openai_service.validate_embedding(invalid_embedding) is False

    @pytest.mark.asyncio
    async def test_service_health_check(self, openai_service, mock_openai_client):
        """Test service health check"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(return_value=mock_response)
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        is_healthy = await service.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_service_health_check_failure(
        self, openai_service, mock_openai_client
    ):
        """Test service health check on failure"""
        from openai import APIError

        # Create mock request for APIError
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.openai.com/v1/embeddings"

        mock_client_instance = AsyncMock()
        mock_client_instance.embeddings.create = AsyncMock(
            side_effect=APIError(
                "Service unavailable",
                request=mock_request,
                body={"error": {"message": "Service unavailable"}},
            )
        )
        mock_openai_client.return_value = mock_client_instance

        service = OpenAIService(api_key="test-key")
        service._client = mock_client_instance

        is_healthy = await service.health_check()
        assert is_healthy is False
