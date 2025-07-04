"""Quiz module constants and configuration values."""

# Default values
DEFAULT_QUESTION_COUNT = 100
MIN_QUESTION_COUNT = 1
MAX_QUESTION_COUNT = 200

DEFAULT_LLM_MODEL = "o3"
DEFAULT_LLM_TEMPERATURE = 1.0
MIN_LLM_TEMPERATURE = 0.0
MAX_LLM_TEMPERATURE = 2.0

# Error messages
ERROR_MESSAGES = {
    "quiz_not_found": "Quiz not found",
    "access_denied": "Access denied",
    "content_extraction_in_progress": "Content extraction is already in progress",
    "question_generation_in_progress": "Question generation is already in progress",
    "export_in_progress": "Quiz export is already in progress",
    "export_already_completed": "Quiz has already been exported to Canvas",
    "content_not_ready": "Content extraction must be completed before generating questions",
    "no_approved_questions": "Quiz has no approved questions to export",
    "creation_failed": "Failed to create quiz. Please try again.",
    "retrieval_failed": "Failed to retrieve quiz. Please try again.",
    "deletion_failed": "Failed to delete quiz. Please try again.",
    "extraction_trigger_failed": "Failed to trigger content extraction",
    "generation_trigger_failed": "Failed to trigger question generation",
    "export_trigger_failed": "Failed to start quiz export. Please try again.",
    "stats_retrieval_failed": "Failed to retrieve question stats. Please try again.",
}

# Success messages
SUCCESS_MESSAGES = {
    "content_extraction_started": "Content extraction started",
    "question_generation_started": "Question generation started",
    "export_started": "Quiz export started",
    "quiz_deleted": "Quiz deleted successfully",
}

# Validation limits
MAX_TITLE_LENGTH = 255
MIN_TITLE_LENGTH = 1

# Background task settings
TRANSACTION_ISOLATION_LEVEL = "REPEATABLE READ"
TRANSACTION_RETRIES = 3
