"""
Pydantic schemas for Canvas LMS integration.
"""

from typing import Any
from uuid import UUID

from sqlmodel import Field, SQLModel

from src.content_extraction.models import ProcessedContent


# Canvas entity schemas
class CanvasCourse(SQLModel):
    """Canvas course information."""

    id: int
    name: str


class CanvasModule(SQLModel):
    """Canvas module (chapter/section) information."""

    id: int
    name: str


class CanvasModuleItem(SQLModel):
    """Canvas module item (page/file/assignment) information."""

    id: int
    title: str
    type: str  # 'Page', 'File', 'Assignment', etc.
    url: str | None = None
    page_url: str | None = None
    file_id: int | None = None


class CanvasPage(SQLModel):
    """Canvas page content."""

    id: int
    title: str
    body: str
    url: str


class CanvasFile(SQLModel):
    """Canvas file information."""

    id: int
    display_name: str
    url: str
    content_type: str
    size: int


# Content extraction schemas
class ExtractedContent(SQLModel):
    """Extracted content from Canvas modules."""

    module_contents: dict[str, list[dict[str, str]]] = Field(
        default_factory=dict,
        description="Dictionary mapping module names to lists of content items",
    )
    total_content_size: int = Field(
        default=0, description="Total size of extracted content in bytes"
    )
    extraction_timestamp: str = Field(
        description="ISO format timestamp of when content was extracted"
    )


# Quiz export schemas
class QuizExportRequest(SQLModel):
    """Request to export a quiz to Canvas."""

    quiz_id: str = Field(description="UUID of the quiz to export")


class QuizExportResponse(SQLModel):
    """Response from quiz export operation."""

    success: bool
    canvas_quiz_id: str | None = None
    message: str
    exported_questions: int = 0
    export_timestamp: str | None = None
    already_exported: bool = False
    export_in_progress: bool = False
    errors: list[dict[str, Any]] = Field(default_factory=list)


# Canvas API response schemas
class CanvasQuizResponse(SQLModel):
    """Response from Canvas quiz creation API."""

    id: str
    title: str
    assignment_id: str | None = None
    points_possible: int | None = None


class CanvasQuizItemResponse(SQLModel):
    """Response from Canvas quiz item creation API."""

    id: str
    position: int
    points_possible: int = 1


# Canvas OAuth config schema
class CanvasConfigResponse(SQLModel):
    """Canvas OAuth configuration response."""

    authorization_url: str
    client_id: str
    redirect_uri: str
    scope: str


# Internal flow data models for type safety


class QuestionData(SQLModel):
    """Typed question data for export operations."""

    id: UUID
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str


class QuizExportData(SQLModel):
    """Typed data for quiz export flow operations."""

    course_id: int
    title: str
    questions: list[QuestionData]
    already_exported: bool = False
    canvas_quiz_id: str | None = None


class ContentExtractionResult(SQLModel):
    """Typed content extraction result from Canvas modules."""

    module_contents: dict[str, list[ProcessedContent]]
    total_content_size: int
    modules_processed: int
    total_word_count: int
    total_pages: int
    average_words_per_page: int
    extracted_at: str  # ISO timestamp


class CanvasItemExportResult(SQLModel):
    """Result of exporting a single Canvas quiz item."""

    success: bool
    question_id: UUID
    item_id: str | None = None
    position: int
    error: str | None = None
