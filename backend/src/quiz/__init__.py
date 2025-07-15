"""Quiz module for quiz management and operations."""

# Import router separately to avoid circular imports
from . import router
from .constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from .models import Quiz
from .orchestrator import (
    orchestrate_quiz_content_extraction,
    orchestrate_quiz_export_to_canvas,
    orchestrate_quiz_question_generation,
)
from .schemas import (
    QuizContentExtractionData,
    QuizCreate,
    QuizExportData,
    QuizOperationResult,
    QuizOperationStatus,
    QuizPublic,
    QuizQuestionGenerationData,
    QuizUpdate,
)
from .service import (
    create_quiz,
    delete_quiz,
    get_quiz_by_id,
    get_user_quizzes,
    prepare_content_extraction,
    prepare_question_generation,
)
from .validators import verify_quiz_ownership

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
    "orchestrate_quiz_content_extraction",
    "orchestrate_quiz_question_generation",
    "orchestrate_quiz_export_to_canvas",
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
