"""
Quiz orchestration module for managing cross-domain workflows.

This module owns the complete quiz lifecycle orchestration using functional
composition and dependency injection to maintain clean domain boundaries.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction

# Removed DI container import - GenerationOrchestrationService imported locally
from src.question.types import GenerationParameters, QuestionType

from .schemas import FailureReason, QuizStatus

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
        from .service import reserve_quiz_job

        return await reserve_quiz_job(session, quiz_id, "extraction")

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

        # Check if meaningful content was extracted
        total_word_count = content_summary.get("total_word_count", 0)
        total_pages = content_summary.get("total_pages", 0)

        if total_word_count == 0 or total_pages == 0:
            logger.warning(
                "extraction_completed_but_no_content_found",
                quiz_id=str(quiz_id),
                course_id=course_id,
                total_word_count=total_word_count,
                total_pages=total_pages,
            )
            final_status = "no_content"
        else:
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
        from .service import update_quiz_status

        additional_fields = {}
        if status == "completed" and content is not None:
            additional_fields["extracted_content"] = content

        if status == "completed":
            # Keep status as EXTRACTING_CONTENT to allow question generation to proceed
            # The extracted_content will be saved via additional_fields
            await update_quiz_status(
                session,
                quiz_id,
                QuizStatus.EXTRACTING_CONTENT,
                None,
                **additional_fields,
            )
        elif status == "no_content":
            # No meaningful content was extracted from the selected modules
            failure_reason = FailureReason.NO_CONTENT_FOUND
            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason, **additional_fields
            )
        elif status == "failed":
            # Technical failure during content extraction
            failure_reason = FailureReason.CONTENT_EXTRACTION_ERROR
            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason, **additional_fields
            )

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
    elif final_status == "no_content":
        logger.info(
            "skipping_question_generation_no_content",
            quiz_id=str(quiz_id),
            reason="no_meaningful_content_extracted",
        )


async def orchestrate_quiz_question_generation(
    quiz_id: UUID,
    target_question_count: int,
    llm_model: str,
    llm_temperature: float,
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
    generation_service: Any = None,
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
        generation_service: Optional injected generation service (creates default if None)
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
        from .service import reserve_quiz_job

        result = await reserve_quiz_job(session, quiz_id, "generation")
        return result is not None

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
        # Use injected generation service or create default
        if generation_service is None:
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
            error_message = None
            logger.info(
                "generation_orchestration_completed",
                quiz_id=str(quiz_id),
                questions_generated=result.questions_generated,
                target_questions=target_question_count,
                question_type=question_type.value,
            )
        else:
            final_status = "failed"
            error_message = result.error_message
            logger.error(
                "generation_orchestration_failed_during_llm",
                quiz_id=str(quiz_id),
                error_message=error_message,
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
        error_message = str(e)

    # === Transaction 2: Save the Result ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Save the generation result to the quiz."""
        from .service import update_quiz_status

        if status == "completed":
            await update_quiz_status(session, quiz_id, QuizStatus.READY_FOR_REVIEW)
        elif status == "failed":
            # Determine appropriate failure reason based on error message
            if (
                error_message
                and "No valid content chunks found for generation" in error_message
            ):
                # This indicates no meaningful content was available for generation
                failure_reason = FailureReason.NO_CONTENT_FOUND
            elif error_message and "No questions generated" in error_message:
                # This indicates the LLM failed to generate any questions
                failure_reason = FailureReason.NO_QUESTIONS_GENERATED
            else:
                # Default to LLM generation error for other failures
                failure_reason = FailureReason.LLM_GENERATION_ERROR

            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason
            )

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        error_message,
        isolation_level="REPEATABLE READ",
        retries=3,
    )


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
    from src.question import service as question_service

    question_data = await question_service.prepare_questions_for_export(quiz_id)

    if not question_data:
        raise RuntimeError("No approved questions found for export")

    # === Transaction 1: Validate and Reserve ===
    async def _validate_and_reserve_export(
        session: Any, quiz_id: UUID, question_data: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Validate quiz for export and reserve the export job."""
        from .service import reserve_quiz_job

        result = await reserve_quiz_job(session, quiz_id, "export")
        if not result:
            return None

        # Add question data to the result
        result["questions"] = question_data
        return result

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
            from src.question import service as question_service

            # Update quiz status
            from .service import update_quiz_status

            await update_quiz_status(
                session,
                quiz_id,
                QuizStatus.PUBLISHED,
                canvas_quiz_id=canvas_quiz["id"],
            )

            # Update individual question Canvas IDs
            await question_service.update_question_canvas_ids(
                session, export_data["questions"], exported_items
            )

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
            from .service import update_quiz_status

            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, FailureReason.CANVAS_EXPORT_ERROR
            )

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
