"""Question module with polymorphic question support and modular architecture."""

# Import router
# Configuration
from . import router, service

# Configuration
from .config import get_configuration_service

# Core components
from .models import Question, QuestionDifficulty, QuestionType
from .schemas import (
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
)

# Services
from .services import (
    # Generation service
    QuestionGenerationService,
    # Content processing functions
    get_content_from_quiz,
    get_content_statistics,
    prepare_and_validate_content,
    prepare_content_for_generation,
    validate_content_quality,
    validate_module_content,
)

__all__ = [
    # Router
    "router",
    # Models and Types
    "Question",
    "QuestionType",
    "QuestionDifficulty",
    # Schemas
    "QuestionCreateRequest",
    "QuestionResponse",
    "QuestionUpdateRequest",
    # Content processing functions
    "get_content_from_quiz",
    "prepare_content_for_generation",
    "prepare_and_validate_content",
    "validate_content_quality",
    "validate_module_content",
    "get_content_statistics",
    # Generation service
    "QuestionGenerationService",
    "service",
    # Infrastructure
    "get_configuration_service",
]
