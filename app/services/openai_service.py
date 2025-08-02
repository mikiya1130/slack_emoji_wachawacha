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

from app.utils.logging import log_execution_time, LogContext, metrics_logger
from app.utils.error_handler import (
    with_error_handling,
    create_circuit_breaker,
    ErrorSeverity,
    ErrorHandler,
    ApplicationError,
)

logger = logging.getLogger(__name__)


class OpenAIServiceError(ApplicationError):
    """OpenAI service specific error"""

    pass


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

        # Error handling setup
        self.error_handler = ErrorHandler(logger)
        self._register_recovery_strategies()

    def enable_cache(self, max_size: int = 100):
        """Enable embedding cache with LRU eviction"""
        self._cache_enabled = True
        self._cache_max_size = max_size
        self._cache = OrderedDict()

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text by normalizing whitespace"""
        return " ".join(text.split())

    @with_error_handling(logger=logger, reraise=True)
    @log_execution_time(logger)
    async def get_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array

        Raises:
            ValueError: If text is empty
            OpenAIServiceError: On API errors
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        processed_text = self._preprocess_text(text)

        with LogContext(logger, text_length=len(text), text_preview=text[:50]):
            # Check cache if enabled
            if self._cache_enabled and self._cache is not None:
                if processed_text in self._cache:
                    logger.debug("Cache hit for embedding")
                    metrics_logger.log_counter("embedding_cache_hits")
                    # Move to end (LRU)
                    self._cache.move_to_end(processed_text)
                    return self._cache[processed_text].copy()

            if self._cache_enabled:
                metrics_logger.log_counter("embedding_cache_misses")

            # Generate embedding with retry logic
            embedding = await self._get_embedding_with_circuit_breaker(processed_text)

            # Store in cache if enabled
            if self._cache_enabled and self._cache is not None:
                self._cache[processed_text] = embedding.copy()
                # Evict oldest if cache is full
                if len(self._cache) > self._cache_max_size:
                    self._cache.popitem(last=False)
                    metrics_logger.log_counter("embedding_cache_evictions")

            return embedding

    @create_circuit_breaker(failure_threshold=3, timeout_seconds=60, logger=logger)
    async def _get_embedding_with_circuit_breaker(self, text: str) -> np.ndarray:
        """Get embedding with circuit breaker protection"""
        for attempt in range(self.max_retries + 1):
            try:
                # Track API call
                metrics_logger.log_counter(
                    "openai_api_calls", tags={"method": "embeddings"}
                )

                response = await self._client.embeddings.create(
                    model=self.model, input=text, dimensions=self.dimensions
                )

                embedding = np.array(response.data[0].embedding, dtype=np.float32)

                # Track success
                metrics_logger.log_counter(
                    "openai_api_success", tags={"method": "embeddings"}
                )

                if attempt > 0:
                    logger.info(
                        f"Successfully generated embedding after {attempt} retries"
                    )

                return embedding

            except RateLimitError as e:
                metrics_logger.log_counter("openai_rate_limits")

                if attempt == self.max_retries:
                    raise OpenAIServiceError(
                        f"Rate limit exceeded after {self.max_retries} retries",
                        severity=ErrorSeverity.HIGH,
                        details={"max_retries": self.max_retries},
                        original_error=e,
                    )

                # Exponential backoff
                delay = self.base_delay * (2**attempt)
                logger.warning(
                    f"Rate limit hit, retrying in {delay}s "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                await asyncio.sleep(delay)

            except AuthenticationError as e:
                # Don't retry auth errors
                metrics_logger.log_counter("openai_auth_errors")
                raise OpenAIServiceError(
                    "OpenAI authentication failed",
                    severity=ErrorSeverity.CRITICAL,
                    details={"api_key_prefix": self.api_key[:8] + "..."},
                    original_error=e,
                )

            except APIError as e:
                metrics_logger.log_counter("openai_api_errors")

                if attempt == self.max_retries:
                    raise OpenAIServiceError(
                        f"OpenAI API error after {self.max_retries} retries",
                        severity=ErrorSeverity.HIGH,
                        details={"error_type": type(e).__name__},
                        original_error=e,
                    )

                logger.warning(
                    f"API error, retrying (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.base_delay)

        # This should never be reached
        raise OpenAIServiceError(
            "Unexpected error in get_embedding", severity=ErrorSeverity.CRITICAL
        )

    @with_error_handling(logger=logger, reraise=True)
    @log_execution_time(logger)
    async def get_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors

        Raises:
            ValueError: If any text is empty
            OpenAIServiceError: If batch processing fails
        """
        if not texts:
            return []

        with LogContext(logger, batch_size=len(texts)):
            # Validate all texts
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    raise ValueError(f"Text at index {i} cannot be empty")

            # Process all texts
            embeddings = []
            successful = 0
            failed = 0

            for i, text in enumerate(texts):
                try:
                    embedding = await self.get_embedding(text)
                    embeddings.append(embedding)
                    successful += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to embed text at index {i}: {e}")

                    # For batch operations, we might want to continue
                    # but still track the error
                    self.error_handler.log_error(
                        e, {"batch_index": i, "text_preview": text[:50]}
                    )

                    # Re-raise if too many failures
                    if failed > len(texts) * 0.5:  # More than 50% failed
                        raise OpenAIServiceError(
                            f"Batch embedding failed: {failed}/{len(texts)} texts failed",
                            severity=ErrorSeverity.HIGH,
                            details={"successful": successful, "failed": failed},
                        )

                    # Add zero embedding as placeholder
                    embeddings.append(np.zeros(self.dimensions, dtype=np.float32))

            if failed > 0:
                logger.warning(
                    f"Batch completed with {failed} failures out of {len(texts)} texts"
                )

            metrics_logger.log_gauge(
                "batch_success_rate", successful / len(texts) * 100
            )

            return embeddings

    @with_error_handling(logger=logger, reraise=True)
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

        try:
            # Generate embedding using circuit breaker protected method
            embedding = await self._get_embedding_with_circuit_breaker(processed_text)

            # Get basic metadata
            metadata = {
                "model": self.model,
                "dimensions": self.dimensions,
                "text_length": len(text),
                "processed_text_length": len(processed_text),
            }

            return embedding, metadata

        except Exception as e:
            raise OpenAIServiceError(
                "Failed to generate embedding with metadata",
                severity=ErrorSeverity.MEDIUM,
                details={"text_length": len(text)},
                original_error=e,
            )

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

    @with_error_handling(logger=logger, reraise=False, default_return=False)
    async def health_check(self) -> bool:
        """
        Check if OpenAI service is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to generate a simple embedding
            await self.get_embedding("health check")
            metrics_logger.log_counter(
                "health_checks_passed", tags={"service": "openai"}
            )
            return True
        except Exception as e:
            metrics_logger.log_counter(
                "health_checks_failed", tags={"service": "openai"}
            )
            self.error_handler.log_error(e, {"action": "health_check"})
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache_enabled or self._cache is None:
            return {"enabled": False, "size": 0, "max_size": self._cache_max_size}

        return {
            "enabled": True,
            "size": len(self._cache),
            "max_size": self._cache_max_size,
            "hit_rate": self._calculate_cache_hit_rate(),
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from metrics"""
        global_metrics = metrics_logger.get_metrics_summary()
        hits = global_metrics.get("embedding_cache_hits", {}).get("sum", 0)
        misses = global_metrics.get("embedding_cache_misses", {}).get("sum", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        cache_stats = self.get_cache_stats()
        error_stats = self.error_handler.get_error_statistics()
        global_metrics = metrics_logger.get_metrics_summary()

        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "cache_stats": cache_stats,
            "error_statistics": error_stats,
            "api_metrics": {
                k: v for k, v in global_metrics.items() if k.startswith("openai_")
            },
            "configuration": {
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
            },
        }

    def _register_recovery_strategies(self) -> None:
        """Register error recovery strategies"""

        def recover_from_rate_limit(error: Exception) -> Any:
            """Recovery strategy for rate limit errors"""
            if (
                isinstance(error, OpenAIServiceError)
                and "rate_limit" in str(error).lower()
            ):
                logger.info("Implementing rate limit recovery with increased delays")
                # Increase base delay for future requests
                self.base_delay = min(self.base_delay * 1.5, 10.0)
            return None

        self.error_handler.register_recovery_strategy(
            OpenAIServiceError, recover_from_rate_limit
        )
