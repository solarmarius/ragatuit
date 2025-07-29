"""Main export service orchestrating PDF and QTI generation."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import ExportFormat, ExportMetadata, PDFExportOptions, QTIExportOptions

logger = logging.getLogger(__name__)


async def export_quiz_to_pdf(
    session: AsyncSession,  # noqa: ARG001
    quiz_id: UUID,
    options: PDFExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to PDF format for student distribution.

    Args:
        session: Database session (unused for now, but kept for API consistency)
        quiz_id: Quiz UUID to export
        options: PDF generation options

    Returns:
        Tuple of (PDF bytes, export metadata)

    Raises:
        ValueError: If quiz has no approved questions
        RuntimeError: If PDF generation fails
    """
    if options is None:
        options = PDFExportOptions()

    logger.info("Starting PDF export for quiz %s", quiz_id)

    # Get quiz and question data
    quiz_data = await _get_quiz_export_data(quiz_id)

    # Format questions for PDF (no answers)
    formatted_questions = []
    for question_data in quiz_data["questions"]:
        try:
            # The question_data already has the formatted export data
            # We need to extract the question type and re-format for PDF
            question_type_str = question_data.get("question_type")
            if not question_type_str:
                logger.warning("Question missing question_type field")
                continue

            # Import here to avoid circular imports
            from src.question.types import QuestionType, get_question_type_registry

            question_registry = get_question_type_registry()
            question_type = QuestionType(question_type_str)
            question_impl = question_registry.get_question_type(question_type)

            # Create a data object from the exported data
            typed_data = question_impl.validate_data(question_data)

            # Use the format_for_pdf method we added in Phase 3
            pdf_data = question_impl.format_for_pdf(typed_data)
            formatted_questions.append(pdf_data)
        except (KeyError, ValueError) as e:
            logger.warning("Failed to format question for PDF: %s", e)
            continue

    if not formatted_questions:
        raise ValueError("No questions could be formatted for PDF export")

    # Generate PDF using ReportLab
    from .pdf_generator import QuizPDFGenerator

    generator = QuizPDFGenerator(options)
    try:
        pdf_bytes = generator.generate_pdf(quiz_data["title"], formatted_questions)
    except Exception as e:
        logger.error("PDF generation failed for quiz %s: %s", quiz_id, e)
        raise RuntimeError(f"Failed to generate PDF: {e}") from e

    # Create metadata
    metadata = ExportMetadata(
        quiz_id=str(quiz_id),
        quiz_title=quiz_data["title"],
        question_count=len(formatted_questions),
        export_format=ExportFormat.PDF,
    )

    logger.info("PDF export completed for quiz %s", quiz_id)
    return pdf_bytes, metadata


async def export_quiz_to_qti_xml(
    session: AsyncSession,  # noqa: ARG001
    quiz_id: UUID,
    options: QTIExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to QTI XML format for LMS import.

    Args:
        session: Database session (unused for now, but kept for API consistency)
        quiz_id: Quiz UUID to export
        options: QTI generation options

    Returns:
        Tuple of (XML bytes, export metadata)

    Raises:
        ValueError: If quiz has no approved questions
        RuntimeError: If QTI generation fails
    """
    if options is None:
        options = QTIExportOptions()

    logger.info("Starting QTI XML export for quiz %s", quiz_id)

    # Get quiz and question data
    quiz_data = await _get_quiz_export_data(quiz_id)

    # Format questions for QTI (with answers)
    formatted_questions = []
    for question_data in quiz_data["questions"]:
        try:
            # The question_data already has the formatted export data
            # We need to extract the question type and re-format for QTI
            question_type_str = question_data.get("question_type")
            if not question_type_str:
                logger.warning("Question missing question_type field")
                continue

            # Import here to avoid circular imports
            from src.question.types import QuestionType, get_question_type_registry

            question_registry = get_question_type_registry()
            question_type = QuestionType(question_type_str)
            question_impl = question_registry.get_question_type(question_type)

            # Create a data object from the exported data
            typed_data = question_impl.validate_data(question_data)

            # Use the format_for_qti method we added in Phase 3
            qti_data = question_impl.format_for_qti(typed_data)
            formatted_questions.append(qti_data)
        except (KeyError, ValueError) as e:
            logger.warning("Failed to format question for QTI: %s", e)
            continue

    if not formatted_questions:
        raise ValueError("No questions could be formatted for QTI export")

    # Generate QTI XML using lxml
    from .qti_generator import QTIGenerator

    generator = QTIGenerator(options)
    try:
        xml_bytes = generator.generate_qti_xml(quiz_data["title"], formatted_questions)
    except Exception as e:
        logger.error("QTI generation failed for quiz %s: %s", quiz_id, e)
        raise RuntimeError(f"Failed to generate QTI XML: {e}") from e

    # Create metadata
    metadata = ExportMetadata(
        quiz_id=str(quiz_id),
        quiz_title=quiz_data["title"],
        question_count=len(formatted_questions),
        export_format=ExportFormat.QTI_XML,
    )

    logger.info("QTI XML export completed for quiz %s", quiz_id)
    return xml_bytes, metadata


async def _get_quiz_export_data(quiz_id: UUID) -> dict[str, Any]:
    """
    Get quiz and question data for export.

    Args:
        quiz_id: Quiz UUID

    Returns:
        Dictionary with quiz title and approved questions

    Raises:
        ValueError: If no approved questions found
    """
    # Import question service to get approved questions
    from src.question import service as question_service

    # Get approved questions using existing service
    questions_data = await question_service.prepare_questions_for_export(quiz_id)

    if not questions_data:
        raise ValueError("No approved questions found for export")

    # For now, use a placeholder title - we'll get the actual title from quiz later
    # In a full implementation, we'd need to get the quiz title from the database
    quiz_title = f"Quiz {quiz_id}"

    return {
        "title": quiz_title,
        "questions": questions_data,
    }
