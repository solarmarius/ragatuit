"""
Dependencies for Canvas module.
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import CanvasToken, CurrentUser
from app.deps import SessionDep

from .service import CanvasQuizExportService, ContentExtractionService


def get_content_extraction_service(
    canvas_token: CanvasToken,
    course_id: int,
) -> ContentExtractionService:
    """
    Factory function to create ContentExtractionService.

    Args:
        canvas_token: Valid Canvas API token
        course_id: Canvas course ID

    Returns:
        ContentExtractionService instance
    """
    return ContentExtractionService(canvas_token, course_id)


def get_quiz_export_service(
    canvas_token: CanvasToken,
) -> CanvasQuizExportService:
    """
    Factory function to create CanvasQuizExportService.

    Args:
        canvas_token: Valid Canvas API token

    Returns:
        CanvasQuizExportService instance
    """
    return CanvasQuizExportService(canvas_token)


# Type annotations for dependency injection
ContentExtractionServiceDep = Annotated[
    ContentExtractionService, Depends(get_content_extraction_service)
]
QuizExportServiceDep = Annotated[
    CanvasQuizExportService, Depends(get_quiz_export_service)
]
