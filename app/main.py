#!/usr/bin/env python3
"""
Slack Emoji Reaction Bot - Main Entry Point

This module serves as the main entry point for the Slack Emoji Bot application.
It initializes the configuration, logging, and starts the Slack Bolt application.
"""

import asyncio
from app.config import Config
from app.utils.logging import get_logger

logger = get_logger("main")


async def main():
    """Main application entry point."""
    logger.info("Starting Slack Emoji Reaction Bot...")

    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validation successful")

        # TODO: Initialize services in Phase 1+
        # - SlackHandler (Phase 1)
        # - DatabaseService (Phase 2)
        # - EmojiService (Phase 2)
        # - OpenAIService (Phase 3)

        logger.info("Bot initialized successfully")

        # TODO: Start Slack Bolt app in Phase 1
        logger.info("Slack Emoji Bot is ready!")

        # Keep container running for testing/development
        import os

        if os.getenv("KEEP_RUNNING", "false").lower() == "true":
            logger.info("Keeping container running for testing...")
            while True:
                await asyncio.sleep(60)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
