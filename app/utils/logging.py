import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from functools import wraps
import traceback

from app.config import Config


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Build base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "message",
            ]
        }

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """Enhanced human-readable formatter with color support."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, *args, use_colors: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format with optional color coding."""
        # Add color to level name if using colors
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        formatted = super().format(record)

        # Add extra fields if present
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "message",
            ]
        }

        if extra_fields:
            formatted += f" | Extra: {json.dumps(extra_fields, default=str)}"

        return formatted


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
    use_structured: bool = False,
    use_colors: bool = True,
) -> logging.Logger:
    """Set up application logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for human-readable logs
        use_structured: Whether to use structured JSON logging
        use_colors: Whether to use color coding in human-readable logs
    """
    # Use config level if not provided
    if level is None:
        level = Config.LOG_LEVEL

    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Set formatter
    formatter: logging.Formatter
    if use_structured:
        formatter = StructuredFormatter()
    else:
        if format_string is None:
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
            )
        formatter = HumanReadableFormatter(format_string, use_colors=use_colors)

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(handler)

    # Create application logger
    logger = logging.getLogger("slack_emoji_bot")

    # Set specific log levels for external libraries
    logging.getLogger("slack_bolt").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"slack_emoji_bot.{name}")


class LogContext:
    """Context manager for adding contextual information to logs."""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_adapter = None

    def __enter__(self):
        """Enter context and create adapter with extra fields."""
        self.old_adapter = self.logger
        # Create adapter that adds context to all log messages
        adapter = logging.LoggerAdapter(self.logger, self.context)
        # Replace logger methods
        for method in ["debug", "info", "warning", "error", "critical"]:
            setattr(self.logger, method, getattr(adapter, method))
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original logger."""
        # Restore original logger methods
        for method in ["debug", "info", "warning", "error", "critical"]:
            original_method = getattr(logging.Logger, method)
            setattr(self.logger, method, original_method.__get__(self.logger))


def log_execution_time(logger: Optional[logging.Logger] = None):
    """Decorator to log function execution time."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            _logger = logger or get_logger(func.__module__)

            _logger.debug(
                f"Starting {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                },
            )

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                _logger.info(
                    f"Completed {func.__name__} in {duration:.3f}s",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "status": "success",
                    },
                )

                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()

                _logger.error(
                    f"Failed {func.__name__} after {duration:.3f}s: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": duration,
                        "status": "failed",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                    exc_info=True,
                )
                raise

        return wrapper

    return decorator


class MetricsLogger:
    """Logger for tracking application metrics."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or get_logger("metrics")
        self.metrics: Dict[str, Any] = {}

    def log_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a metric value."""
        metric_data: Dict[str, Any] = {
            "metric_name": metric_name,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "metric",
        }

        if unit:
            metric_data["unit"] = unit

        if tags:
            metric_data["tags"] = tags

        self.logger.info(
            f"Metric: {metric_name}={value}{' ' + unit if unit else ''}",
            extra=metric_data,
        )

        # Store for aggregation
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(metric_data)

    def log_counter(
        self,
        counter_name: str,
        increment: int = 1,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a counter increment."""
        self.log_metric(counter_name, increment, "count", tags)

    def log_gauge(
        self,
        gauge_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a gauge value."""
        self.log_metric(gauge_name, value, "gauge", tags)

    def log_histogram(
        self,
        histogram_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log a histogram value."""
        self.log_metric(histogram_name, value, "histogram", tags)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        summary = {}

        for metric_name, values in self.metrics.items():
            numeric_values = [v["value"] for v in values]
            summary[metric_name] = {
                "count": len(values),
                "sum": sum(numeric_values),
                "min": min(numeric_values) if numeric_values else None,
                "max": max(numeric_values) if numeric_values else None,
                "avg": (
                    sum(numeric_values) / len(numeric_values)
                    if numeric_values
                    else None
                ),
            }

        return summary


# Initialize default logger
default_logger = setup_logging()

# Initialize metrics logger
metrics_logger = MetricsLogger()
