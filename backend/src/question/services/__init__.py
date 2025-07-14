"""Services module for question generation system."""

# Content processing functions (functional approach)
from .content_service import (
    get_content_from_quiz,
    get_content_statistics,
    prepare_and_validate_content,
    prepare_content_for_generation,
    validate_content_quality,
    validate_module_content,
)

# Question generation service (class-based)
from .generation_service import QuestionGenerationService

__all__ = [
    # Content processing functions
    "get_content_from_quiz",
    "prepare_content_for_generation",
    "prepare_and_validate_content",
    "validate_content_quality",
    "validate_module_content",
    "get_content_statistics",
    # Generation service
    "QuestionGenerationService",
]
