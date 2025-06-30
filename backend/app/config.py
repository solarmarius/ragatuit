import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
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
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

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

    # Content extraction limits
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB per file
    MAX_TOTAL_CONTENT_SIZE: int = 50 * 1024 * 1024  # 50MB total per quiz
    MAX_PAGES_PER_MODULE: int = 100  # Maximum pages per module
    MAX_CONTENT_LENGTH: int = 500_000  # Maximum content length per page
    MIN_CONTENT_LENGTH: int = 50  # Minimum content length

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
    LLM_API_TIMEOUT: float = 120.0  # LLM request timeout in seconds (2 minutes)

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
