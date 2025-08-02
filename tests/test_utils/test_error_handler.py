"""Tests for error handling utilities."""

import pytest
import logging
from datetime import datetime
from unittest.mock import MagicMock

from app.utils.error_handler import (
    ErrorSeverity,
    ApplicationError,
    ConfigurationError,
    ServiceError,
    SlackServiceError,
    OpenAIServiceError,
    DatabaseError,
    ErrorHandler,
    with_error_handling,
    create_circuit_breaker,
)


class TestApplicationError:
    """Test ApplicationError base class."""

    def test_application_error_initialization(self):
        """Test ApplicationError initialization with all parameters."""
        original_error = ValueError("Original error")
        error = ApplicationError(
            message="Test error",
            severity=ErrorSeverity.HIGH,
            error_code="TEST_ERROR",
            details={"key": "value"},
            original_error=original_error,
        )

        assert str(error) == "Test error"
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"key": "value"}
        assert error.original_error == original_error
        assert isinstance(error.timestamp, datetime)

    def test_application_error_defaults(self):
        """Test ApplicationError with default values."""
        error = ApplicationError("Test error")

        assert error.severity == ErrorSeverity.MEDIUM
        assert error.error_code == "ApplicationError"
        assert error.details == {}
        assert error.original_error is None


class TestSpecificErrors:
    """Test specific error classes."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Missing config", details={"missing_key": "API_KEY"})

        assert str(error) == "Missing config"
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.error_code == "CONFIG_ERROR"
        assert error.details == {"missing_key": "API_KEY"}

    def test_slack_service_error(self):
        """Test SlackServiceError."""
        original = Exception("Slack API error")
        error = SlackServiceError(
            "Failed to post message",
            severity=ErrorSeverity.HIGH,
            details={"channel": "#test"},
            original_error=original,
        )

        assert str(error) == "Failed to post message"
        assert error.error_code == "SLACK_ERROR"
        assert error.original_error == original

    def test_openai_service_error(self):
        """Test OpenAIServiceError."""
        error = OpenAIServiceError("Rate limit exceeded", details={"retry_after": 60})

        assert str(error) == "Rate limit exceeded"
        assert error.error_code == "OPENAI_ERROR"

    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError(
            "Connection failed", details={"host": "localhost", "port": 5432}
        )

        assert str(error) == "Connection failed"
        assert error.severity == ErrorSeverity.HIGH
        assert error.error_code == "DATABASE_ERROR"


class TestErrorHandler:
    """Test ErrorHandler class."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def error_handler(self, mock_logger):
        """Create an ErrorHandler instance."""
        return ErrorHandler(logger=mock_logger)

    def test_log_error_with_application_error(self, error_handler, mock_logger):
        """Test logging ApplicationError."""
        error = ApplicationError(
            "Test error",
            severity=ErrorSeverity.HIGH,
            error_code="TEST_001",
            details={"user_id": 123},
        )

        error_handler.log_error(error, context={"action": "test"})

        # Check that error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "High severity error occurred" in call_args[0]

        # Check logged data
        extra = call_args[1]["extra"]
        assert extra["error_type"] == "ApplicationError"
        assert extra["error_message"] == "Test error"
        assert extra["severity"] == "high"
        assert extra["error_code"] == "TEST_001"
        assert extra["details"] == {"user_id": 123}
        assert extra["context"] == {"action": "test"}
        assert extra["occurrence_count"] == 1
        assert "traceback" in extra

    def test_log_error_severity_levels(self, error_handler, mock_logger):
        """Test logging with different severity levels."""
        # Critical
        error = ApplicationError("Critical", severity=ErrorSeverity.CRITICAL)
        error_handler.log_error(error)
        mock_logger.critical.assert_called_once()

        # High
        error = ApplicationError("High", severity=ErrorSeverity.HIGH)
        error_handler.log_error(error)
        mock_logger.error.assert_called_once()

        # Medium
        error = ApplicationError("Medium", severity=ErrorSeverity.MEDIUM)
        error_handler.log_error(error)
        mock_logger.warning.assert_called_once()

        # Low
        error = ApplicationError("Low", severity=ErrorSeverity.LOW)
        error_handler.log_error(error)
        mock_logger.info.assert_called_once()

    def test_log_error_with_standard_exception(self, error_handler, mock_logger):
        """Test logging standard Python exception."""
        error = ValueError("Invalid value")
        error_handler.log_error(error)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        extra = call_args[1]["extra"]
        assert extra["error_type"] == "ValueError"
        assert extra["error_message"] == "Invalid value"

    def test_error_counting(self, error_handler):
        """Test error occurrence counting."""
        error1 = ApplicationError("Error 1", error_code="ERR_001")
        error2 = ApplicationError("Error 2", error_code="ERR_001")
        error3 = ApplicationError("Error 3", error_code="ERR_002")

        error_handler.log_error(error1)
        error_handler.log_error(error2)
        error_handler.log_error(error3)

        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == 3
        assert stats["error_counts"]["ApplicationError:ERR_001"] == 2
        assert stats["error_counts"]["ApplicationError:ERR_002"] == 1

    def test_recovery_strategy(self, error_handler):
        """Test error recovery strategies."""

        # Register recovery strategy
        def recover_from_value_error(error):
            return "recovered"

        error_handler.register_recovery_strategy(ValueError, recover_from_value_error)

        # Test recovery
        result = error_handler.attempt_recovery(ValueError("test"))
        assert result == "recovered"

        # Test no recovery for unregistered error
        result = error_handler.attempt_recovery(
            TypeError("test"), default_result="default"
        )
        assert result == "default"

    def test_recovery_strategy_failure(self, error_handler, mock_logger):
        """Test recovery strategy that fails."""

        def failing_recovery(error):
            raise RuntimeError("Recovery failed")

        error_handler.register_recovery_strategy(ValueError, failing_recovery)

        result = error_handler.attempt_recovery(
            ValueError("test"), default_result="default"
        )
        assert result == "default"
        mock_logger.error.assert_called_with(
            "Recovery strategy failed: Recovery failed", exc_info=True
        )


class TestErrorHandlingDecorator:
    """Test with_error_handling decorator."""

    def test_successful_function(self):
        """Test decorator with successful function."""

        @with_error_handling(reraise=False)
        def successful_func(x, y):
            return x + y

        result = successful_func(2, 3)
        assert result == 5

    def test_function_with_error_reraise(self):
        """Test decorator with error and reraise=True."""
        mock_logger = MagicMock()

        @with_error_handling(logger=mock_logger, reraise=True)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        # Check that error was logged
        assert mock_logger.error.called

    def test_function_with_error_no_reraise(self):
        """Test decorator with error and reraise=False."""

        @with_error_handling(reraise=False, default_return="default")
        def failing_func():
            raise ValueError("Test error")

        result = failing_func()
        assert result == "default"

    def test_function_with_recovery(self):
        """Test decorator with recovery strategy."""
        mock_logger = MagicMock()

        @with_error_handling(
            logger=mock_logger, reraise=False, default_return="default"
        )
        def func_with_recovery():
            raise ValueError("Test error")

        # This should use default since no recovery is registered
        result = func_with_recovery()
        assert result == "default"


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        circuit_breaker = create_circuit_breaker(
            failure_threshold=3, timeout_seconds=60
        )

        @circuit_breaker
        def successful_func(x):
            return x * 2

        # Multiple successful calls
        assert successful_func(5) == 10
        assert successful_func(3) == 6
        assert successful_func(7) == 14

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        circuit_breaker = create_circuit_breaker(
            failure_threshold=3, timeout_seconds=60
        )

        call_count = 0

        @circuit_breaker
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        # First few failures
        for i in range(3):
            with pytest.raises(ValueError):
                failing_func()

        # Circuit should be open now
        with pytest.raises(ServiceError, match="Circuit breaker is open"):
            failing_func()

        # Function shouldn't be called when circuit is open
        assert call_count == 3

    def test_circuit_breaker_reset_after_timeout(self):
        """Test circuit breaker resets after timeout."""
        circuit_breaker = create_circuit_breaker(
            failure_threshold=2, timeout_seconds=0.1  # 100ms for testing
        )

        @circuit_breaker
        def sometimes_failing_func(should_fail):
            if should_fail:
                raise ValueError("Test error")
            return "success"

        # Cause circuit to open
        for _ in range(2):
            with pytest.raises(ValueError):
                sometimes_failing_func(True)

        # Circuit is open
        with pytest.raises(ServiceError, match="Circuit breaker is open"):
            sometimes_failing_func(False)

        # Wait for timeout
        import time

        time.sleep(0.2)

        # Circuit should reset and allow calls
        result = sometimes_failing_func(False)
        assert result == "success"

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery on successful calls."""
        circuit_breaker = create_circuit_breaker(
            failure_threshold=3, timeout_seconds=60
        )

        fail_next = True

        @circuit_breaker
        def intermittent_func():
            nonlocal fail_next
            if fail_next:
                fail_next = False
                raise ValueError("Test error")
            fail_next = True
            return "success"

        # Some failures but not reaching threshold
        with pytest.raises(ValueError):
            intermittent_func()

        # Success resets counter
        assert intermittent_func() == "success"

        # Can fail again without opening circuit
        with pytest.raises(ValueError):
            intermittent_func()

        assert intermittent_func() == "success"

    def test_manual_circuit_reset(self):
        """Test manual circuit breaker reset."""
        circuit_breaker = create_circuit_breaker(
            failure_threshold=2, timeout_seconds=3600  # 1 hour
        )

        @circuit_breaker
        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                failing_func()

        # Circuit is open
        with pytest.raises(ServiceError):
            failing_func()

        # Manual reset
        failing_func.reset()

        # Can fail again
        with pytest.raises(ValueError):
            failing_func()
