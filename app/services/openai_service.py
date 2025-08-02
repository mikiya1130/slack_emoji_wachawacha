"""
OpenAI Service - Handles text vectorization using OpenAI embeddings
"""

import asyncio
import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from openai import (
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for generating text embeddings using OpenAI API"""

    def __init__(self, api_key: str):
        """
        Initialize OpenAI service

        Args:
            api_key: OpenAI API key

        Raises:
            ValueError: If API key is not provided
        """
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.api_key = api_key
        self.model = "text-embedding-3-small"
        self.dimensions = 1536
        self.max_retries = 3
        self.base_delay = 1.0
        self._client = AsyncOpenAI(api_key=api_key)
        self._cache_enabled = False
        self._cache: Optional[OrderedDict] = None
        self._cache_max_size = 100

    def enable_cache(self, max_size: int = 100):
        """Enable embedding cache with LRU eviction"""
        self._cache_enabled = True
        self._cache_max_size = max_size
        self._cache = OrderedDict()

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text by normalizing whitespace"""
        return " ".join(text.split())

    async def get_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array

        Raises:
            ValueError: If text is empty
            OpenAIError: On API errors
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        processed_text = self._preprocess_text(text)

        # Check cache if enabled
        if self._cache_enabled and self._cache is not None:
            if processed_text in self._cache:
                # Move to end (LRU)
                self._cache.move_to_end(processed_text)
                return self._cache[processed_text].copy()

        # Generate embedding with retry logic
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.embeddings.create(
                    model=self.model, input=processed_text, dimensions=self.dimensions
                )

                embedding = np.array(response.data[0].embedding, dtype=np.float32)

                # Store in cache if enabled
                if self._cache_enabled and self._cache is not None:
                    self._cache[processed_text] = embedding.copy()
                    # Evict oldest if cache is full
                    if len(self._cache) > self._cache_max_size:
                        self._cache.popitem(last=False)

                return embedding

            except RateLimitError as e:
                if attempt == self.max_retries:
                    raise Exception(f"Max retries ({self.max_retries}) exceeded") from e

                # Exponential backoff
                delay = self.base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay)

            except (APIError, AuthenticationError) as e:
                # Don't retry on non-rate-limit errors
                logger.error(f"OpenAI API error: {e}")
                raise

        # This should never be reached
        raise RuntimeError("Unexpected error in get_embedding")

    async def get_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If any text is empty
        """
        if not texts:
            return []

        # Validate all texts
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty")

        # Process all texts
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)

        return embeddings

    async def get_embedding_with_metadata(
        self, text: str
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Generate embedding with metadata

        Args:
            text: Input text

        Returns:
            Tuple of (embedding, metadata)
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        processed_text = self._preprocess_text(text)

        # Generate embedding
        response = await self._client.embeddings.create(
            model=self.model, input=processed_text, dimensions=self.dimensions
        )

        embedding = np.array(response.data[0].embedding, dtype=np.float32)

        metadata = {
            "model": self.model,
            "tokens_used": (
                response.usage.total_tokens if hasattr(response, "usage") else 0
            ),
        }

        return embedding, metadata

    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate embedding dimensions

        Args:
            embedding: Embedding vector

        Returns:
            True if valid, False otherwise
        """
        return (
            isinstance(embedding, np.ndarray)
            and embedding.shape == (self.dimensions,)
            and embedding.dtype == np.float32
        )

    async def health_check(self) -> bool:
        """
        Check if OpenAI service is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to generate a simple embedding
            await self.get_embedding("health check")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
