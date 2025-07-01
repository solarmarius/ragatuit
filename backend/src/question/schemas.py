"""Question schemas for validation and serialization with polymorphic support."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .types import QuestionDifficulty, QuestionType


class QuestionCreateRequest(BaseModel):
    """Schema for creating a new question."""

    quiz_id: uuid.UUID
    question_type: QuestionType
    question_data: dict[str, Any] = Field(description="Question type-specific data")
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None

    class Config:
        use_enum_values = True


class QuestionUpdateRequest(BaseModel):
    """Schema for updating a question."""

    question_data: dict[str, Any] | None = Field(
        default=None, description="Updated question data"
    )
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None

    class Config:
        use_enum_values = True


class QuestionResponse(BaseModel):
    """Public question schema for API responses."""

    id: uuid.UUID
    quiz_id: uuid.UUID
    question_type: QuestionType
    question_data: dict[str, Any]
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None
    is_approved: bool
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    canvas_item_id: str | None = None

    class Config:
        use_enum_values = True


class GenerationRequest(BaseModel):
    """Schema for question generation requests."""

    quiz_id: uuid.UUID
    question_type: QuestionType
    target_count: int = Field(
        ge=1, le=100, description="Number of questions to generate"
    )
    difficulty: QuestionDifficulty | None = None
    tags: list[str] | None = None
    custom_instructions: str | None = Field(default=None, max_length=500)

    # Provider and workflow options
    provider_name: str | None = None
    workflow_name: str | None = None
    template_name: str | None = None

    class Config:
        use_enum_values = True


class GenerationResponse(BaseModel):
    """Schema for question generation responses."""

    success: bool
    questions_generated: int
    target_questions: int
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


class QuestionStatistics(BaseModel):
    """Schema for question statistics."""

    total_questions: int
    approved_questions: int
    approval_rate: float
    by_question_type: dict[str, dict[str, int | float]]


class BatchGenerationRequest(BaseModel):
    """Schema for batch question generation."""

    requests: list[GenerationRequest] = Field(min_length=1, max_length=10)


class BatchGenerationResponse(BaseModel):
    """Schema for batch generation responses."""

    results: list[GenerationResponse]
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_questions_generated: int
