"""Quiz schemas for validation and serialization."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import field_validator
from sqlmodel import Field, SQLModel

# Import QuizLanguage from question types to avoid circular dependency
from src.question.types import QuizLanguage


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


class ModuleSelection(SQLModel):
    """Schema for module selection with question count."""

    name: str
    question_count: int = Field(ge=1, le=20, description="Questions per module (1-20)")


class QuizCreate(SQLModel):
    """Schema for creating a new quiz with module-based questions."""

    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, ModuleSelection]
    title: str = Field(min_length=1, max_length=255)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    language: QuizLanguage = Field(default=QuizLanguage.ENGLISH)

    @field_validator("selected_modules")
    def validate_modules(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate selected modules structure."""
        if not v:
            raise ValueError("At least one module must be selected")

        # Validate each module has required fields
        for module_id, module_data in v.items():
            if not isinstance(module_data, dict) and not isinstance(
                module_data, ModuleSelection
            ):
                raise ValueError(f"Module {module_id} must be a valid module selection")

            # Convert to dict if ModuleSelection object
            if isinstance(module_data, ModuleSelection):
                module_dict = module_data.model_dump()
            else:
                module_dict = module_data

            if "name" not in module_dict or "question_count" not in module_dict:
                raise ValueError(f"Module {module_id} missing required fields")

            if not 1 <= module_dict["question_count"] <= 20:
                raise ValueError(f"Module {module_id} question count must be 1-20")

        return v

    @property
    def total_question_count(self) -> int:
        """Calculate total questions across all modules."""
        total = 0
        for module in self.selected_modules.values():
            if isinstance(module, ModuleSelection):
                total += module.question_count
            elif isinstance(module, dict) and "question_count" in module:
                total += module["question_count"]
        return total


class QuizUpdate(SQLModel):
    """Schema for updating quiz settings."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    llm_model: str | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    language: QuizLanguage | None = None


class QuizPublic(SQLModel):
    """Public quiz schema for API responses."""

    id: UUID
    owner_id: UUID
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, dict[str, Any]]
    title: str
    question_count: int
    llm_model: str
    llm_temperature: float
    language: QuizLanguage
    status: QuizStatus
    failure_reason: FailureReason | None = None
    last_status_update: datetime
    extracted_content: dict[str, Any] | None
    content_extracted_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    canvas_quiz_id: str | None
    exported_at: datetime | None
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    module_question_distribution: dict[str, int] = Field(default_factory=dict)


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
    language: QuizLanguage


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
