"""Question module with polymorphic question support and modular architecture."""

# Import router
from . import router

# Configuration
from .config import get_configuration_service

# DI Container
from .di import get_container

# Core components
from .models import Question, QuestionDifficulty, QuestionType
from .schemas import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GenerationRequest,
    GenerationResponse,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionStatistics,
    QuestionUpdateRequest,
)

# Services
from .services import (
    ContentProcessingService,
    GenerationOrchestrationService,
    QuestionPersistenceService,
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
    "QuestionStatistics",
    "BatchGenerationRequest",
    "BatchGenerationResponse",
    # Services
    "ContentProcessingService",
    "GenerationOrchestrationService",
    "QuestionPersistenceService",
    # Infrastructure
    "get_container",
    "get_configuration_service",
]
