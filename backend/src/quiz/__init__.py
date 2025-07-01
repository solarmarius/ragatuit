"""Quiz module for quiz management and operations."""

# Import router separately to avoid circular imports
from . import router
from .constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from .flows import (
    quiz_content_extraction_flow,
    quiz_export_background_flow,
    quiz_question_generation_flow,
)
from .models import Quiz
from .schemas import (
    QuizContentExtractionData,
    QuizCreate,
    QuizExportData,
    QuizOperationResult,
    QuizOperationStatus,
    QuizPublic,
    QuizQuestionGenerationData,
    QuizUpdate,
    Status,
)
from .service import (
    create_quiz,
    delete_quiz,
    get_quiz_by_id,
    get_user_quizzes,
    prepare_content_extraction,
    prepare_question_generation,
    verify_quiz_ownership,
)

__all__ = [
    "router",
    "Quiz",
    "QuizCreate",
    "QuizPublic",
    "QuizUpdate",
    "Status",
    "QuizContentExtractionData",
    "QuizQuestionGenerationData",
    "QuizExportData",
    "QuizOperationResult",
    "QuizOperationStatus",
    "quiz_content_extraction_flow",
    "quiz_question_generation_flow",
    "quiz_export_background_flow",
    "ERROR_MESSAGES",
    "SUCCESS_MESSAGES",
    "create_quiz",
    "delete_quiz",
    "get_quiz_by_id",
    "get_user_quizzes",
    "prepare_content_extraction",
    "prepare_question_generation",
    "verify_quiz_ownership",
]
