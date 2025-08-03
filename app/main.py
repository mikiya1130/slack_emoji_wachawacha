#!/usr/bin/env python3
"""
Slack Emoji Reaction Bot - Main Entry Point

This module serves as the main entry point for the Slack Emoji Bot application.
It initializes the configuration, logging, and starts the Slack Bolt application.
"""

import asyncio
import os
from app.config import Config
from app.utils.logging import get_logger
from app.services.slack_handler import SlackHandler
from app.services.database_service import DatabaseService
from app.services.emoji_service import EmojiService
from app.services.openai_service import OpenAIService
from app.services.slash_command_handler import SlashCommandHandler
from app.utils.permission_manager import PermissionManager

logger = get_logger("main")

# Global references for shutdown
slack_handler = None
db_service = None


async def main():
    """Main application entry point."""
    global slack_handler, db_service

    logger.info("Starting Slack Emoji Reaction Bot...")

    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validation successful")

        # Initialize services
        logger.info("Initializing services...")

        # Initialize database service
        db_service = DatabaseService(Config.DATABASE_URL)
        await db_service.connect()
        await db_service.initialize_schema()
        logger.info("Database service initialized")

        # Initialize OpenAI service
        openai_service = OpenAIService(Config.OPENAI_API_KEY)
        logger.info("OpenAI service initialized")

        # Initialize emoji service
        emoji_service = EmojiService(db_service)
        emoji_service.openai_service = openai_service
        await emoji_service.load_initial_data()
        logger.info("Emoji service initialized")

        # Initialize permission manager
        permission_manager = PermissionManager(db_service=db_service)
        logger.info("Permission manager initialized")

        # Initialize Slack handler
        slack_handler = SlackHandler(openai_service, emoji_service)
        slack_handler.set_emoji_service(emoji_service)

        # Initialize slash command handler
        slash_command_handler = SlashCommandHandler(
            slack_handler=slack_handler,
            emoji_service=emoji_service,
            permission_manager=permission_manager,
        )

        # Set slash command handler in slack handler
        slack_handler.set_slash_command_handler(slash_command_handler)

        await slack_handler.start()
        logger.info("Slack handler initialized with slash commands")

        logger.info("Bot initialized successfully")
        logger.info("Slack Emoji Bot is ready!")

        # Keep container running for testing/development
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


async def shutdown():
    """Gracefully shutdown the application."""
    logger.info("Shutting down Slack Emoji Reaction Bot...")

    try:
        # Stop Slack handler
        if slack_handler:
            await slack_handler.stop()
            logger.info("Slack handler stopped")

        # Close database connection
        if db_service:
            await db_service.close()
            logger.info("Database connection closed")

        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        exit(1)
