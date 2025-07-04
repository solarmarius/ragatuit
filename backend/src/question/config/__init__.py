"""Configuration module for question generation system."""

from .service import (
    ConfigurationService,
    QuestionGenerationConfig,
    get_configuration_service,
)

__all__ = [
    "ConfigurationService",
    "QuestionGenerationConfig",
    "get_configuration_service",
]
