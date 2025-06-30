"""
Service dependency injection configuration for the application.

This module provides FastAPI dependency injection for all services,
ensuring proper service lifecycle management and testability.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.services.canvas_quiz_export import CanvasQuizExportService
from app.services.content_extraction import ContentExtractionService
from app.services.mcq_generation import MCQGenerationService


class ServiceContainer:
    """
    Service container for managing service dependencies and lifecycle.

    This class provides centralized service creation and configuration,
    making it easy to swap implementations for testing or different environments.
    """

    @staticmethod
    @lru_cache
    def get_mcq_generation_service() -> MCQGenerationService:
        """
        Get MCQ generation service instance.

        Returns:
            MCQGenerationService: Singleton service instance
        """
        return MCQGenerationService()

    @staticmethod
    def get_content_extraction_service(
        canvas_token: str,
        course_id: int,
    ) -> ContentExtractionService:
        """
        Get content extraction service instance with configuration.

        Args:
            canvas_token: Canvas API token
            course_id: Canvas course ID

        Returns:
            ContentExtractionService: Configured service instance
        """
        return ContentExtractionService(
            canvas_token=canvas_token,
            course_id=course_id,
        )

    @staticmethod
    def get_canvas_quiz_export_service(canvas_token: str) -> CanvasQuizExportService:
        """
        Get Canvas quiz export service instance with token.

        Args:
            canvas_token: Canvas API token

        Returns:
            CanvasQuizExportService: Configured service instance
        """
        return CanvasQuizExportService(canvas_token=canvas_token)


# Dependency type aliases for services that don't need runtime parameters
MCQServiceDep = Annotated[
    MCQGenerationService, Depends(ServiceContainer.get_mcq_generation_service)
]
