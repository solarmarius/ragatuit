"""Question module with polymorphic question support and modular architecture."""

# Import router
# Configuration
from . import router, service

# Configuration
from .config import get_configuration_service

# Core components
from .models import Question, QuestionDifficulty, QuestionType
from .schemas import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GenerationRequest,
    GenerationResponse,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
)

# Services
from .services import (
    ContentProcessingService,
    QuestionGenerationService,
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
    "GenerationRequest",
    "GenerationResponse",
    "BatchGenerationRequest",
    "BatchGenerationResponse",
    # Services
    "ContentProcessingService",
    "QuestionGenerationService",
    "service",
    # Infrastructure
    "get_configuration_service",
]
