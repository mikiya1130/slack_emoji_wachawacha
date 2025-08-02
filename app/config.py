import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Slack-specific configuration"""

    bot_token: str = ""
    app_token: str = ""
    socket_mode_enabled: bool = True
    request_timeout: int = 30
    max_retries: int = 3


@dataclass
class OpenAIConfig:
    """OpenAI-specific configuration"""

    api_key: str = ""
    model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    request_timeout: int = 60
    max_retries: int = 3
    base_delay: float = 1.0


@dataclass
class DatabaseConfig:
    """Database-specific configuration"""

    url: str = "postgresql://user:pass@localhost:5432/emoji_bot"
    pool_size: int = 10
    min_pool_size: int = 2
    max_pool_size: int = 20
    connection_timeout: int = 30
    command_timeout: int = 60


@dataclass
class EmojiConfig:
    """Emoji service configuration"""

    default_reaction_count: int = 3
    cache_enabled: bool = True
    cache_ttl: int = 3600
    similarity_threshold: float = 0.7
    max_concurrent_reactions: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration"""

    level: str = "INFO"
    format: str = "human"  # human or json
    use_colors: bool = True
    log_file: Optional[str] = None
    max_file_size: int = 10_485_760  # 10MB
    backup_count: int = 5


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""

    enabled: bool = True
    export_interval: int = 60
    metrics_port: int = 9090
    health_check_interval: int = 30


class Config:
    """Enhanced application configuration management."""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CONFIG_FILE: Optional[str] = os.getenv("CONFIG_FILE")

    # Component configurations
    slack: SlackConfig
    openai: OpenAIConfig
    database: DatabaseConfig
    emoji: EmojiConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig

    # Legacy compatibility
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://user:pass@localhost:5432/emoji_bot"
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    DEFAULT_REACTION_COUNT: int = 3

    # Internal state
    _instance: Optional["Config"] = None
    _loaded: bool = False
    _config_sources: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern for configuration"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize configuration from all sources"""
        if self._loaded:
            return

        # Load environment at runtime, not class definition time
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.CONFIG_FILE = os.getenv("CONFIG_FILE")

        # Initialize component configurations
        self.slack = SlackConfig()
        self.openai = OpenAIConfig()
        self.database = DatabaseConfig()
        self.emoji = EmojiConfig()
        self.logging = LoggingConfig()
        self.monitoring = MonitoringConfig()

        # Load from environment variables
        self._load_from_env()

        # Load from config file if specified
        if self.CONFIG_FILE:
            self._load_from_file(self.CONFIG_FILE)

        # Apply environment-specific overrides
        self._apply_environment_overrides()

        # Update legacy fields
        self._update_legacy_fields()

        self._loaded = True
        logger.info(f"Configuration loaded for environment: {self.ENVIRONMENT}")

    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Slack configuration
        self.slack.bot_token = os.getenv("SLACK_BOT_TOKEN", "")
        self.slack.app_token = os.getenv("SLACK_APP_TOKEN", "")
        self.slack.socket_mode_enabled = (
            os.getenv("SLACK_SOCKET_MODE", "true").lower() == "true"
        )
        self.slack.request_timeout = int(os.getenv("SLACK_REQUEST_TIMEOUT", "30"))
        self.slack.max_retries = int(os.getenv("SLACK_MAX_RETRIES", "3"))

        # OpenAI configuration
        self.openai.api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai.model = os.getenv("OPENAI_MODEL", "text-embedding-3-small")
        self.openai.embedding_dimension = int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))
        self.openai.request_timeout = int(os.getenv("OPENAI_REQUEST_TIMEOUT", "60"))
        self.openai.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self.openai.base_delay = float(os.getenv("OPENAI_BASE_DELAY", "1.0"))

        # Database configuration
        self.database.url = os.getenv(
            "DATABASE_URL", "postgresql://user:pass@localhost:5432/emoji_bot"
        )
        self.database.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.database.min_pool_size = int(os.getenv("DB_MIN_POOL_SIZE", "2"))
        self.database.max_pool_size = int(os.getenv("DB_MAX_POOL_SIZE", "20"))
        self.database.connection_timeout = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
        self.database.command_timeout = int(os.getenv("DB_COMMAND_TIMEOUT", "60"))

        # Emoji configuration
        self.emoji.default_reaction_count = int(
            os.getenv("DEFAULT_REACTION_COUNT", "3")
        )
        self.emoji.cache_enabled = (
            os.getenv("EMOJI_CACHE_ENABLED", "true").lower() == "true"
        )
        self.emoji.cache_ttl = int(os.getenv("EMOJI_CACHE_TTL", "3600"))
        self.emoji.similarity_threshold = float(
            os.getenv("EMOJI_SIMILARITY_THRESHOLD", "0.7")
        )
        self.emoji.max_concurrent_reactions = int(
            os.getenv("MAX_CONCURRENT_REACTIONS", "10")
        )

        # Logging configuration
        self.logging.level = os.getenv("LOG_LEVEL", "INFO")
        self.logging.format = os.getenv("LOG_FORMAT", "human")
        self.logging.use_colors = os.getenv("LOG_USE_COLORS", "true").lower() == "true"
        self.logging.log_file = os.getenv("LOG_FILE")
        self.logging.max_file_size = int(os.getenv("LOG_MAX_FILE_SIZE", "10485760"))
        self.logging.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

        # Monitoring configuration
        self.monitoring.enabled = (
            os.getenv("MONITORING_ENABLED", "true").lower() == "true"
        )
        self.monitoring.export_interval = int(
            os.getenv("METRICS_EXPORT_INTERVAL", "60")
        )
        self.monitoring.metrics_port = int(os.getenv("METRICS_PORT", "9090"))
        self.monitoring.health_check_interval = int(
            os.getenv("HEALTH_CHECK_INTERVAL", "30")
        )

        self._config_sources["environment"] = "Environment variables loaded"

    def _load_from_file(self, config_file: str):
        """Load configuration from JSON or YAML file"""
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_file}")
            return

        try:
            with open(config_path, "r") as f:
                if config_path.suffix in [".json"]:
                    file_config = json.load(f)
                elif config_path.suffix in [".yaml", ".yml"]:
                    # Optional YAML support
                    try:
                        import yaml  # type: ignore[import-untyped]

                        file_config = yaml.safe_load(f)
                    except ImportError:
                        logger.warning("PyYAML not installed, skipping YAML config")
                        return
                else:
                    logger.warning(
                        f"Unsupported config file format: {config_path.suffix}"
                    )
                    return

            # Apply file configuration
            self._apply_dict_config(file_config)
            self._config_sources["file"] = str(config_path)
            logger.info(f"Loaded configuration from file: {config_path}")

        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")

    def _apply_dict_config(self, config_dict: Dict[str, Any]):
        """Apply configuration from dictionary"""
        # Slack configuration
        if "slack" in config_dict:
            slack_config = config_dict["slack"]
            self.slack.bot_token = slack_config.get("bot_token", self.slack.bot_token)
            self.slack.app_token = slack_config.get("app_token", self.slack.app_token)
            self.slack.socket_mode_enabled = slack_config.get(
                "socket_mode_enabled", self.slack.socket_mode_enabled
            )
            self.slack.request_timeout = slack_config.get(
                "request_timeout", self.slack.request_timeout
            )
            self.slack.max_retries = slack_config.get(
                "max_retries", self.slack.max_retries
            )

        # OpenAI configuration
        if "openai" in config_dict:
            openai_config = config_dict["openai"]
            self.openai.api_key = openai_config.get("api_key", self.openai.api_key)
            self.openai.model = openai_config.get("model", self.openai.model)
            self.openai.embedding_dimension = openai_config.get(
                "embedding_dimension", self.openai.embedding_dimension
            )
            self.openai.request_timeout = openai_config.get(
                "request_timeout", self.openai.request_timeout
            )
            self.openai.max_retries = openai_config.get(
                "max_retries", self.openai.max_retries
            )
            self.openai.base_delay = openai_config.get(
                "base_delay", self.openai.base_delay
            )

        # Database configuration
        if "database" in config_dict:
            db_config = config_dict["database"]
            self.database.url = db_config.get("url", self.database.url)
            self.database.pool_size = db_config.get(
                "pool_size", self.database.pool_size
            )
            self.database.min_pool_size = db_config.get(
                "min_pool_size", self.database.min_pool_size
            )
            self.database.max_pool_size = db_config.get(
                "max_pool_size", self.database.max_pool_size
            )
            self.database.connection_timeout = db_config.get(
                "connection_timeout", self.database.connection_timeout
            )
            self.database.command_timeout = db_config.get(
                "command_timeout", self.database.command_timeout
            )

        # Emoji configuration
        if "emoji" in config_dict:
            emoji_config = config_dict["emoji"]
            self.emoji.default_reaction_count = emoji_config.get(
                "default_reaction_count", self.emoji.default_reaction_count
            )
            self.emoji.cache_enabled = emoji_config.get(
                "cache_enabled", self.emoji.cache_enabled
            )
            self.emoji.cache_ttl = emoji_config.get("cache_ttl", self.emoji.cache_ttl)
            self.emoji.similarity_threshold = emoji_config.get(
                "similarity_threshold", self.emoji.similarity_threshold
            )
            self.emoji.max_concurrent_reactions = emoji_config.get(
                "max_concurrent_reactions", self.emoji.max_concurrent_reactions
            )

        # Logging configuration
        if "logging" in config_dict:
            log_config = config_dict["logging"]
            self.logging.level = log_config.get("level", self.logging.level)
            self.logging.format = log_config.get("format", self.logging.format)
            self.logging.use_colors = log_config.get(
                "use_colors", self.logging.use_colors
            )
            self.logging.log_file = log_config.get("log_file", self.logging.log_file)
            self.logging.max_file_size = log_config.get(
                "max_file_size", self.logging.max_file_size
            )
            self.logging.backup_count = log_config.get(
                "backup_count", self.logging.backup_count
            )

        # Monitoring configuration
        if "monitoring" in config_dict:
            mon_config = config_dict["monitoring"]
            self.monitoring.enabled = mon_config.get("enabled", self.monitoring.enabled)
            self.monitoring.export_interval = mon_config.get(
                "export_interval", self.monitoring.export_interval
            )
            self.monitoring.metrics_port = mon_config.get(
                "metrics_port", self.monitoring.metrics_port
            )
            self.monitoring.health_check_interval = mon_config.get(
                "health_check_interval", self.monitoring.health_check_interval
            )

    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides"""
        if self.is_production():
            # Production overrides
            self.logging.level = "WARNING"
            self.logging.format = "json"
            self.logging.use_colors = False
            self.monitoring.enabled = True
        elif self.is_development():
            # Development overrides
            self.logging.use_colors = True
            self.monitoring.enabled = False

    def _update_legacy_fields(self):
        """Update legacy fields for backward compatibility"""
        self.SLACK_BOT_TOKEN = self.slack.bot_token
        self.SLACK_APP_TOKEN = self.slack.app_token
        self.OPENAI_API_KEY = self.openai.api_key
        self.DATABASE_URL = self.database.url
        self.LOG_LEVEL = self.logging.level
        self.EMBEDDING_MODEL = self.openai.model
        self.EMBEDDING_DIMENSION = self.openai.embedding_dimension
        self.DEFAULT_REACTION_COUNT = self.emoji.default_reaction_count

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        instance = cls()
        errors = []

        # Validate Slack configuration
        if not instance.slack.bot_token:
            errors.append("SLACK_BOT_TOKEN is required")
        if not instance.slack.app_token:
            errors.append("SLACK_APP_TOKEN is required")

        # Validate OpenAI configuration
        if not instance.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        if instance.openai.embedding_dimension not in [1536, 3072]:
            errors.append(
                f"Invalid embedding dimension: {instance.openai.embedding_dimension}"
            )

        # Validate Database configuration
        if not instance.database.url:
            errors.append("DATABASE_URL is required")
        if instance.database.pool_size < 1:
            errors.append("Database pool size must be at least 1")

        # Validate other settings
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if instance.logging.level.upper() not in valid_log_levels:
            errors.append(f"Invalid log level: {instance.logging.level}")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            raise ValueError(error_msg)

        # Clear any cached instance to force reload
        cls._instance = None
        cls._loaded = False

        return True

    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment."""
        return cls().ENVIRONMENT.lower() == "development"

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls().ENVIRONMENT.lower() == "production"

    @classmethod
    def is_testing(cls) -> bool:
        """Check if running in testing environment."""
        return cls().ENVIRONMENT.lower() in ["test", "testing"]

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary (with sensitive data masked)"""
        return {
            "environment": self.ENVIRONMENT,
            "config_sources": self._config_sources,
            "slack": {
                "bot_token": self._mask_sensitive(self.slack.bot_token),
                "app_token": self._mask_sensitive(self.slack.app_token),
                "socket_mode_enabled": self.slack.socket_mode_enabled,
            },
            "openai": {
                "api_key": self._mask_sensitive(self.openai.api_key),
                "model": self.openai.model,
                "embedding_dimension": self.openai.embedding_dimension,
            },
            "database": {
                "url": self._mask_database_url(self.database.url),
                "pool_size": self.database.pool_size,
            },
            "emoji": {
                "default_reaction_count": self.emoji.default_reaction_count,
                "cache_enabled": self.emoji.cache_enabled,
                "cache_ttl": self.emoji.cache_ttl,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "metrics_port": self.monitoring.metrics_port,
            },
        }

    def _mask_sensitive(self, value: str, visible_chars: int = 4) -> str:
        """Mask sensitive configuration values"""
        if not value:
            return "<not_set>"
        if len(value) <= visible_chars * 2:
            return "*" * len(value)
        return f"{value[:visible_chars]}...{value[-visible_chars:]}"

    def _mask_database_url(self, url: str) -> str:
        """Mask database URL while keeping structure visible"""
        if not url:
            return "<not_set>"

        # Parse and mask password
        if "@" in url:
            parts = url.split("@")
            if ":" in parts[0]:
                scheme_user = parts[0].rsplit(":", 1)[0]
                host_db = parts[1] if len(parts) > 1 else ""
                return f"{scheme_user}:****@{host_db}"

        return self._mask_sensitive(url, 10)

    def export_config(self, output_file: str, include_sensitive: bool = False):
        """Export current configuration to file"""
        config_data = (
            self.get_config_summary()
            if not include_sensitive
            else {
                "environment": self.ENVIRONMENT,
                "slack": {
                    "bot_token": self.slack.bot_token,
                    "app_token": self.slack.app_token,
                    "socket_mode_enabled": self.slack.socket_mode_enabled,
                    "request_timeout": self.slack.request_timeout,
                    "max_retries": self.slack.max_retries,
                },
                # ... (full config)
            }
        )

        output_path = Path(output_file)
        with open(output_path, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"Configuration exported to: {output_path}")


# Create singleton instance
config = Config()
