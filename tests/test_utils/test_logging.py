"""Tests for enhanced logging utilities."""

import json
import logging
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from app.utils.logging import (
    StructuredFormatter,
    HumanReadableFormatter,
    setup_logging,
    get_logger,
    LogContext,
    log_execution_time,
    MetricsLogger,
)


class TestStructuredFormatter:
    """Test StructuredFormatter class."""

    def test_basic_formatting(self):
        """Test basic JSON formatting."""
        formatter = StructuredFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Format and parse
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify structure
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        assert "thread" in log_data
        assert "process" in log_data

    def test_exception_formatting(self):
        """Test formatting with exception info."""
        formatter = StructuredFormatter()

        # Create exception
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        # Create log record with exception
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        # Format and parse
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify exception data
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test error"
        assert isinstance(log_data["exception"]["traceback"], list)

    def test_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = StructuredFormatter()

        # Create log record with extra fields
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.request_id = "abc-123"

        # Format and parse
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Verify extra fields
        assert "extra" in log_data
        assert log_data["extra"]["user_id"] == 123
        assert log_data["extra"]["request_id"] == "abc-123"


class TestHumanReadableFormatter:
    """Test HumanReadableFormatter class."""

    def test_basic_formatting(self):
        """Test basic human-readable formatting."""
        formatter = HumanReadableFormatter(
            "%(levelname)s - %(message)s", use_colors=False
        )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # The formatter adds extra fields, so check the base message
        assert formatted.startswith("INFO - Test message")

    def test_color_formatting(self):
        """Test formatting with colors."""
        formatter = HumanReadableFormatter(
            "%(levelname)s - %(message)s", use_colors=True
        )

        # Mock isatty to return True
        with patch("sys.stdout.isatty", return_value=True):
            formatter = HumanReadableFormatter(
                "%(levelname)s - %(message)s", use_colors=True
            )

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # Should contain ANSI color codes
        assert "\033[31m" in formatted  # Red for ERROR
        assert "\033[0m" in formatted  # Reset

    def test_extra_fields_formatting(self):
        """Test formatting with extra fields."""
        formatter = HumanReadableFormatter("%(message)s", use_colors=False)

        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.user_id = 123
        record.action = "test_action"

        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "Extra:" in formatted
        assert '"user_id": 123' in formatted
        assert '"action": "test_action"' in formatted


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_with_defaults(self):
        """Test setup with default parameters."""
        logger = setup_logging()

        assert logger.name == "slack_emoji_bot"
        # Check effective level (logger inherits from root)
        assert logger.getEffectiveLevel() == logging.INFO  # Default from Config

    def test_setup_with_structured_logging(self):
        """Test setup with structured logging."""
        # Capture log output
        stream = StringIO()
        with patch("sys.stdout", stream):
            logger = setup_logging(level="DEBUG", use_structured=True)

            logger.info("Test message", extra={"key": "value"})

            # Get output and parse JSON
            output = stream.getvalue()
            log_data = json.loads(output.strip())

            assert log_data["level"] == "INFO"
            assert log_data["message"] == "Test message"
            assert log_data["extra"]["key"] == "value"

    def test_external_library_log_levels(self):
        """Test that external library log levels are set correctly."""
        setup_logging()

        assert logging.getLogger("slack_bolt").level == logging.WARNING
        assert logging.getLogger("openai").level == logging.WARNING
        assert logging.getLogger("psycopg").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("asyncio").level == logging.WARNING


class TestLogContext:
    """Test LogContext context manager."""

    def test_log_context_adds_extra_fields(self):
        """Test that LogContext adds extra fields to logs."""
        logger = get_logger("test")

        # Capture log output
        handler = logging.StreamHandler(StringIO())
        formatter = HumanReadableFormatter("%(message)s", use_colors=False)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Use LogContext
        with LogContext(logger, user_id=123, request_id="abc"):
            logger.info("Test message")
            output = handler.stream.getvalue()

        # Context should be included
        assert "Test message" in output
        assert "Extra:" in output
        assert "user_id" in output
        assert "request_id" in output


class TestLogExecutionTime:
    """Test log_execution_time decorator."""

    def test_successful_execution(self):
        """Test decorator with successful function execution."""
        mock_logger = MagicMock()

        @log_execution_time(logger=mock_logger)
        def test_func(x, y):
            return x + y

        result = test_func(2, 3)

        assert result == 5

        # Check debug and info logs were called
        assert mock_logger.debug.called
        assert mock_logger.info.called

        # Check log messages
        debug_call = mock_logger.debug.call_args
        assert "Starting test_func" in debug_call[0][0]

        info_call = mock_logger.info.call_args
        assert "Completed test_func" in info_call[0][0]
        assert "duration_seconds" in info_call[1]["extra"]
        assert info_call[1]["extra"]["status"] == "success"

    def test_failed_execution(self):
        """Test decorator with function that raises exception."""
        mock_logger = MagicMock()

        @log_execution_time(logger=mock_logger)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

        # Check debug and error logs were called
        assert mock_logger.debug.called
        assert mock_logger.error.called

        # Check error log
        error_call = mock_logger.error.call_args
        assert "Failed failing_func" in error_call[0][0]
        assert error_call[1]["extra"]["status"] == "failed"
        assert error_call[1]["extra"]["error_type"] == "ValueError"


class TestMetricsLogger:
    """Test MetricsLogger class."""

    def test_log_metric(self):
        """Test logging a basic metric."""
        mock_logger = MagicMock()
        metrics = MetricsLogger(logger=mock_logger)

        metrics.log_metric("response_time", 1.5, "seconds", {"endpoint": "/api"})

        # Check log was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args

        assert "Metric: response_time=1.5 seconds" in call_args[0][0]
        extra = call_args[1]["extra"]
        assert extra["metric_name"] == "response_time"
        assert extra["value"] == 1.5
        assert extra["unit"] == "seconds"
        assert extra["tags"] == {"endpoint": "/api"}

    def test_log_counter(self):
        """Test logging a counter."""
        mock_logger = MagicMock()
        metrics = MetricsLogger(logger=mock_logger)

        metrics.log_counter("api_calls", 1, {"method": "GET"})

        call_args = mock_logger.info.call_args
        assert "Metric: api_calls=1 count" in call_args[0][0]

    def test_log_gauge(self):
        """Test logging a gauge."""
        mock_logger = MagicMock()
        metrics = MetricsLogger(logger=mock_logger)

        metrics.log_gauge("memory_usage", 75.5)

        call_args = mock_logger.info.call_args
        assert "Metric: memory_usage=75.5 gauge" in call_args[0][0]

    def test_metrics_summary(self):
        """Test getting metrics summary."""
        metrics = MetricsLogger()

        # Log some metrics
        metrics.log_metric("response_time", 1.0)
        metrics.log_metric("response_time", 2.0)
        metrics.log_metric("response_time", 3.0)
        metrics.log_counter("errors", 1)
        metrics.log_counter("errors", 1)

        summary = metrics.get_metrics_summary()

        # Check response_time summary
        assert summary["response_time"]["count"] == 3
        assert summary["response_time"]["sum"] == 6.0
        assert summary["response_time"]["min"] == 1.0
        assert summary["response_time"]["max"] == 3.0
        assert summary["response_time"]["avg"] == 2.0

        # Check errors summary
        assert summary["errors"]["count"] == 2
        assert summary["errors"]["sum"] == 2
