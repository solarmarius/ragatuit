"""Quiz schemas for validation and serialization."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlmodel import Field, SQLModel


class QuizStatus(str, Enum):
    """Consolidated status values for quiz workflow."""

    CREATED = "created"
    EXTRACTING_CONTENT = "extracting_content"
    GENERATING_QUESTIONS = "generating_questions"
    READY_FOR_REVIEW = "ready_for_review"
    EXPORTING_TO_CANVAS = "exporting_to_canvas"
    PUBLISHED = "published"
    FAILED = "failed"


class FailureReason(str, Enum):
    """Specific failure reasons for detailed error tracking."""

    CONTENT_EXTRACTION_ERROR = "content_extraction_error"
    NO_CONTENT_FOUND = "no_content_found"
    LLM_GENERATION_ERROR = "llm_generation_error"
    NO_QUESTIONS_GENERATED = "no_questions_generated"
    CANVAS_EXPORT_ERROR = "canvas_export_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"


# Legacy enum for backwards compatibility during migration
class Status(str, Enum):
    """Legacy status values - will be removed after migration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class QuizCreate(SQLModel):
    """Schema for creating a new quiz."""

    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[int, str]
    title: str = Field(min_length=1, max_length=255)
    question_count: int = Field(default=100, ge=1, le=200)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)


class QuizUpdate(SQLModel):
    """Schema for updating quiz settings."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    question_count: int | None = Field(default=None, ge=1, le=200)
    llm_model: str | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class QuizPublic(SQLModel):
    """Public quiz schema for API responses."""

    id: UUID
    owner_id: UUID
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, str]
    title: str
    question_count: int
    llm_model: str
    llm_temperature: float
    status: QuizStatus
    failure_reason: FailureReason | None = None
    last_status_update: datetime
    extracted_content: dict[str, Any] | None
    content_extracted_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    canvas_quiz_id: str | None
    exported_at: datetime | None


class QuizStatusUpdate(SQLModel):
    """Schema for updating quiz status."""

    status: QuizStatus
    failure_reason: FailureReason | None = None


class QuizRetryRequest(SQLModel):
    """Request to retry a failed quiz."""

    pass  # Empty body for now, could add options later


class QuizStatusFilter(SQLModel):
    """Filter quizzes by status."""

    status: QuizStatus | None = None
    failure_reason: FailureReason | None = None


# Legacy schemas for backwards compatibility during migration
class QuizContentUpdate(SQLModel):
    """Legacy schema for updating quiz content extraction results."""

    content_extraction_status: str
    extracted_content: dict[str, Any] | None = None
    content_extracted_at: datetime | None = None


class QuizGenerationUpdate(SQLModel):
    """Legacy schema for updating quiz generation status."""

    llm_generation_status: str


class QuizExportUpdate(SQLModel):
    """Legacy schema for updating quiz export results."""

    export_status: str
    canvas_quiz_id: str | None = None
    exported_at: datetime | None = None


# Flow operation schemas
class QuizContentExtractionData(SQLModel):
    """Typed data for content extraction flow operations."""

    quiz_id: UUID
    course_id: int
    module_ids: list[int]
    canvas_token: str


class QuizQuestionGenerationData(SQLModel):
    """Typed data for question generation flow operations."""

    quiz_id: UUID
    target_question_count: int
    llm_model: str
    llm_temperature: float


class QuizExportData(SQLModel):
    """Typed data for quiz export flow operations."""

    quiz_id: UUID
    canvas_token: str


class QuizOperationResult(SQLModel):
    """Standardized result for quiz operations."""

    success: bool
    message: str
    quiz_id: UUID | None = None
    operation_type: str | None = None
    error_details: dict[str, Any] | None = None
    timestamp: datetime | None = None


class QuizOperationStatus(SQLModel):
    """Status information for ongoing quiz operations."""

    quiz_id: UUID
    status: QuizStatus
    failure_reason: FailureReason | None = None
    last_updated: datetime | None = None
