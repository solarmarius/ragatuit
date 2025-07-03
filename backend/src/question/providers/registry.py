"""LLM provider registry for managing and creating provider instances."""

from src.logging_config import get_logger

from .base import BaseLLMProvider, LLMConfiguration, LLMModel, LLMProvider

logger = get_logger("llm_provider_registry")


class LLMProviderRegistry:
    """
    Registry for LLM provider implementations.

    Manages provider classes, configurations, and provides factory methods
    for creating provider instances.
    """

    def __init__(self) -> None:
        self._provider_classes: dict[LLMProvider, type[BaseLLMProvider]] = {}
        self._default_configurations: dict[LLMProvider, LLMConfiguration] = {}
        self._initialized = False

    def register_provider(
        self,
        provider: LLMProvider,
        provider_class: type[BaseLLMProvider],
        default_config: LLMConfiguration | None = None,
    ) -> None:
        """
        Register an LLM provider implementation.

        Args:
            provider: The provider enum
            provider_class: The provider implementation class
            default_config: Default configuration for the provider

        Raises:
            ValueError: If provider is already registered or class is invalid
        """
        if provider in self._provider_classes:
            raise ValueError(f"Provider {provider} is already registered")

        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError("Provider class must inherit from BaseLLMProvider")

        self._provider_classes[provider] = provider_class

        if default_config:
            if default_config.provider != provider:
                raise ValueError(
                    f"Default config provider {default_config.provider} "
                    f"does not match registered provider {provider}"
                )
            self._default_configurations[provider] = default_config

        logger.info(
            "llm_provider_registered",
            provider=provider.value,
            provider_class=provider_class.__name__,
            has_default_config=default_config is not None,
        )

    def get_provider(
        self, provider: LLMProvider, configuration: LLMConfiguration | None = None
    ) -> BaseLLMProvider:
        """
        Create a provider instance.

        Args:
            provider: The provider to create
            configuration: Configuration for the provider, uses default if None

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered or configuration is invalid
        """
        if not self._initialized:
            self._initialize_default_providers()

        if provider not in self._provider_classes:
            raise ValueError(f"Provider {provider} is not registered")

        # Use provided configuration or default
        if configuration is None:
            if provider in self._default_configurations:
                configuration = self._default_configurations[provider]
            else:
                raise ValueError(
                    f"No configuration provided for provider {provider} and no default available"
                )

        # Validate configuration matches provider
        if configuration.provider != provider:
            raise ValueError(
                f"Configuration provider {configuration.provider} "
                f"does not match requested provider {provider}"
            )

        provider_class = self._provider_classes[provider]
        instance = provider_class(configuration)

        # Validate the configuration
        instance.validate_configuration()

        return instance

    def get_available_providers(self) -> list[LLMProvider]:
        """
        Get list of all registered providers.

        Returns:
            List of registered providers
        """
        if not self._initialized:
            self._initialize_default_providers()

        return list(self._provider_classes.keys())

    def is_registered(self, provider: LLMProvider) -> bool:
        """
        Check if a provider is registered.

        Args:
            provider: The provider to check

        Returns:
            True if registered, False otherwise
        """
        if not self._initialized:
            self._initialize_default_providers()

        return provider in self._provider_classes

    def get_default_configuration(
        self, provider: LLMProvider
    ) -> LLMConfiguration | None:
        """
        Get default configuration for a provider.

        Args:
            provider: The provider

        Returns:
            Default configuration or None if not available
        """
        return self._default_configurations.get(provider)

    def set_default_configuration(
        self, provider: LLMProvider, configuration: LLMConfiguration
    ) -> None:
        """
        Set default configuration for a provider.

        Args:
            provider: The provider
            configuration: The default configuration

        Raises:
            ValueError: If provider is not registered or configuration is invalid
        """
        if provider not in self._provider_classes:
            raise ValueError(f"Provider {provider} is not registered")

        if configuration.provider != provider:
            raise ValueError(
                f"Configuration provider {configuration.provider} "
                f"does not match provider {provider}"
            )

        self._default_configurations[provider] = configuration

        logger.info(
            "default_configuration_updated",
            provider=provider.value,
            model=configuration.model,
        )

    async def get_available_models(self, provider: LLMProvider) -> list[LLMModel]:
        """
        Get available models for a provider.

        Args:
            provider: The provider

        Returns:
            List of available models

        Raises:
            ValueError: If provider is not registered
        """
        if not self.is_registered(provider):
            raise ValueError(f"Provider {provider} is not registered")

        # Create a temporary instance to get models
        provider_instance = self.get_provider(provider)
        return await provider_instance.get_available_models()

    async def health_check(self, provider: LLMProvider) -> bool:
        """
        Perform health check on a provider.

        Args:
            provider: The provider to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.is_registered(provider):
                return False

            provider_instance = self.get_provider(provider)
            return await provider_instance.health_check()

        except Exception as e:
            logger.error(
                "provider_health_check_failed",
                provider=provider.value,
                error=str(e),
                exc_info=True,
            )
            return False

    def unregister_provider(self, provider: LLMProvider) -> None:
        """
        Unregister a provider.

        Args:
            provider: The provider to unregister

        Raises:
            ValueError: If provider is not registered
        """
        if provider not in self._provider_classes:
            raise ValueError(f"Provider {provider} is not registered")

        del self._provider_classes[provider]

        if provider in self._default_configurations:
            del self._default_configurations[provider]

        logger.info("llm_provider_unregistered", provider=provider.value)

    def _initialize_default_providers(self) -> None:
        """Initialize the registry with default provider implementations."""
        if self._initialized:
            return

        try:
            # Import and register default providers
            # Register OpenAI provider
            from src.config import settings

            from .mock_provider import MockProvider
            from .openai_provider import OpenAIProvider

            if settings.OPENAI_SECRET_KEY:
                openai_config = LLMConfiguration(
                    provider=LLMProvider.OPENAI,
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    timeout=settings.LLM_API_TIMEOUT,
                    max_retries=settings.MAX_RETRIES,
                    initial_retry_delay=settings.INITIAL_RETRY_DELAY,
                    max_retry_delay=settings.MAX_RETRY_DELAY,
                    retry_backoff_factor=settings.RETRY_BACKOFF_FACTOR,
                    provider_settings={"api_key": settings.OPENAI_SECRET_KEY},
                )

                self.register_provider(
                    LLMProvider.OPENAI, OpenAIProvider, openai_config
                )

            # Always register mock provider for testing
            mock_config = LLMConfiguration(
                provider=LLMProvider.MOCK,
                model="mock-model",
                temperature=0.7,
                timeout=5.0,
                max_retries=0,
            )

            self.register_provider(LLMProvider.MOCK, MockProvider, mock_config)

            logger.info(
                "llm_provider_registry_initialized",
                registered_providers=len(self._provider_classes),
            )

        except ImportError as e:
            logger.error(
                "failed_to_initialize_default_providers", error=str(e), exc_info=True
            )
            # Continue with empty registry rather than failing

        self._initialized = True


# Global registry instance
llm_provider_registry = LLMProviderRegistry()


def get_llm_provider_registry() -> LLMProviderRegistry:
    """Get the global LLM provider registry instance."""
    return llm_provider_registry
