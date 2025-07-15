"""OpenAI LLM provider implementation."""

import time
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config import get_logger

from .base import (
    AuthenticationError,
    BaseLLMProvider,
    LLMConfiguration,
    LLMMessage,
    LLMModel,
    LLMProvider,
    LLMResponse,
    ModelNotFoundError,
    RateLimitError,
)

logger = get_logger("openai_provider")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation using LangChain."""

    def __init__(self, configuration: LLMConfiguration):
        super().__init__(configuration)
        self._client: ChatOpenAI | None = None

        # OpenAI model definitions
        self._models = [
            LLMModel(
                provider=LLMProvider.OPENAI,
                model_id="o3-2025-04-16",
                display_name="OpenAI o3",
                max_tokens=200000,
                supports_streaming=True,
                cost_per_1k_tokens=0.015,
                description="Latest OpenAI o3 reasoning model",
            ),
        ]

    @property
    def provider_name(self) -> LLMProvider:
        """Return the provider name."""
        return LLMProvider.OPENAI

    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if self._client is not None:
            return

        api_key = self.configuration.provider_settings.get("api_key")
        if not api_key:
            raise AuthenticationError(
                "OpenAI API key is required", provider=self.provider_name
            )

        try:
            self._client = ChatOpenAI(
                model=self.configuration.model,
                temperature=self.configuration.temperature,
                api_key=SecretStr(api_key),
                timeout=self.configuration.timeout,
                max_retries=0,  # We handle retries ourselves
            )

            logger.info(
                "openai_provider_initialized",
                model=self.configuration.model,
                temperature=self.configuration.temperature,
                timeout=self.configuration.timeout,
            )

        except Exception as e:
            logger.error(
                "openai_provider_initialization_failed", error=str(e), exc_info=True
            )
            raise AuthenticationError(
                f"Failed to initialize OpenAI client: {str(e)}",
                provider=self.provider_name,
            )

    async def generate(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """
        Generate a response using OpenAI.

        Args:
            messages: List of messages for the conversation
            **kwargs: Additional generation parameters

        Returns:
            LLM response

        Raises:
            LLMError: If generation fails
        """
        if self._client is None:
            await self.initialize()

        start_time = time.time()

        try:
            # Convert our messages to LangChain format
            langchain_messages = []
            for msg in messages:
                langchain_messages.append((msg.role, msg.content))

            # Call the LangChain client
            if self._client is None:
                raise RuntimeError("OpenAI client not initialized")
            result = await self._client.ainvoke(langchain_messages)

            response_time = time.time() - start_time

            # Extract usage information if available
            prompt_tokens = getattr(result, "usage", {}).get("prompt_tokens")
            completion_tokens = getattr(result, "usage", {}).get("completion_tokens")
            total_tokens = getattr(result, "usage", {}).get("total_tokens")

            # Get content from response
            if hasattr(result, "content"):
                content = str(result.content) if result.content else ""
            else:
                content = str(result)

            logger.info(
                "openai_generation_completed",
                model=self.configuration.model,
                response_time=response_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                content_length=len(content),
            )

            return LLMResponse(
                content=content,
                model=self.configuration.model,
                provider=self.provider_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                response_time=response_time,
                metadata={"langchain_response": True, **kwargs},
            )

        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()

            logger.error(
                "openai_generation_failed",
                model=self.configuration.model,
                error=str(e),
                error_type=error_type,
                response_time=time.time() - start_time,
                exc_info=True,
            )

            # Map specific errors to our exception types
            if any(
                pattern in error_str
                for pattern in [
                    "invalid_api_key",
                    "invalidapikeyerror",
                    "authentication",
                    "insufficient_quota",
                    "billing",
                    "organization must be verified",
                ]
            ):
                raise AuthenticationError(
                    f"OpenAI authentication error: {str(e)}",
                    provider=self.provider_name,
                )

            elif any(
                pattern in error_str
                for pattern in ["rate_limit", "rate limit", "too many requests"]
            ):
                # Try to extract retry-after from error message
                retry_after = None
                if "retry after" in error_str:
                    try:
                        # Simple parsing for retry-after seconds
                        parts = error_str.split("retry after")
                        if len(parts) > 1:
                            number_part = parts[1].split()[0]
                            retry_after = float(number_part)
                    except (ValueError, IndexError):
                        pass

                raise RateLimitError(
                    f"OpenAI rate limit exceeded: {str(e)}",
                    provider=self.provider_name,
                    retry_after=retry_after,
                )

            elif any(
                pattern in error_str
                for pattern in ["model_not_found", "invalid_model", "unsupported_model"]
            ):
                raise ModelNotFoundError(
                    f"OpenAI model not found: {str(e)}",
                    provider=self.provider_name,
                    model=self.configuration.model,
                )

            elif any(
                pattern in error_str for pattern in ["timeout", "502", "503", "504"]
            ):
                # These are retryable errors
                from .base import LLMError

                raise LLMError(
                    f"OpenAI temporary error: {str(e)}",
                    provider=self.provider_name,
                    error_code="temporary_error",
                    retryable=True,
                )

            else:
                # Generic error
                from .base import LLMError

                raise LLMError(
                    f"OpenAI error: {str(e)}",
                    provider=self.provider_name,
                    error_code="unknown_error",
                    retryable=False,
                )

    async def get_available_models(self) -> list[LLMModel]:
        """
        Get list of available OpenAI models.

        Returns:
            List of available models
        """
        return self._models.copy()

    def validate_configuration(self) -> None:
        """
        Validate the OpenAI provider configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.configuration.provider != LLMProvider.OPENAI:
            raise ValueError(f"Configuration provider must be {LLMProvider.OPENAI}")

        api_key = self.configuration.provider_settings.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key is required in provider_settings.api_key")

        if not isinstance(api_key, str) or len(api_key.strip()) == 0:
            raise ValueError("OpenAI API key must be a non-empty string")

        # Validate model is supported
        available_model_ids = [model.model_id for model in self._models]
        if self.configuration.model not in available_model_ids:
            raise ValueError(
                f"Model {self.configuration.model} is not supported. "
                f"Available models: {', '.join(available_model_ids)}"
            )

        # Validate temperature range
        if not (0.0 <= self.configuration.temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")

        # Validate timeout
        if self.configuration.timeout <= 0:
            raise ValueError("Timeout must be positive")

    def get_model_info(self, model_id: str) -> LLMModel | None:
        """
        Get information about a specific model.

        Args:
            model_id: The model ID

        Returns:
            Model information or None if not found
        """
        for model in self._models:
            if model.model_id == model_id:
                return model
        return None

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"OpenAI Provider (model: {self.configuration.model})"
