"""Main export service orchestrating PDF and QTI generation."""

import logging
from typing import Any
from uuid import UUID

from .schemas import ExportFormat, ExportMetadata, PDFExportOptions, QTIExportOptions

logger = logging.getLogger(__name__)


async def export_quiz_to_pdf(
    quiz_id: UUID,
    options: PDFExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to PDF format for student distribution.

    Args:
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

            # Remove metadata fields that are not part of the question data model
            clean_question_data = {
                k: v
                for k, v in question_data.items()
                if k not in ("question_type", "id")
            }

            # Create a data object from the clean exported data
            typed_data = question_impl.validate_data(clean_question_data)

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
    quiz_id: UUID,
    options: QTIExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to QTI XML format for LMS import.

    Args:
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

            # Remove metadata fields that are not part of the question data model
            clean_question_data = {
                k: v
                for k, v in question_data.items()
                if k not in ("question_type", "id")
            }

            # Create a data object from the clean exported data
            typed_data = question_impl.validate_data(clean_question_data)

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
        ValueError: If quiz not found or no approved questions found
    """
    # Import dependencies
    from src.database import get_async_session
    from src.question import service as question_service
    from src.quiz.models import Quiz

    # Get quiz title from database
    async with get_async_session() as session:
        quiz = await session.get(Quiz, quiz_id)
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")
        quiz_title = quiz.title

    # Get approved questions using existing service
    questions_data = await question_service.prepare_questions_for_export(quiz_id)

    if not questions_data:
        raise ValueError("No approved questions found for export")

    return {
        "title": quiz_title,
        "questions": questions_data,
    }
