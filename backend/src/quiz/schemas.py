"""Quiz schemas for validation and serialization."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import field_validator
from sqlmodel import Field, SQLModel

# Import QuizLanguage, QuestionType, and QuestionDifficulty from question types to avoid circular dependency
from src.question.types import QuestionDifficulty, QuestionType, QuizLanguage


class QuizStatus(str, Enum):
    """Consolidated status values for quiz workflow."""

    CREATED = "created"
    EXTRACTING_CONTENT = "extracting_content"
    GENERATING_QUESTIONS = "generating_questions"
    READY_FOR_REVIEW = "ready_for_review"
    READY_FOR_REVIEW_PARTIAL = "ready_for_review_partial"
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


class QuizTone(str, Enum):
    """Tone of voice options for quiz question generation."""

    ACADEMIC = "academic"
    CASUAL = "casual"
    ENCOURAGING = "encouraging"
    PROFESSIONAL = "professional"


class QuestionBatch(SQLModel):
    """Schema for a batch of questions of a specific type and difficulty."""

    question_type: QuestionType
    count: int = Field(ge=1, le=20, description="Number of questions (1-20)")
    difficulty: QuestionDifficulty


class ModuleSelection(SQLModel):
    """Schema for module selection with multiple question type batches."""

    name: str
    question_batches: list[QuestionBatch] = Field(
        min_length=1, max_length=4, description="Question type batches (1-4 per module)"
    )
    source_type: str = Field(
        default="canvas", description="Module source: 'canvas' or 'manual'"
    )
    # Optional fields for manual modules (populated when source_type is 'manual')
    content: str | None = Field(
        default=None, description="Full content for manual modules"
    )
    word_count: int | None = Field(
        default=None, description="Word count for manual modules"
    )
    processing_metadata: dict[str, Any] | None = Field(
        default=None, description="Processing metadata for manual modules"
    )
    content_type: str | None = Field(
        default=None,
        description="Content type for manual modules (e.g., 'text', 'pdf')",
    )

    @property
    def total_questions(self) -> int:
        """Calculate total questions across all batches."""
        return sum(batch.count for batch in self.question_batches)


class ManualModuleCreate(SQLModel):
    """Schema for creating a manual module with file upload or text content."""

    name: str = Field(min_length=1, max_length=255, description="Module name")
    text_content: str | None = Field(default=None, description="Direct text content")

    @field_validator("text_content")
    def validate_content_provided(cls, v: str | None) -> str | None:
        """Ensure at least text content is provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Text content cannot be empty")
        return v


class ManualModuleResponse(SQLModel):
    """Response schema for manual module creation."""

    module_id: str = Field(description="Generated manual module ID")
    name: str = Field(description="Module name")
    content_preview: str = Field(description="Preview of processed content")
    full_content: str = Field(description="Full processed content")
    word_count: int = Field(description="Word count of processed content")
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Processing details"
    )


class QuizCreate(SQLModel):
    """Schema for creating a new quiz with module-based questions."""

    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, ModuleSelection]
    title: str = Field(min_length=1, max_length=255)
    llm_model: str = Field(default="gpt-5-mini-2025-08-07")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    language: QuizLanguage = Field(default=QuizLanguage.ENGLISH)
    tone: QuizTone = Field(default=QuizTone.ACADEMIC)

    @field_validator("selected_modules")
    def validate_modules(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate selected modules structure supporting both Canvas and manual modules."""
        if not v:
            raise ValueError("At least one module must be selected")

        for module_id, module_data in v.items():
            if not isinstance(module_data, dict | ModuleSelection):
                raise ValueError(f"Module {module_id} must be a valid module selection")

            # Convert to ModuleSelection if dict
            if isinstance(module_data, dict):
                try:
                    module_selection = ModuleSelection(**module_data)
                except Exception as e:
                    raise ValueError(f"Module {module_id} has invalid structure: {e}")
            else:
                module_selection = module_data

            # Validate source_type
            if hasattr(module_selection, "source_type"):
                if module_selection.source_type not in ["canvas", "manual"]:
                    raise ValueError(
                        f"Module {module_id} source_type must be 'canvas' or 'manual'"
                    )

                # Manual modules should have manual_ prefix
                if (
                    module_selection.source_type == "manual"
                    and not module_id.startswith("manual_")
                ):
                    raise ValueError(
                        f"Manual module {module_id} must have 'manual_' prefix"
                    )

                # Manual modules must have content fields
                if module_selection.source_type == "manual":
                    if not module_selection.content:
                        raise ValueError(f"Manual module {module_id} must have content")
                    if (
                        module_selection.word_count is None
                        or module_selection.word_count <= 0
                    ):
                        raise ValueError(
                            f"Manual module {module_id} must have a valid word count"
                        )

            # Validate batch count
            if len(module_selection.question_batches) > 4:
                raise ValueError(
                    f"Module {module_id} cannot have more than 4 question batches"
                )

            # Validate no duplicate question type + difficulty combinations in same module
            batch_combinations = [
                (batch.question_type, batch.difficulty)
                for batch in module_selection.question_batches
            ]
            if len(batch_combinations) != len(set(batch_combinations)):
                raise ValueError(
                    f"Module {module_id} has duplicate question type and difficulty combinations"
                )

        return v


class QuizUpdate(SQLModel):
    """Schema for updating quiz settings."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    llm_model: str | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    language: QuizLanguage | None = None
    # Removed: question_type field


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
    tone: QuizTone
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
    # Removed: target_question_count (now per batch)
    llm_model: str
    llm_temperature: float
    language: QuizLanguage
    # Removed: question_type (now per batch)


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
