"""
Canvas module orchestration flows.

This module orchestrates Canvas operations using functional composition:
- Content extraction flows for module content processing
- Quiz export flows for exporting quizzes to Canvas LMS
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.content_extraction import (
    ProcessedContent,
    RawContent,
    get_content_processor,
)
from src.content_extraction.constants import (
    MAX_FILE_SIZE,
    MAX_PAGES_PER_MODULE,
    MAX_TOTAL_CONTENT_SIZE,
)
from src.exceptions import ResourceNotFoundError, ValidationError
from src.logging_config import get_logger

# QuizService imported locally to avoid circular imports
from .service import (
    create_canvas_quiz,
    create_canvas_quiz_items,
    download_canvas_file_content,
    fetch_canvas_file_info,
    fetch_canvas_module_items,
    fetch_canvas_page_content,
)

logger = get_logger("content_extraction_flows")


async def extract_content_for_modules(
    canvas_token: str, course_id: int, module_ids: list[int]
) -> dict[str, list[dict[str, str]]]:
    """
    Extract content from all pages and files in the specified Canvas modules.

    This is the main public API that maintains backward compatibility with
    the original ContentExtractionService.extract_content_for_modules() method.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        module_ids: List of Canvas module IDs to extract content from

    Returns:
        Dict mapping module_id to list of extracted content:
        {
            "module_123": [
                {"title": "Page Title", "content": "cleaned text content", "type": "page"},
                {"title": "File Title", "content": "extracted text", "type": "file"},
                ...
            ]
        }
    """
    extracted_content: dict[str, list[dict[str, str]]] = {}
    total_content_size = 0
    max_total_content_size = MAX_TOTAL_CONTENT_SIZE

    for module_id in module_ids:
        logger.info(
            "content_extraction_module_started",
            course_id=course_id,
            module_id=module_id,
        )

        try:
            # Process content for this module
            module_content, module_size = await process_module_content(
                canvas_token=canvas_token,
                course_id=course_id,
                module_id=module_id,
                remaining_content_size=max_total_content_size - total_content_size,
            )

            # Track total content size
            total_content_size += module_size
            extracted_content[f"module_{module_id}"] = module_content

            logger.info(
                "content_extraction_module_completed",
                course_id=course_id,
                module_id=module_id,
                extracted_pages=len(module_content),
                content_size=module_size,
            )

        except Exception as e:
            logger.error(
                "content_extraction_module_failed",
                course_id=course_id,
                module_id=module_id,
                error=str(e),
                exc_info=True,
            )
            # Continue with other modules even if one fails
            extracted_content[f"module_{module_id}"] = []
            continue

    return extracted_content


async def process_module_content(
    canvas_token: str,
    course_id: int,
    module_id: int,
    remaining_content_size: int,
) -> tuple[list[dict[str, str]], int]:
    """
    Process all content items in a Canvas module.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        module_id: Canvas module ID
        remaining_content_size: Remaining allowed content size in bytes

    Returns:
        Tuple of (extracted_content_list, total_content_size)
    """
    # Fetch module items using Canvas API
    module_items = await fetch_canvas_module_items(canvas_token, course_id, module_id)

    # Filter for supported content types (Page and File)
    content_items = [
        item
        for item in module_items
        if (item.get("type") == "Page" and item.get("page_url"))
        or (item.get("type") == "File" and item.get("content_id"))
    ]

    # Apply per-module content limits
    max_pages_per_module = MAX_PAGES_PER_MODULE
    if len(content_items) > max_pages_per_module:
        logger.warning(
            "content_extraction_items_limited",
            course_id=course_id,
            module_id=module_id,
            total_items=len(content_items),
            limit=max_pages_per_module,
        )
        content_items = content_items[:max_pages_per_module]

    logger.info(
        "content_extraction_items_found",
        course_id=course_id,
        module_id=module_id,
        total_items=len(module_items),
        content_items=len(content_items),
        page_items=len([i for i in content_items if i.get("type") == "Page"]),
        file_items=len([i for i in content_items if i.get("type") == "File"]),
    )

    # Extract content from each item
    module_content = []
    module_content_size = 0

    for content_item in content_items:
        # Check content size limits
        if module_content_size >= remaining_content_size:
            logger.warning(
                "content_extraction_size_limit_reached",
                course_id=course_id,
                module_id=module_id,
                current_size=module_content_size,
                limit=remaining_content_size,
            )
            break

        try:
            # Extract content from individual item
            item_content = await extract_canvas_item_content(
                canvas_token=canvas_token,
                course_id=course_id,
                content_item=content_item,
            )

            if item_content:
                content_size = len(item_content.get("content", ""))
                module_content_size += content_size
                module_content.append(item_content)

        except Exception as e:
            logger.warning(
                "content_extraction_item_failed",
                course_id=course_id,
                module_id=module_id,
                item_type=content_item.get("type"),
                item_title=content_item.get("title"),
                error=str(e),
            )
            # Continue with other items even if one fails
            continue

    return module_content, module_content_size


async def extract_canvas_item_content(
    canvas_token: str,
    course_id: int,
    content_item: dict[str, Any],
) -> dict[str, str] | None:
    """
    Extract content from a single Canvas content item (Page or File).

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        content_item: Canvas content item dict with type and metadata

    Returns:
        Extracted content dict or None if extraction fails
    """
    item_type = content_item.get("type")

    if item_type == "Page":
        return await extract_page_content_flow(canvas_token, course_id, content_item)
    elif item_type == "File":
        return await extract_file_content_flow(canvas_token, course_id, content_item)
    else:
        logger.warning(
            "unsupported_content_item_type",
            course_id=course_id,
            item_type=item_type,
            item_title=content_item.get("title"),
        )
        return None


async def extract_page_content_flow(
    canvas_token: str,
    course_id: int,
    page_item: dict[str, Any],
) -> dict[str, str] | None:
    """
    Flow for extracting content from a Canvas page.

    Steps:
    1. Fetch page content from Canvas API
    2. Convert to RawContent for domain processing
    3. Process using content extraction domain
    4. Convert back to legacy API format
    """
    page_url = page_item.get("page_url")
    if not page_url:
        return None

    try:
        # Step 1: Fetch page content using Canvas API
        page_data = await fetch_canvas_page_content(canvas_token, course_id, page_url)
        if not page_data or not page_data.get("body"):
            logger.info(
                "content_extraction_page_empty",
                course_id=course_id,
                page_url=page_url,
            )
            return None

        # Step 2: Convert to RawContent for domain processing
        raw_content = convert_page_to_raw_content(page_data, course_id, page_url)

        # Step 3: Process using content extraction domain
        processed_contents = await process_raw_content_batch([raw_content])
        if not processed_contents:
            logger.info(
                "content_extraction_page_processing_failed",
                course_id=course_id,
                page_url=page_url,
            )
            return None

        # Step 4: Convert back to legacy API format
        return convert_processed_to_legacy_format(processed_contents[0], "page")

    except Exception as e:
        logger.warning(
            "content_extraction_page_error",
            course_id=course_id,
            page_url=page_url,
            error=str(e),
        )
        return None


async def extract_file_content_flow(
    canvas_token: str,
    course_id: int,
    file_item: dict[str, Any],
) -> dict[str, str] | None:
    """
    Flow for extracting content from a Canvas file.

    Steps:
    1. Get file metadata from Canvas API
    2. Check file type and size limits
    3. Download file content
    4. Convert to RawContent for domain processing
    5. Process using content extraction domain
    6. Convert back to legacy API format
    """
    file_id = file_item.get("content_id")
    if not file_id:
        logger.warning(
            "file_extraction_no_content_id",
            course_id=course_id,
            file_title=file_item.get("title"),
        )
        return None

    try:
        # Step 1: Get file metadata using Canvas API
        file_info = await fetch_canvas_file_info(canvas_token, course_id, file_id)
        if not file_info:
            return None

        # Step 2: Check file type and size limits
        if not is_supported_file_type(file_info):
            content_type = file_info.get("content-type", "")
            mime_class = file_info.get("mime_class", "")
            logger.info(
                "file_extraction_unsupported_type",
                course_id=course_id,
                file_id=file_id,
                content_type=content_type,
                mime_class=mime_class,
            )
            return None

        if not is_file_size_allowed(file_info, course_id, file_id):
            return None

        # Step 3: Download file content
        download_url = file_info.get("url")
        if not download_url:
            logger.error(
                "file_extraction_no_download_url",
                course_id=course_id,
                file_id=file_id,
            )
            return None

        file_content = await download_canvas_file_content(download_url)
        if not file_content:
            logger.warning(
                "file_extraction_download_failed",
                course_id=course_id,
                file_id=file_id,
            )
            return None

        # Step 4: Convert to RawContent for domain processing
        raw_content = convert_file_to_raw_content(
            file_content, file_info, file_item, course_id, file_id
        )

        # Step 5: Process using content extraction domain
        processed_contents = await process_raw_content_batch([raw_content])
        if not processed_contents:
            logger.info(
                "file_extraction_processing_failed",
                course_id=course_id,
                file_id=file_id,
            )
            return None

        # Step 6: Convert back to legacy API format
        content_type = file_info.get("content-type", "")
        result = convert_processed_to_legacy_format(processed_contents[0], "file")
        result["content_type"] = content_type  # Add file-specific field
        return result

    except Exception as e:
        logger.error(
            "file_extraction_failed",
            course_id=course_id,
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        return None


# Data conversion utilities


def convert_page_to_raw_content(
    page_data: dict[str, Any], course_id: int, page_url: str
) -> RawContent:
    """Convert Canvas page data to RawContent for domain processing."""
    return RawContent(
        content=page_data.get("body", ""),
        content_type="html",
        title=page_data.get("title", "Untitled Page"),
        metadata={
            "source": "canvas_page",
            "page_url": page_url,
            "course_id": course_id,
        },
    )


def convert_file_to_raw_content(
    file_content: bytes,
    file_info: dict[str, Any],
    file_item: dict[str, Any],
    course_id: int,
    file_id: int,
) -> RawContent:
    """Convert Canvas file data to RawContent for domain processing."""
    content_type = file_info.get("content-type", "")

    # Determine content type for processing
    if "pdf" in content_type.lower() or "application/pdf" in content_type:
        processing_type = "pdf"
    else:
        processing_type = "text"

    # Convert bytes to string for RawContent model compatibility
    # The PDF processor will convert back to bytes using latin-1 encoding
    content_str = (
        file_content.decode("latin-1")
        if isinstance(file_content, bytes)
        else str(file_content)
    )

    return RawContent(
        content=content_str,
        content_type=processing_type,
        title=file_info.get("display_name", file_item.get("title", "Untitled")),
        metadata={
            "source": "canvas_file",
            "file_id": file_id,
            "course_id": course_id,
            "original_content_type": content_type,
            "file_size": file_info.get("size", 0),
        },
    )


def convert_processed_to_legacy_format(
    processed_content: ProcessedContent, item_type: str
) -> dict[str, str]:
    """Convert ProcessedContent back to legacy API format."""
    return {
        "title": processed_content.title,
        "content": processed_content.content,
        "type": item_type,
    }


async def process_raw_content_batch(
    raw_contents: list[RawContent],
) -> list[ProcessedContent]:
    """Process a batch of RawContent using the content extraction domain."""
    # Get configured content processor
    process_contents = get_content_processor()
    result: list[ProcessedContent] = await process_contents(raw_contents)
    return result


# Validation utilities


def is_supported_file_type(file_info: dict[str, Any]) -> bool:
    """Check if file type is supported for extraction."""
    content_type = file_info.get("content-type", "").lower()
    mime_class = file_info.get("mime_class", "").lower()
    supported_types = ["application/pdf", "pdf"]

    return any(
        supported_type in content_type for supported_type in supported_types
    ) or any(supported_type in mime_class for supported_type in supported_types)


def is_file_size_allowed(
    file_info: dict[str, Any], course_id: int, file_id: int
) -> bool:
    """Check if file size is within allowed limits."""
    file_size = file_info.get("size", 0)

    if file_size > MAX_FILE_SIZE:
        logger.warning(
            "file_extraction_size_limit",
            course_id=course_id,
            file_id=file_id,
            file_size=file_size,
            limit=MAX_FILE_SIZE,
        )
        return False

    return True


# Summary utility for backward compatibility


def get_content_summary(
    extracted_content: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    """
    Generate a summary of extracted content.

    Returns statistics about the extracted content for logging and UI display.
    This maintains compatibility with the original ContentExtractionService method.
    """
    total_pages = 0
    total_word_count = 0
    modules_processed = len(extracted_content)

    for pages in extracted_content.values():
        total_pages += len(pages)
        for page in pages:
            # Rough word count estimation
            word_count = len(page.get("content", "").split())
            total_word_count += word_count

    return {
        "modules_processed": modules_processed,
        "total_pages": total_pages,
        "total_word_count": total_word_count,
        "average_words_per_page": (
            total_word_count // total_pages if total_pages > 0 else 0
        ),
        "extracted_at": datetime.now().isoformat(),
    }


# Quiz Export Flows


async def export_quiz_to_canvas_flow(
    quiz_id: UUID, canvas_token: str
) -> dict[str, Any]:
    """
    Main orchestration flow to export a quiz to Canvas.

    Uses proper transaction management for background task compatibility.
    Follows the same pattern as content extraction with separate transactions.

    Args:
        quiz_id: UUID of the quiz to export
        canvas_token: Canvas API authentication token

    Returns:
        Export result with success status and Canvas quiz information

    Raises:
        ResourceNotFoundError: If quiz not found
        ValidationError: If quiz has no approved questions
        ExternalServiceError: If Canvas API calls fail
    """
    logger.info("canvas_quiz_export_started", quiz_id=str(quiz_id))

    # === Transaction 1: Validate and Reserve ===
    async def _validate_and_reserve(
        session: Any, quiz_id: UUID
    ) -> dict[str, Any] | None:
        return await validate_quiz_for_export_flow(session, quiz_id)

    from src.database import execute_in_transaction

    quiz_data = await execute_in_transaction(
        _validate_and_reserve, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not quiz_data:
        raise RuntimeError("Failed to validate quiz for export")

    # Handle already exported case
    if quiz_data.get("already_exported"):
        return {
            "success": True,
            "canvas_quiz_id": quiz_data["canvas_quiz_id"],
            "exported_questions": 0,
            "message": "Quiz already exported to Canvas",
            "already_exported": True,
        }

    # === Canvas API Operations (outside transaction) ===
    try:
        # Create Canvas quiz
        canvas_quiz = await create_canvas_quiz_flow(
            canvas_token=canvas_token,
            course_id=quiz_data["course_id"],
            title=quiz_data["title"],
            total_points=len(quiz_data["questions"]),
        )

        # Export questions to Canvas
        exported_items = await export_questions_batch_flow(
            canvas_token=canvas_token,
            course_id=quiz_data["course_id"],
            quiz_id=canvas_quiz["id"],
            questions=quiz_data["questions"],
        )

        # === Transaction 2: Save Results ===
        async def _save_results(session: Any, quiz_id: UUID) -> dict[str, Any]:
            return await finalize_quiz_export_flow(
                session=session,
                quiz_id=quiz_id,
                canvas_quiz_id=canvas_quiz["id"],
                questions=quiz_data["questions"],
                exported_items=exported_items,
            )

        result: dict[str, Any] = await execute_in_transaction(
            _save_results, quiz_id, isolation_level="REPEATABLE READ", retries=3
        )

        logger.info(
            "canvas_quiz_export_completed",
            quiz_id=str(quiz_id),
            canvas_quiz_id=canvas_quiz["id"],
            exported_questions=result["exported_questions"],
        )

        return result

    except Exception as e:
        # === Transaction 3: Mark as Failed ===
        async def _mark_failed(session: Any, quiz_id: UUID) -> None:
            await update_quiz_export_status(session, quiz_id, "failed")

        try:
            await execute_in_transaction(
                _mark_failed, quiz_id, isolation_level="REPEATABLE READ", retries=3
            )
        except Exception as update_error:
            logger.error(
                "canvas_quiz_export_status_update_failed",
                quiz_id=str(quiz_id),
                error=str(update_error),
            )

        logger.error(
            "canvas_quiz_export_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise


async def validate_quiz_for_export_flow(session: Any, quiz_id: UUID) -> dict[str, Any]:
    """
    Validation flow for quiz export prerequisites.

    Args:
        session: Database session
        quiz_id: UUID of the quiz to validate

    Returns:
        Quiz data dictionary with course_id, title, and questions

    Raises:
        ResourceNotFoundError: If quiz not found
        ValidationError: If quiz invalid for export
    """
    from src.quiz.service import QuizService

    quiz = await QuizService.get_quiz_for_update(session, quiz_id)
    if not quiz:
        logger.error("canvas_quiz_export_quiz_not_found", quiz_id=str(quiz_id))
        raise ResourceNotFoundError(f"Quiz {quiz_id}")

    # Extract all quiz data WITHIN the session context to avoid lazy loading issues
    quiz_course_id = quiz.canvas_course_id
    quiz_title = quiz.title
    quiz_export_status = quiz.export_status
    quiz_canvas_quiz_id = quiz.canvas_quiz_id

    # Check if already exported
    if quiz_export_status == "completed" and quiz_canvas_quiz_id:
        logger.warning(
            "canvas_quiz_export_already_exported",
            quiz_id=str(quiz_id),
            canvas_quiz_id=quiz_canvas_quiz_id,
        )
        return {
            "already_exported": True,
            "canvas_quiz_id": quiz_canvas_quiz_id,
        }

    # Check if currently processing
    if quiz_export_status == "processing":
        logger.warning(
            "canvas_quiz_export_already_processing",
            quiz_id=str(quiz_id),
            current_status=quiz_export_status,
        )
        raise ValidationError("Quiz export is already in progress")

    # Get approved questions
    from src.question.service import QuestionService

    approved_questions = await QuestionService.get_approved_questions_by_quiz_id_async(
        session, quiz_id
    )

    if not approved_questions:
        logger.error(
            "canvas_quiz_export_no_approved_questions",
            quiz_id=str(quiz_id),
        )
        raise ValidationError("Quiz has no approved questions to export")

    # Prepare question data - extract all attributes within session context
    question_data = [
        {
            "id": question.id,
            "question_text": question.question_text,
            "option_a": question.option_a,
            "option_b": question.option_b,
            "option_c": question.option_c,
            "option_d": question.option_d,
            "correct_answer": question.correct_answer,
        }
        for question in approved_questions
    ]

    # Mark as processing
    quiz.export_status = "processing"
    await session.commit()

    logger.info(
        "canvas_quiz_export_processing",
        quiz_id=str(quiz_id),
        course_id=quiz_course_id,
        approved_questions_count=len(question_data),
    )

    return {
        "course_id": quiz_course_id,
        "title": quiz_title,
        "questions": question_data,
        "already_exported": False,
    }


async def create_canvas_quiz_flow(
    canvas_token: str, course_id: int, title: str, total_points: int
) -> dict[str, Any]:
    """
    Flow for creating a Canvas quiz.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        title: Quiz title
        total_points: Total points for the quiz

    Returns:
        Canvas quiz data with ID

    Raises:
        ExternalServiceError: If Canvas API call fails
    """

    canvas_quiz = await create_canvas_quiz(canvas_token, course_id, title, total_points)

    logger.info(
        "canvas_quiz_created",
        course_id=course_id,
        title=title,
        canvas_quiz_id=canvas_quiz["id"],
    )

    return canvas_quiz


async def export_questions_batch_flow(
    canvas_token: str, course_id: int, quiz_id: str, questions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Flow for exporting questions to Canvas in batch.

    Args:
        canvas_token: Canvas API authentication token
        course_id: Canvas course ID
        quiz_id: Canvas quiz ID
        questions: List of question dictionaries

    Returns:
        List of export results for each question
    """
    exported_items = await create_canvas_quiz_items(
        canvas_token, course_id, quiz_id, questions
    )

    successful_items = len([r for r in exported_items if r["success"]])
    logger.info(
        "canvas_questions_batch_exported",
        course_id=course_id,
        canvas_quiz_id=quiz_id,
        total_questions=len(questions),
        successful_items=successful_items,
        failed_items=len(questions) - successful_items,
    )

    return exported_items


async def finalize_quiz_export_flow(
    session: Any,
    quiz_id: UUID,
    canvas_quiz_id: str,
    questions: list[dict[str, Any]],
    exported_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Flow for finalizing quiz export and updating database.

    Args:
        session: Database session
        quiz_id: UUID of the original quiz
        canvas_quiz_id: Canvas quiz ID
        questions: Original question data
        exported_items: Export results from Canvas

    Returns:
        Final export result summary
    """
    # Update quiz export status
    from src.question.models import Question
    from src.quiz.service import QuizService

    quiz = await QuizService.get_quiz_for_update(session, quiz_id)
    if quiz:
        quiz.canvas_quiz_id = canvas_quiz_id
        quiz.export_status = "completed"
        quiz.exported_at = datetime.now(timezone.utc)

        # Update individual question Canvas IDs
        for question_dict, item_result in zip(questions, exported_items, strict=False):
            if item_result["success"]:
                question_obj = await session.get(Question, question_dict["id"])
                if question_obj:
                    question_obj.canvas_item_id = item_result["item_id"]

        # Note: session.commit() will be handled by execute_in_transaction()

    successful_exports = len([r for r in exported_items if r["success"]])

    return {
        "success": True,
        "canvas_quiz_id": canvas_quiz_id,
        "exported_questions": successful_exports,
        "message": "Quiz successfully exported to Canvas",
    }


async def update_quiz_export_status(session: Any, quiz_id: UUID, status: str) -> None:
    """
    Utility function to update quiz export status.

    Args:
        session: Database session
        quiz_id: UUID of the quiz
        status: New export status
    """
    from src.quiz.service import QuizService

    quiz = await QuizService.get_quiz_for_update(session, quiz_id)
    if quiz:
        quiz.export_status = status
        await session.commit()
