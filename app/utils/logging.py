import logging
import sys
from typing import Optional
from app.config import Config


def setup_logging(
    level: Optional[str] = None, format_string: Optional[str] = None
) -> logging.Logger:
    """Set up application logging configuration."""

    # Use config level if not provided
    if level is None:
        level = Config.LOG_LEVEL

    # Default format
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )

    # Set up root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        stream=sys.stdout,
        force=True,
    )

    # Create application logger
    logger = logging.getLogger("slack_emoji_bot")

    # Set specific log levels for external libraries
    logging.getLogger("slack_bolt").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(f"slack_emoji_bot.{name}")


# Initialize default logger
default_logger = setup_logging()
