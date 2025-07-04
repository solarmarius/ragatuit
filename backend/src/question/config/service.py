"""Configuration service for question generation system."""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.config import get_logger, settings

from ..providers import LLMConfiguration, LLMProvider
from ..types import QuestionType
from ..workflows import WorkflowConfiguration

logger = get_logger("config_service")


class QuestionGenerationConfig(BaseModel):
    """Configuration for question generation system."""

    # Provider configurations
    default_provider: LLMProvider = Field(default=LLMProvider.OPENAI)
    provider_configs: dict[LLMProvider, LLMConfiguration] = Field(default_factory=dict)

    # Workflow configurations
    default_workflow_config: WorkflowConfiguration = Field(
        default_factory=WorkflowConfiguration
    )
    question_type_configs: dict[QuestionType, WorkflowConfiguration] = Field(
        default_factory=dict
    )

    # Template configurations
    default_template_dir: str | None = Field(default=None)
    template_cache_size: int = Field(default=100, ge=1)
    template_auto_reload: bool = Field(default=True)

    # Generation settings
    enable_content_caching: bool = Field(default=True)
    max_concurrent_generations: int = Field(default=20, ge=1, le=50)
    generation_timeout: float = Field(default=300.0, ge=60.0)

    # Quality settings
    enable_duplicate_detection: bool = Field(default=True)
    min_question_quality_score: float = Field(default=0.7, ge=0.0, le=1.0)
    enable_automatic_validation: bool = Field(default=True)

    # Monitoring and logging
    enable_detailed_logging: bool = Field(default=False)
    log_llm_requests: bool = Field(default=False)
    enable_metrics_collection: bool = Field(default=True)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"

    @field_validator("provider_configs")
    def validate_provider_configs(
        cls, v: dict[LLMProvider, LLMConfiguration]
    ) -> dict[LLMProvider, LLMConfiguration]:
        """Validate provider configurations."""
        for provider, config in v.items():
            if config.provider != provider:
                raise ValueError(
                    f"Provider config mismatch: {provider} != {config.provider}"
                )
        return v


class ConfigurationService:
    """
    Service for managing configuration of the question generation system.

    Provides centralized configuration management with support for:
    - Environment-based configuration
    - File-based configuration overrides
    - Runtime configuration updates
    - Configuration validation
    """

    def __init__(self, config_file: str | None = None):
        """
        Initialize configuration service.

        Args:
            config_file: Optional configuration file path
        """
        self.config_file = config_file
        self._config: QuestionGenerationConfig | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the configuration service."""
        if self._initialized:
            return

        try:
            # Load configuration
            self._config = self._load_configuration()

            # Validate configuration
            self._validate_configuration()

            logger.info(
                "configuration_service_initialized",
                config_file=self.config_file,
                default_provider=self._config.default_provider.value,
                provider_count=len(self._config.provider_configs),
                question_type_configs=len(self._config.question_type_configs),
            )

        except Exception as e:
            logger.error(
                "configuration_service_initialization_failed",
                config_file=self.config_file,
                error=str(e),
                exc_info=True,
            )
            # Use default configuration
            self._config = QuestionGenerationConfig()

        self._initialized = True

    def get_config(self) -> QuestionGenerationConfig:
        """
        Get the current configuration.

        Returns:
            Current configuration
        """
        if not self._initialized:
            self.initialize()

        assert self._config is not None, "Configuration should be initialized"
        return self._config

    def get_provider_config(
        self, provider: LLMProvider | None = None
    ) -> LLMConfiguration:
        """
        Get provider configuration.

        Args:
            provider: Provider to get config for, uses default if None

        Returns:
            Provider configuration

        Raises:
            ValueError: If provider configuration is not found
        """
        config = self.get_config()

        if provider is None:
            provider = config.default_provider

        if provider in config.provider_configs:
            return config.provider_configs[provider]

        # Create default configuration from environment
        return self._create_default_provider_config(provider)

    def get_workflow_config(
        self, question_type: QuestionType | None = None
    ) -> WorkflowConfiguration:
        """
        Get workflow configuration.

        Args:
            question_type: Question type to get config for

        Returns:
            Workflow configuration
        """
        config = self.get_config()

        if question_type and question_type in config.question_type_configs:
            return config.question_type_configs[question_type]

        return config.default_workflow_config

    def update_provider_config(
        self, provider: LLMProvider, provider_config: LLMConfiguration
    ) -> None:
        """
        Update provider configuration.

        Args:
            provider: Provider to update
            provider_config: New provider configuration

        Raises:
            ValueError: If provider configuration is invalid
        """
        if provider_config.provider != provider:
            raise ValueError(
                f"Provider config mismatch: {provider} != {provider_config.provider}"
            )

        config = self.get_config()
        config.provider_configs[provider] = provider_config

        # Save to file if configured
        if self.config_file:
            self._save_configuration(config)

        logger.info(
            "provider_config_updated",
            provider=provider.value,
            model=provider_config.model,
            temperature=provider_config.temperature,
        )

    def update_workflow_config(
        self, question_type: QuestionType, workflow_config: WorkflowConfiguration
    ) -> None:
        """
        Update workflow configuration for a question type.

        Args:
            question_type: Question type to update
            workflow_config: New workflow configuration
        """
        config = self.get_config()
        config.question_type_configs[question_type] = workflow_config

        # Save to file if configured
        if self.config_file:
            self._save_configuration(config)

        logger.info(
            "workflow_config_updated",
            question_type=question_type.value,
            max_chunk_size=workflow_config.max_chunk_size,
            max_questions_per_chunk=workflow_config.max_questions_per_chunk,
        )

    def set_default_provider(self, provider: LLMProvider) -> None:
        """
        Set the default provider.

        Args:
            provider: Provider to set as default
        """
        config = self.get_config()
        config.default_provider = provider

        # Save to file if configured
        if self.config_file:
            self._save_configuration(config)

        logger.info("default_provider_updated", provider=provider.value)

    def get_available_providers(self) -> list[LLMProvider]:
        """
        Get list of configured providers.

        Returns:
            List of available providers
        """
        config = self.get_config()
        return list(config.provider_configs.keys())

    def get_configuration_summary(self) -> dict[str, Any]:
        """
        Get a summary of current configuration.

        Returns:
            Configuration summary
        """
        config = self.get_config()

        return {
            "default_provider": config.default_provider.value,
            "configured_providers": [p.value for p in config.provider_configs.keys()],
            "configured_question_types": [
                q.value for q in config.question_type_configs.keys()
            ],
            "template_config": {
                "default_dir": config.default_template_dir,
                "cache_size": config.template_cache_size,
                "auto_reload": config.template_auto_reload,
            },
            "generation_settings": {
                "max_concurrent": config.max_concurrent_generations,
                "timeout": config.generation_timeout,
                "enable_caching": config.enable_content_caching,
            },
            "quality_settings": {
                "duplicate_detection": config.enable_duplicate_detection,
                "min_quality_score": config.min_question_quality_score,
                "auto_validation": config.enable_automatic_validation,
            },
            "monitoring": {
                "detailed_logging": config.enable_detailed_logging,
                "log_requests": config.log_llm_requests,
                "metrics_collection": config.enable_metrics_collection,
            },
        }

    def export_configuration(self, filepath: str) -> None:
        """
        Export current configuration to a file.

        Args:
            filepath: Path to export configuration to
        """
        config = self.get_config()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, indent=2, ensure_ascii=False, default=str)

        logger.info("configuration_exported", filepath=filepath)

    def import_configuration(self, filepath: str) -> None:
        """
        Import configuration from a file.

        Args:
            filepath: Path to import configuration from

        Raises:
            ValueError: If configuration file is invalid
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # Validate configuration
        config = QuestionGenerationConfig(**data)

        self._config = config

        # Save as current config file if one is set
        if self.config_file:
            self._save_configuration(config)

        logger.info("configuration_imported", filepath=filepath)

    def _load_configuration(self) -> QuestionGenerationConfig:
        """Load configuration from various sources."""
        config_data = {}

        # Start with default configuration
        base_config = self._create_default_configuration()
        config_data.update(base_config.dict())

        # Load from file if specified
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    file_config = json.load(f)
                config_data.update(file_config)

                logger.info(
                    "configuration_loaded_from_file", config_file=self.config_file
                )

            except Exception as e:
                logger.warning(
                    "configuration_file_load_failed",
                    config_file=self.config_file,
                    error=str(e),
                )

        # Override with environment variables
        env_overrides = self._load_environment_overrides()
        config_data.update(env_overrides)

        return QuestionGenerationConfig(**config_data)

    def _create_default_configuration(self) -> QuestionGenerationConfig:
        """Create default configuration."""
        config = QuestionGenerationConfig()

        # Add provider configurations based on available settings
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
            config.provider_configs[LLMProvider.OPENAI] = openai_config

        # Add mock provider for testing
        mock_config = LLMConfiguration(
            provider=LLMProvider.MOCK,
            model="mock-model",
            temperature=0.7,
            timeout=5.0,
            max_retries=0,
        )
        config.provider_configs[LLMProvider.MOCK] = mock_config

        # Configure question type specific settings
        mcq_config = WorkflowConfiguration(
            max_chunk_size=3000,
            min_chunk_size=100,
            max_questions_per_chunk=1,
            allow_duplicate_detection=True,
            quality_threshold=0.8,
            type_specific_settings={
                "enforce_unique_correct_answers": True,
                "require_plausible_distractors": True,
            },
        )
        config.question_type_configs[QuestionType.MULTIPLE_CHOICE] = mcq_config

        return config

    def _create_default_provider_config(
        self, provider: LLMProvider
    ) -> LLMConfiguration:
        """Create default configuration for a provider."""
        if provider == LLMProvider.OPENAI:
            if not settings.OPENAI_SECRET_KEY:
                raise ValueError("OpenAI API key not configured")

            return LLMConfiguration(
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                temperature=0.7,
                timeout=settings.LLM_API_TIMEOUT,
                max_retries=settings.MAX_RETRIES,
                provider_settings={"api_key": settings.OPENAI_SECRET_KEY},
            )

        elif provider == LLMProvider.MOCK:
            return LLMConfiguration(
                provider=LLMProvider.MOCK,
                model="mock-model",
                temperature=0.7,
                timeout=5.0,
                max_retries=0,
            )

        else:
            raise ValueError(
                f"No default configuration available for provider {provider}"
            )

    def _load_environment_overrides(self) -> dict[str, Any]:
        """Load configuration overrides from environment variables."""
        overrides: dict[str, Any] = {}

        # Provider settings
        if os.getenv("QUESTION_DEFAULT_PROVIDER"):
            overrides["default_provider"] = os.getenv("QUESTION_DEFAULT_PROVIDER")

        # Generation settings
        max_concurrent_str = os.getenv("QUESTION_MAX_CONCURRENT")
        if max_concurrent_str:
            overrides["max_concurrent_generations"] = int(max_concurrent_str)

        generation_timeout_str = os.getenv("QUESTION_GENERATION_TIMEOUT")
        if generation_timeout_str:
            overrides["generation_timeout"] = float(generation_timeout_str)

        # Quality settings
        min_quality_score_str = os.getenv("QUESTION_MIN_QUALITY_SCORE")
        if min_quality_score_str:
            overrides["min_question_quality_score"] = float(min_quality_score_str)

        # Monitoring settings
        detailed_logging_str = os.getenv("QUESTION_DETAILED_LOGGING")
        if detailed_logging_str:
            overrides["enable_detailed_logging"] = (
                detailed_logging_str.lower() == "true"
            )

        return overrides

    def _save_configuration(self, config: QuestionGenerationConfig) -> None:
        """Save configuration to file."""
        if not self.config_file:
            return

        # Ensure directory exists
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, indent=2, ensure_ascii=False, default=str)

    def _validate_configuration(self) -> None:
        """Validate the current configuration."""
        config = self._config

        if not config:
            raise ValueError("Configuration not loaded")

        # Validate default provider is configured
        if config.default_provider not in config.provider_configs:
            logger.warning(
                "default_provider_not_configured",
                provider=config.default_provider.value,
                available_providers=[p.value for p in config.provider_configs.keys()],
            )

        # Validate provider configurations
        for provider, provider_config in config.provider_configs.items():
            try:
                # This would validate using the provider's validate_configuration method
                # For now, just check basic consistency
                if provider_config.provider != provider:
                    raise ValueError(
                        f"Provider config mismatch: {provider} != {provider_config.provider}"
                    )
            except Exception as e:
                logger.error(
                    "provider_config_validation_failed",
                    provider=provider.value,
                    error=str(e),
                )


# Global configuration service instance
_default_config_service: ConfigurationService | None = None


def get_configuration_service() -> ConfigurationService:
    """Get the default configuration service instance."""
    global _default_config_service

    if _default_config_service is None:
        # Look for config file in standard locations
        config_file = os.getenv("QUESTION_CONFIG_FILE")
        if not config_file:
            # Default config file location
            backend_dir = Path(__file__).parent.parent.parent.parent
            config_file = str(backend_dir / "config" / "question_generation.json")

        _default_config_service = ConfigurationService(config_file)
        _default_config_service.initialize()

    return _default_config_service
