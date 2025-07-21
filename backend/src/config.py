import logging
import logging.config
import sys
import warnings
from typing import Annotated, Any, Literal

import structlog
from pydantic import (
    AnyUrl,
    BeforeValidator,
    Field,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production", "test"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Database pool settings
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    # Feature flag for optimized pool
    USE_OPTIMIZED_DB_POOL: bool = True

    CANVAS_CLIENT_ID: str
    CANVAS_CLIENT_SECRET: str
    CANVAS_REDIRECT_URI: HttpUrl
    CANVAS_BASE_URL: HttpUrl
    CANVAS_API_VERSION: str = "v1"

    # Mock Canvas URL for testing
    CANVAS_MOCK_URL: HttpUrl | None = None
    USE_CANVAS_MOCK: bool = False

    # API rate limiting
    CANVAS_API_RATE_LIMIT: int = 10  # Requests per second
    CANVAS_API_TIMEOUT: float = 30.0  # Request timeout in seconds

    # Retry configuration
    MAX_RETRIES: int = 3
    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 30.0
    RETRY_BACKOFF_FACTOR: float = 2.0

    # LLM settings
    OPENAI_SECRET_KEY: str | None = None
    LLM_API_TIMEOUT: float = 500.0  # LLM request timeout in seconds (5 minutes)

    # Module-based question generation settings
    MAX_CONCURRENT_MODULES: int = 5  # Maximum concurrent module processing tasks
    MAX_GENERATION_RETRIES: int = (
        3  # Maximum retries for question generation per module
    )
    MAX_JSON_CORRECTIONS: int = 2  # Maximum JSON correction attempts per module
    MODULE_GENERATION_TIMEOUT: int = (
        300  # Timeout per module generation in seconds (5 minutes)
    )
    CONTENT_LENGTH_THRESHOLD: int = (
        100  # Minimum content length for question generation
    )

    # RAGAS Validation Settings
    RAGAS_ENABLED: bool = Field(
        default=True, description="Enable RAGAS validation for generated questions"
    )
    RAGAS_FAITHFULNESS_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum faithfulness score for question validation",
    )
    RAGAS_SEMANTIC_SIMILARITY_THRESHOLD: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum semantic similarity score for question validation",
    )
    MAX_VALIDATION_RETRIES: int = Field(
        default=3,
        ge=0,
        description="Maximum number of validation retry attempts per question batch",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_TEST_DATABASE_URI(self) -> PostgresDsn:
        """Separate database URI for tests to avoid affecting development data"""
        test_db_name = f"{self.POSTGRES_DB}_test"
        return MultiHostUrl.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=test_db_name,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def canvas_api_url(self) -> str:
        """Get full Canvas API URL."""
        base = str(
            self.CANVAS_MOCK_URL
            if self.USE_CANVAS_MOCK and self.CANVAS_MOCK_URL
            else self.CANVAS_BASE_URL
        )
        return f"{base.rstrip('/')}/api/{self.CANVAS_API_VERSION}"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)

        return self


settings = Settings()  # type: ignore


# Logging Configuration
# ====================


# Context variables for request tracking
class LogContext:
    """Context manager for adding request/user context to logs."""

    def __init__(self) -> None:
        from contextvars import ContextVar

        self.request_id: ContextVar[str] = ContextVar("request_id", default="")
        self.request_method: ContextVar[str] = ContextVar("request_method", default="")
        self.request_path: ContextVar[str] = ContextVar("request_path", default="")
        self.user_id: ContextVar[str] = ContextVar("user_id", default="")
        self.canvas_id: ContextVar[int] = ContextVar("canvas_id", default=0)

    def set_request_context(self, request_id: str, method: str, path: str) -> None:
        """Set request context for logging."""
        self.request_id.set(request_id)
        self.request_method.set(method)
        self.request_path.set(path)

    def set_user_context(self, user_id: str, canvas_id: int = 0) -> None:
        """Set user context for logging."""
        self.user_id.set(user_id)
        if canvas_id:
            self.canvas_id.set(canvas_id)

    def clear_context(self) -> None:
        """Clear all context variables."""
        self.request_id.set("")
        self.request_method.set("")
        self.request_path.set("")
        self.user_id.set("")
        self.canvas_id.set(0)


# Global context instance
log_context = LogContext()


def configure_logging() -> None:
    """
    Configure structured logging for the application.

    Sets up structlog with different configurations based on environment:
    - Development: Human-readable console output with colors
    - Production: JSON structured logs for aggregation
    """
    # Configure standard library logging first
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=_get_log_level(),
    )

    # Configure structlog processors
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add context processors
        _add_request_context,
        _add_user_context,
    ]

    # Environment-specific final processor
    if settings.ENVIRONMENT == "local":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure third-party loggers
    _configure_third_party_loggers()


def _get_log_level() -> int:
    """Get log level based on environment."""
    log_levels = {
        "local": logging.DEBUG,
        "staging": logging.INFO,
        "production": logging.WARNING,
    }
    return log_levels.get(settings.ENVIRONMENT, logging.INFO)


def _add_request_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add request context to log entries.

    This processor adds request-specific information like request_id,
    method, and path to all log entries within a request context.
    """
    if log_context.request_id.get():
        event_dict["request_id"] = log_context.request_id.get()
    if log_context.request_method.get():
        event_dict["method"] = log_context.request_method.get()
    if log_context.request_path.get():
        event_dict["path"] = log_context.request_path.get()

    return event_dict


def _add_user_context(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add user context to log entries.

    This processor adds user-specific information like user_id and canvas_id
    to log entries when available.
    """
    if log_context.user_id.get():
        event_dict["user_id"] = log_context.user_id.get()
    if log_context.canvas_id.get():
        event_dict["canvas_id"] = log_context.canvas_id.get()

    return event_dict


def _configure_third_party_loggers() -> None:
    """Configure logging levels for third-party libraries."""
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)

    # Keep FastAPI logs at INFO level
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str = "") -> Any:
    """
    Get a configured logger instance.

    Args:
        name: Logger name, defaults to the calling module's name

    Returns:
        Configured structlog logger instance
    """
    return structlog.get_logger(name)
