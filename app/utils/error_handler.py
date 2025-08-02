"""Error handling utilities for the Slack Emoji Bot application."""

import functools
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union
from enum import Enum

from app.utils.logging import get_logger

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels for structured error handling."""

    LOW = "low"  # Minor issues that don't affect core functionality
    MEDIUM = "medium"  # Issues that may affect some features
    HIGH = "high"  # Critical issues that affect core functionality
    CRITICAL = "critical"  # System-breaking issues requiring immediate attention


class ApplicationError(Exception):
    """Base exception class for application-specific errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.severity = severity
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now(timezone.utc)


class ConfigurationError(ApplicationError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            error_code="CONFIG_ERROR",
            details=details,
        )


class ServiceError(ApplicationError):
    """Base class for service-specific errors."""

    pass


class SlackServiceError(ServiceError):
    """Raised when Slack operations fail."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            severity=severity,
            error_code="SLACK_ERROR",
            details=details,
            original_error=original_error,
        )


class OpenAIServiceError(ServiceError):
    """Raised when OpenAI operations fail."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            severity=severity,
            error_code="OPENAI_ERROR",
            details=details,
            original_error=original_error,
        )


class DatabaseError(ServiceError):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            severity=severity,
            error_code="DATABASE_ERROR",
            details=details,
            original_error=original_error,
        )


class ErrorHandler:
    """Centralized error handling and recovery utilities."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("error_handler")
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[Type[Exception], Callable] = {}

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True,
    ) -> None:
        """Log error with structured context."""
        error_info: Dict[str, Any] = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        }

        # Add ApplicationError-specific fields
        if isinstance(error, ApplicationError):
            error_info.update(
                {
                    "severity": error.severity.value,
                    "error_code": error.error_code,
                    "details": error.details,
                    "timestamp": error.timestamp.isoformat(),
                }
            )
            if error.original_error:
                error_info["original_error"] = {
                    "type": type(error.original_error).__name__,
                    "message": str(error.original_error),
                }

        # Track error counts
        error_key = (
            f"{error_info['error_type']}:{error_info.get('error_code', 'UNKNOWN')}"
        )
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        error_info["occurrence_count"] = self.error_counts[error_key]

        # Add traceback if requested
        if include_traceback:
            error_info["traceback"] = traceback.format_exc()

        # Log at appropriate level based on severity
        if isinstance(error, ApplicationError):
            if error.severity == ErrorSeverity.CRITICAL:
                self.logger.critical("Critical error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.HIGH:
                self.logger.error("High severity error occurred", extra=error_info)
            elif error.severity == ErrorSeverity.MEDIUM:
                self.logger.warning("Medium severity error occurred", extra=error_info)
            else:
                self.logger.info("Low severity error occurred", extra=error_info)
        else:
            self.logger.error("Unhandled error occurred", extra=error_info)

    def register_recovery_strategy(
        self, error_type: Type[Exception], strategy: Callable[[Exception], Any]
    ) -> None:
        """Register a recovery strategy for a specific error type."""
        self.recovery_strategies[error_type] = strategy

    def attempt_recovery(self, error: Exception, default_result: Any = None) -> Any:
        """Attempt to recover from an error using registered strategies."""
        for error_type, strategy in self.recovery_strategies.items():
            if isinstance(error, error_type):
                try:
                    self.logger.info(
                        f"Attempting recovery for {type(error).__name__} "
                        f"using strategy {strategy.__name__}"
                    )
                    return strategy(error)
                except Exception as recovery_error:
                    self.logger.error(
                        f"Recovery strategy failed: {recovery_error}", exc_info=True
                    )

        return default_result

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": dict(self.error_counts),
            "total_errors": sum(self.error_counts.values()),
            "error_types": list(
                set(key.split(":")[0] for key in self.error_counts.keys())
            ),
        }


def with_error_handling(
    logger: Optional[logging.Logger] = None,
    default_return: Any = None,
    reraise: bool = True,
    include_traceback: bool = True,
) -> Callable:
    """Decorator for automatic error handling and logging."""

    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, Any]:
            error_handler = ErrorHandler(logger)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error with context
                context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                }
                error_handler.log_error(e, context, include_traceback)

                # Attempt recovery
                recovery_result = error_handler.attempt_recovery(e, default_return)
                if recovery_result is not None:
                    return recovery_result

                # Re-raise if configured
                if reraise:
                    raise

                return default_return

        return wrapper

    return decorator


def create_circuit_breaker(
    failure_threshold: int = 5,
    timeout_seconds: float = 60.0,
    logger: Optional[logging.Logger] = None,
) -> Callable:
    """Create a circuit breaker decorator for preventing cascading failures."""

    class CircuitBreaker:
        def __init__(self):
            self.failure_count = 0
            self.last_failure_time: Optional[datetime] = None
            self.is_open = False
            self.logger = logger or get_logger("circuit_breaker")

        def reset(self) -> None:
            """Reset the circuit breaker."""
            self.failure_count = 0
            self.is_open = False
            self.last_failure_time = None

        def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                # Check if circuit is open
                if self.is_open:
                    if (
                        self.last_failure_time
                        and (
                            datetime.now(timezone.utc) - self.last_failure_time
                        ).total_seconds()
                        > timeout_seconds
                    ):
                        self.logger.info(
                            f"Circuit breaker resetting for {func.__name__}"
                        )
                        self.reset()
                    else:
                        raise ServiceError(
                            f"Circuit breaker is open for {func.__name__}",
                            severity=ErrorSeverity.HIGH,
                            error_code="CIRCUIT_BREAKER_OPEN",
                        )

                try:
                    result = func(*args, **kwargs)
                    # Reset on success
                    if self.failure_count > 0:
                        self.logger.info(
                            f"Circuit breaker recovering for {func.__name__}"
                        )
                    self.failure_count = 0
                    return result
                except Exception:
                    self.failure_count += 1
                    self.last_failure_time = datetime.now(timezone.utc)

                    if self.failure_count >= failure_threshold:
                        self.is_open = True
                        self.logger.error(
                            f"Circuit breaker opened for {func.__name__} "
                            f"after {self.failure_count} failures"
                        )

                    raise

            # Expose reset method on the wrapper
            wrapper.reset = self.reset  # type: ignore[attr-defined]
            return wrapper

    return CircuitBreaker()
