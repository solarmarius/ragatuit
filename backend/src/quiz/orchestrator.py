"""
Quiz orchestration module for managing cross-domain workflows.

This module owns the complete quiz lifecycle orchestration using functional
composition and dependency injection to maintain clean domain boundaries.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.database import execute_in_transaction
from src.logging_config import get_logger

# Removed DI container import - GenerationOrchestrationService imported locally
from src.question.types import GenerationParameters, QuestionType

from .service import get_quiz_for_update

logger = get_logger("quiz_orchestrator")

# Type aliases for dependency injection
ContentExtractorFunc = Callable[[str, int, list[int]], Any]
ContentSummaryFunc = Callable[[dict[str, list[dict[str, str]]]], dict[str, Any]]
QuizCreatorFunc = Callable[[str, int, str, int], Any]
QuestionExporterFunc = Callable[[str, int, str, list[dict[str, Any]]], Any]


async def orchestrate_quiz_content_extraction(
    quiz_id: UUID,
    course_id: int,
    module_ids: list[int],
    canvas_token: str,
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> None:
    """
    Orchestrate the complete content extraction workflow for a quiz.

    This function owns the cross-domain workflow of extracting content from Canvas
    and updating the quiz status, using dependency injection for clean boundaries.

    Args:
        quiz_id: UUID of the quiz to extract content for
        course_id: Canvas course ID
        module_ids: List of Canvas module IDs to process
        canvas_token: Canvas API authentication token
        content_extractor: Function to extract content from Canvas
        content_summarizer: Function to generate content summary
    """
    logger.info(
        "quiz_content_extraction_orchestration_started",
        quiz_id=str(quiz_id),
        course_id=course_id,
        module_count=len(module_ids),
    )

    # === Transaction 1: Reserve the Job ===
    async def _reserve_extraction_job(
        session: Any, quiz_id: UUID
    ) -> dict[str, Any] | None:
        """Reserve the extraction job and return quiz settings if successful."""
        quiz = await get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("quiz_not_found_for_extraction", quiz_id=str(quiz_id))
            return None

        if quiz.content_extraction_status in ["processing", "completed"]:
            logger.info(
                "extraction_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.content_extraction_status,
            )
            return None

        # Reserve the job
        quiz.content_extraction_status = "processing"
        await session.flush()

        # Return quiz settings for later use
        return {
            "target_questions": quiz.question_count,
            "llm_model": quiz.llm_model,
            "llm_temperature": quiz.llm_temperature,
        }

    quiz_settings = await execute_in_transaction(
        _reserve_extraction_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not quiz_settings:
        logger.info(
            "extraction_orchestration_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Content Extraction (outside transaction) ===
    try:
        # Use injected content extractor function
        extracted_content = await content_extractor(canvas_token, course_id, module_ids)
        content_summary = content_summarizer(extracted_content)

        logger.info(
            "extraction_orchestration_completed",
            quiz_id=str(quiz_id),
            course_id=course_id,
            modules_processed=content_summary["modules_processed"],
            total_pages=content_summary["total_pages"],
            total_word_count=content_summary["total_word_count"],
        )

        final_status = "completed"

    except Exception as e:
        logger.error(
            "extraction_orchestration_failed",
            quiz_id=str(quiz_id),
            course_id=course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        extracted_content = None
        final_status = "failed"

    # === Transaction 2: Save the Result ===
    async def _save_extraction_result(
        session: Any,
        quiz_id: UUID,
        content: dict[str, Any] | None,
        status: str,
    ) -> None:
        """Save the extraction result to the quiz."""
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error("quiz_not_found_during_save", quiz_id=str(quiz_id))
            return

        quiz.content_extraction_status = status
        if status == "completed" and content is not None:
            quiz.extracted_content = content
            quiz.content_extracted_at = datetime.now(timezone.utc)

    await execute_in_transaction(
        _save_extraction_result,
        quiz_id,
        extracted_content,
        final_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )

    # If extraction was successful, trigger question generation
    if final_status == "completed" and quiz_settings:
        logger.info(
            "auto_triggering_question_generation",
            quiz_id=str(quiz_id),
            target_questions=quiz_settings["target_questions"],
            llm_model=quiz_settings["llm_model"],
        )
        await orchestrate_quiz_question_generation(
            quiz_id=quiz_id,
            target_question_count=quiz_settings["target_questions"],
            llm_model=quiz_settings["llm_model"],
            llm_temperature=quiz_settings["llm_temperature"],
        )


async def orchestrate_quiz_question_generation(
    quiz_id: UUID,
    target_question_count: int,
    llm_model: str,
    llm_temperature: float,
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
) -> None:
    """
    Orchestrate the complete question generation workflow for a quiz.

    This function owns the question generation orchestration while using
    the existing modular question generation system.

    Args:
        quiz_id: UUID of the quiz to generate questions for
        target_question_count: Number of questions to generate
        llm_model: LLM model to use for generation
        llm_temperature: Temperature setting for LLM
        question_type: Type of questions to generate
    """
    logger.info(
        "quiz_question_generation_orchestration_started",
        quiz_id=str(quiz_id),
        target_questions=target_question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        question_type=question_type.value,
    )

    # === Transaction 1: Reserve the Job ===
    async def _reserve_generation_job(session: Any, quiz_id: UUID) -> bool:
        """Reserve the question generation job."""
        quiz = await get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("quiz_not_found_for_generation", quiz_id=str(quiz_id))
            return False

        if quiz.llm_generation_status in ["processing", "completed"]:
            logger.info(
                "generation_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.llm_generation_status,
            )
            return False

        # Reserve the job
        quiz.llm_generation_status = "processing"
        await session.flush()
        return True

    should_proceed = await execute_in_transaction(
        _reserve_generation_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not should_proceed:
        logger.info(
            "generation_orchestration_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Question Generation (outside transaction) ===
    try:
        # Get generation service
        from src.question.services import GenerationOrchestrationService

        generation_service = GenerationOrchestrationService()

        # Create generation parameters
        generation_parameters = GenerationParameters(target_count=target_question_count)

        # Generate questions using modular system
        result = await generation_service.generate_questions(
            quiz_id=quiz_id,
            question_type=question_type,
            generation_parameters=generation_parameters,
            provider_name=None,  # Use default provider
            workflow_name=None,  # Use default workflow
            template_name=None,  # Use default template
        )

        if result.success:
            final_status = "completed"
            logger.info(
                "generation_orchestration_completed",
                quiz_id=str(quiz_id),
                questions_generated=result.questions_generated,
                target_questions=target_question_count,
                question_type=question_type.value,
            )
        else:
            final_status = "failed"
            logger.error(
                "generation_orchestration_failed_during_llm",
                quiz_id=str(quiz_id),
                error_message=result.error_message,
                question_type=question_type.value,
            )

    except Exception as e:
        logger.error(
            "generation_orchestration_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            question_type=question_type.value,
            exc_info=True,
        )
        final_status = "failed"

    # === Transaction 2: Save the Result ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
    ) -> None:
        """Save the generation result to the quiz."""
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error("quiz_not_found_during_generation_save", quiz_id=str(quiz_id))
            return

        quiz.llm_generation_status = status

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )


async def _load_and_extract_question_data(quiz_id: UUID) -> list[dict[str, Any]]:
    """
    Load approved questions and extract their data while bound to session.

    This function loads questions in their own session context and extracts
    all needed data before the session closes to avoid DetachedInstanceError.

    Args:
        quiz_id: UUID of the quiz to load questions for

    Returns:
        List of question data dictionaries ready for export
    """
    from src.database import get_async_session
    from src.question import service as question_service
    from src.question.types import QuestionType, get_question_type_registry
    from src.question.types.mcq import MultipleChoiceData

    async with get_async_session() as async_session:
        # Load approved questions with all needed data
        approved_questions = await question_service.get_questions_by_quiz(
            async_session, quiz_id=quiz_id, approved_only=True
        )

        if not approved_questions:
            logger.error("no_approved_questions_for_export", quiz_id=str(quiz_id))
            return []

        # Extract all data while questions are still bound to session
        question_registry = get_question_type_registry()
        question_data = []

        for question in approved_questions:
            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                typed_data = question.get_typed_data(question_registry)
                if isinstance(typed_data, MultipleChoiceData):
                    question_data.append(
                        {
                            "id": question.id,
                            "question_text": typed_data.question_text,
                            "option_a": typed_data.option_a,
                            "option_b": typed_data.option_b,
                            "option_c": typed_data.option_c,
                            "option_d": typed_data.option_d,
                            "correct_answer": typed_data.correct_answer,
                        }
                    )

        logger.debug(
            "question_data_extracted_for_export",
            quiz_id=str(quiz_id),
            questions_extracted=len(question_data),
        )

        return question_data


async def orchestrate_quiz_export_to_canvas(
    quiz_id: UUID,
    canvas_token: str,
    quiz_creator: QuizCreatorFunc,
    question_exporter: QuestionExporterFunc,
) -> dict[str, Any]:
    """
    Orchestrate the complete quiz export workflow to Canvas.

    This function owns the cross-domain workflow of exporting a quiz to Canvas,
    using dependency injection for Canvas operations while managing Quiz state.

    Args:
        quiz_id: UUID of the quiz to export
        canvas_token: Canvas API authentication token
        quiz_creator: Function to create quiz in Canvas
        question_exporter: Function to export questions to Canvas

    Returns:
        Export result with success status and Canvas quiz information
    """
    logger.info("quiz_export_orchestration_started", quiz_id=str(quiz_id))

    # === Load Question Data (outside transaction) ===
    question_data = await _load_and_extract_question_data(quiz_id)

    if not question_data:
        raise RuntimeError("No approved questions found for export")

    # === Transaction 1: Validate and Reserve ===
    async def _validate_and_reserve_export(
        session: Any, quiz_id: UUID, question_data: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Validate quiz for export and reserve the export job."""
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error("quiz_not_found_for_export", quiz_id=str(quiz_id))
            return None

        # Check if already exported
        if quiz.export_status == "completed" and quiz.canvas_quiz_id:
            logger.warning(
                "quiz_already_exported",
                quiz_id=str(quiz_id),
                canvas_quiz_id=quiz.canvas_quiz_id,
            )
            return {
                "already_exported": True,
                "canvas_quiz_id": quiz.canvas_quiz_id,
                "course_id": quiz.canvas_course_id,
                "title": quiz.title,
            }

        # Check if currently processing
        if quiz.export_status == "processing":
            logger.warning(
                "export_already_processing",
                quiz_id=str(quiz_id),
                current_status=quiz.export_status,
            )
            return None

        # Mark as processing
        quiz.export_status = "processing"
        await session.flush()

        return {
            "already_exported": False,
            "course_id": quiz.canvas_course_id,
            "title": quiz.title,
            "questions": question_data,
        }

    export_data = await execute_in_transaction(
        _validate_and_reserve_export,
        quiz_id,
        question_data,
        isolation_level="REPEATABLE READ",
        retries=3,
    )

    if not export_data:
        raise RuntimeError("Failed to validate quiz for export")

    # Handle already exported case
    if export_data["already_exported"]:
        return {
            "success": True,
            "canvas_quiz_id": export_data["canvas_quiz_id"],
            "exported_questions": 0,
            "message": "Quiz already exported to Canvas",
            "already_exported": True,
        }

    # === Canvas Operations (outside transaction) ===
    try:
        # Create Canvas quiz using injected function
        canvas_quiz = await quiz_creator(
            canvas_token,
            export_data["course_id"],
            export_data["title"],
            len(export_data["questions"]),
        )

        # Export questions using injected function
        exported_items = await question_exporter(
            canvas_token,
            export_data["course_id"],
            canvas_quiz["id"],
            export_data["questions"],
        )

        # === Transaction 2: Save Results ===
        async def _save_export_results(session: Any, quiz_id: UUID) -> dict[str, Any]:
            """Save the export results to the quiz."""
            from src.question.models import Question

            quiz = await get_quiz_for_update(session, quiz_id)
            if quiz:
                quiz.canvas_quiz_id = canvas_quiz["id"]
                quiz.export_status = "completed"
                quiz.exported_at = datetime.now(timezone.utc)

                # Update individual question Canvas IDs
                for question_data, item_result in zip(
                    export_data["questions"], exported_items, strict=False
                ):
                    if item_result.get("success"):
                        question_obj = await session.get(Question, question_data["id"])
                        if question_obj:
                            question_obj.canvas_item_id = item_result.get("item_id")

            successful_exports = len([r for r in exported_items if r.get("success")])
            return {
                "success": True,
                "canvas_quiz_id": canvas_quiz["id"],
                "exported_questions": successful_exports,
                "message": "Quiz successfully exported to Canvas",
            }

        result: dict[str, Any] = await execute_in_transaction(
            _save_export_results, quiz_id, isolation_level="REPEATABLE READ", retries=3
        )

        logger.info(
            "quiz_export_orchestration_completed",
            quiz_id=str(quiz_id),
            canvas_quiz_id=canvas_quiz["id"],
            exported_questions=result["exported_questions"],
        )

        return result

    except Exception as e:
        # === Transaction 3: Mark as Failed ===
        async def _mark_export_failed(session: Any, quiz_id: UUID) -> None:
            """Mark export as failed."""
            quiz = await get_quiz_for_update(session, quiz_id)
            if quiz:
                quiz.export_status = "failed"

        try:
            await execute_in_transaction(
                _mark_export_failed,
                quiz_id,
                isolation_level="REPEATABLE READ",
                retries=3,
            )
        except Exception as update_error:
            logger.error(
                "export_status_update_failed",
                quiz_id=str(quiz_id),
                error=str(update_error),
            )

        logger.error(
            "quiz_export_orchestration_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
