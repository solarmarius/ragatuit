"""Abstract base classes and interfaces for LLM providers."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.config import get_logger

logger = get_logger("llm_provider")


class LLMProvider(str, Enum):
    """Enumeration of supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    MOCK = "mock"  # For testing


class LLMModel(BaseModel):
    """Model information for an LLM."""

    provider: LLMProvider
    model_id: str
    display_name: str
    max_tokens: int
    supports_streaming: bool = False
    cost_per_1k_tokens: float | None = None
    description: str | None = None


class LLMConfiguration(BaseModel):
    """Configuration for LLM providers."""

    provider: LLMProvider
    model: str
    temperature: float = Field(ge=0.0, le=2.0, default=1.0)
    max_tokens: int | None = Field(default=None, ge=1)
    timeout: float = Field(default=120.0, ge=1.0)

    # Retry configuration
    max_retries: int = Field(default=3, ge=0)
    initial_retry_delay: float = Field(default=1.0, ge=0.1)
    max_retry_delay: float = Field(default=30.0, ge=1.0)
    retry_backoff_factor: float = Field(default=2.0, ge=1.0)

    # Provider-specific settings
    provider_settings: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class LLMMessage(BaseModel):
    """A message in an LLM conversation."""

    role: str = Field(description="Message role (system, user, assistant)")
    content: str = Field(description="Message content")
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str = Field(description="Generated content")
    model: str = Field(description="Model used for generation")
    provider: LLMProvider = Field(description="Provider used")

    # Usage statistics
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    # Metadata
    response_time: float = Field(description="Response time in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class LLMError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider: LLMProvider | None = None,
        error_code: str | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable


class RateLimitError(LLMError):
    """Exception for rate limit errors."""

    def __init__(
        self,
        message: str,
        provider: LLMProvider | None = None,
        retry_after: float | None = None,
    ):
        super().__init__(message, provider, "rate_limit", retryable=True)
        self.retry_after = retry_after


class AuthenticationError(LLMError):
    """Exception for authentication errors."""

    def __init__(self, message: str, provider: LLMProvider | None = None):
        super().__init__(message, provider, "authentication", retryable=False)


class ModelNotFoundError(LLMError):
    """Exception for model not found errors."""

    def __init__(
        self,
        message: str,
        provider: LLMProvider | None = None,
        model: str | None = None,
    ):
        super().__init__(message, provider, "model_not_found", retryable=False)
        self.model = model


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, configuration: LLMConfiguration):
        self.configuration = configuration
        self._initialized = False

    @property
    @abstractmethod
    def provider_name(self) -> LLMProvider:
        """Return the provider name."""
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (authentication, setup, etc.)."""
        pass

    @abstractmethod
    async def generate(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of messages for the conversation
            **kwargs: Additional generation parameters

        Returns:
            LLM response

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    async def get_available_models(self) -> list[LLMModel]:
        """
        Get list of available models for this provider.

        Returns:
            List of available models
        """
        pass

    @abstractmethod
    def validate_configuration(self) -> None:
        """
        Validate the provider configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        pass

    async def generate_with_retry(
        self, messages: list[LLMMessage], **kwargs: Any
    ) -> LLMResponse:
        """
        Generate with automatic retry logic.

        Args:
            messages: List of messages for the conversation
            **kwargs: Additional generation parameters

        Returns:
            LLM response

        Raises:
            LLMError: If all retries fail
        """
        if not self._initialized:
            await self.initialize()
            self._initialized = True

        last_exception = None

        for attempt in range(self.configuration.max_retries + 1):
            try:
                return await self.generate(messages, **kwargs)

            except LLMError as e:
                last_exception = e

                # Don't retry non-retryable errors
                if not e.retryable:
                    logger.error(
                        "non_retryable_llm_error",
                        provider=self.provider_name.value,
                        error_code=e.error_code,
                        message=e.message,
                        attempt=attempt + 1,
                    )
                    raise

                # Don't retry on final attempt
                if attempt == self.configuration.max_retries:
                    logger.error(
                        "llm_max_retries_exceeded",
                        provider=self.provider_name.value,
                        error_code=e.error_code,
                        message=e.message,
                        total_attempts=attempt + 1,
                    )
                    raise

                # Calculate delay for retry
                delay = min(
                    self.configuration.initial_retry_delay
                    * (self.configuration.retry_backoff_factor**attempt),
                    self.configuration.max_retry_delay,
                )

                # Special handling for rate limits
                if isinstance(e, RateLimitError) and e.retry_after:
                    delay = max(delay, e.retry_after)

                logger.warning(
                    "llm_error_retrying",
                    provider=self.provider_name.value,
                    error_code=e.error_code,
                    message=e.message,
                    attempt=attempt + 1,
                    retry_delay=delay,
                )

                await asyncio.sleep(delay)

            except Exception as e:
                # Wrap unexpected errors
                last_exception = LLMError(
                    f"Unexpected error: {str(e)}",
                    provider=self.provider_name,
                    retryable=False,
                )
                logger.error(
                    "unexpected_llm_error",
                    provider=self.provider_name.value,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                    exc_info=True,
                )
                raise last_exception

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise LLMError(
                "Failed to generate response after retries", provider=self.provider_name
            )

    async def health_check(self) -> bool:
        """
        Perform a health check on the provider.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            if not self._initialized:
                await self.initialize()
                self._initialized = True

            # Try a simple generation
            test_messages = [
                LLMMessage(role="user", content="Hello, this is a test message.")
            ]

            response = await self.generate(test_messages)
            return bool(response.content)

        except Exception as e:
            logger.error(
                "llm_provider_health_check_failed",
                provider=self.provider_name.value,
                error=str(e),
                exc_info=True,
            )
            return False
