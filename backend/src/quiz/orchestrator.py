"""
Quiz orchestration module for managing cross-domain workflows.

This module owns the complete quiz lifecycle orchestration using functional
composition and dependency injection to maintain clean domain boundaries.
"""

import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction

# Removed DI container import - GenerationOrchestrationService imported locally
from src.question.types import QuestionType, QuizLanguage

from .constants import OPERATION_TIMEOUTS
from .exceptions import OrchestrationTimeoutError
from .schemas import FailureReason, QuizStatus

T = TypeVar("T")

logger = get_logger("quiz_orchestrator")


async def safe_background_orchestration(
    operation_func: Callable[..., Any],
    operation_name: str,
    quiz_id: UUID,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Safely execute orchestration operations as background tasks with proper exception handling.

    This wrapper ensures that all exceptions, including OrchestrationTimeoutError, are properly
    caught and handled when operations are run as FastAPI background tasks. Without this wrapper,
    background tasks silently swallow exceptions, leaving quizzes stuck in incomplete states.

    Args:
        operation_func: The orchestration function to execute
        operation_name: Name of the operation for logging (e.g., "content_extraction")
        quiz_id: UUID of the quiz being processed
        *args: Arguments to pass to the operation function
        **kwargs: Keyword arguments to pass to the operation function
    """
    # Generate correlation ID for tracking concurrent operations
    correlation_id = str(uuid.uuid4())

    logger.info(
        "background_orchestration_started",
        operation=operation_name,
        quiz_id=str(quiz_id),
        correlation_id=correlation_id,
    )

    try:
        # Execute the orchestration operation
        await operation_func(*args, **kwargs)

        logger.info(
            "background_orchestration_completed",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
        )

    except OrchestrationTimeoutError as timeout_error:
        logger.error(
            "background_orchestration_timeout",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            timeout_seconds=timeout_error.timeout_seconds,
            error=str(timeout_error),
        )

        # Update quiz status to failed with appropriate failure reason
        await _handle_orchestration_failure(
            quiz_id, operation_name, timeout_error, correlation_id
        )

    except Exception as error:
        logger.error(
            "background_orchestration_error",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
        )

        # Update quiz status to failed with appropriate failure reason
        await _handle_orchestration_failure(
            quiz_id, operation_name, error, correlation_id
        )


async def _handle_orchestration_failure(
    quiz_id: UUID,
    operation_name: str,
    error: Exception,
    correlation_id: str,
) -> None:
    """
    Handle orchestration failures by updating quiz status appropriately.

    Args:
        quiz_id: UUID of the failed quiz
        operation_name: Name of the operation that failed
        error: The exception that occurred
        correlation_id: Correlation ID for tracking
    """
    logger.warning(
        "orchestration_failure_status_update_initiated",
        operation=operation_name,
        quiz_id=str(quiz_id),
        correlation_id=correlation_id,
        error_type=type(error).__name__,
    )

    try:

        async def _update_failed_status(session: Any, quiz_id: UUID) -> None:
            """Update quiz status to failed with appropriate failure reason."""
            from .exceptions import determine_failure_reason
            from .service import update_quiz_status

            # Determine appropriate failure reason based on operation and error
            failure_reason = determine_failure_reason(operation_name, error, str(error))

            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason
            )

        await execute_in_transaction(
            _update_failed_status,
            quiz_id,
            isolation_level="REPEATABLE READ",
            retries=3,
        )

        logger.info(
            "orchestration_failure_status_updated",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            new_status="failed",
        )

    except Exception as update_error:
        logger.error(
            "orchestration_failure_status_update_failed",
            operation=operation_name,
            quiz_id=str(quiz_id),
            correlation_id=correlation_id,
            update_error=str(update_error),
            original_error=str(error),
            exc_info=True,
        )
        # If we can't update the status, log as critical for manual intervention


def timeout_operation(
    timeout_seconds: int,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to add timeout to orchestration operations.

    Args:
        timeout_seconds: Maximum time to wait before timing out

    Raises:
        OrchestrationTimeoutError: If operation times out
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Extract quiz_id from args if available for better logging
                quiz_id = None
                if args and hasattr(args[0], "hex"):  # UUID has hex attribute
                    quiz_id = str(args[0])
                elif len(args) > 0:
                    quiz_id = str(args[0])

                logger.error(
                    "orchestration_operation_timeout",
                    operation=func.__name__,
                    timeout_seconds=timeout_seconds,
                    quiz_id=quiz_id,
                )

                raise OrchestrationTimeoutError(
                    operation=func.__name__,
                    timeout_seconds=timeout_seconds,
                    quiz_id=quiz_id,
                )

        return wrapper

    return decorator


# Type aliases for dependency injection
ContentExtractorFunc = Callable[[str, int, list[int]], Any]
ContentSummaryFunc = Callable[[dict[str, list[dict[str, str]]]], dict[str, Any]]
QuizCreatorFunc = Callable[[str, int, str, int], Any]
QuestionExporterFunc = Callable[[str, int, str, list[dict[str, Any]]], Any]


async def _execute_content_extraction_workflow(
    quiz_id: UUID,
    course_id: int,
    module_ids: list[int],
    canvas_token: str,
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> tuple[dict[str, Any] | None, str]:
    """
    Execute the content extraction workflow.

    Returns:
        Tuple of (extracted_content, final_status)
    """
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
            return None, "no_content"
        else:
            return extracted_content, "completed"

    except Exception as e:
        logger.error(
            "extraction_orchestration_failed",
            quiz_id=str(quiz_id),
            course_id=course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None, "failed"


async def _execute_generation_workflow(
    quiz_id: UUID,
    _target_question_count: int,
    _llm_model: str,
    _llm_temperature: float,
    language: QuizLanguage,
    question_type: Any,
    generation_service: Any = None,
) -> tuple[str, str | None, Exception | None]:
    """
    Execute the module-based question generation workflow with batch-level tracking.

    Returns:
        Tuple of (final_status, error_message, failure_exception)
    """
    try:
        # Use injected generation service or create default
        if generation_service is None:
            from src.question.services import QuestionGenerationService

            generation_service = QuestionGenerationService()

        # Prepare content using functional content service
        from src.question.services import prepare_and_validate_content

        logger.info(
            "generation_workflow_content_preparation_started",
            quiz_id=str(quiz_id),
            language=language.value,
            question_type=question_type.value,
        )

        extracted_content = await prepare_and_validate_content(quiz_id)

        if not extracted_content:
            logger.warning(
                "generation_workflow_no_content_found",
                quiz_id=str(quiz_id),
            )
            return "failed", "No valid content found for question generation", None

        logger.info(
            "generation_workflow_content_prepared",
            quiz_id=str(quiz_id),
            modules_count=len(extracted_content),
            total_content_size=sum(
                len(content) for content in extracted_content.values()
            ),
        )

        # Generate questions using module-based service with batch tracking
        provider_name = "openai"  # Use default provider
        batch_results = (
            await generation_service.generate_questions_for_quiz_with_batch_tracking(
                quiz_id=quiz_id,
                extracted_content=extracted_content,
                provider_name=provider_name,
            )
        )

        # Analyze batch-level results
        successful_batches = []
        failed_batches = []
        total_generated = 0
        total_target = 0

        # Get expected counts from quiz module selection
        from src.database import get_async_session
        from src.quiz.models import Quiz

        async with get_async_session() as session:
            quiz = await session.get(Quiz, quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            # Build batch analysis
            for module_id, module_info in quiz.selected_modules.items():
                expected_count = module_info.get("question_count", 0)
                total_target += expected_count

                batch_key = f"{module_id}_{question_type.value}_{expected_count}"
                actual_count = len(batch_results.get(module_id, []))
                total_generated += actual_count

                if actual_count == expected_count:
                    # 100% success - batch completed fully
                    successful_batches.append(
                        {
                            "batch_key": batch_key,
                            "module_id": module_id,
                            "module_name": module_info.get("name", "Unknown"),
                            "question_type": question_type.value,
                            "target_count": expected_count,
                            "generated_count": actual_count,
                            "status": "success",
                            "questions_saved": True,
                        }
                    )
                else:
                    # Failed batch - didn't meet target
                    failed_batches.append(
                        {
                            "batch_key": batch_key,
                            "module_id": module_id,
                            "module_name": module_info.get("name", "Unknown"),
                            "question_type": question_type.value,
                            "target_count": expected_count,
                            "generated_count": actual_count,
                            "status": "failed",
                            "questions_saved": False,
                            "error": f"Generated {actual_count}/{expected_count} questions",
                        }
                    )

        # Store batch results in quiz metadata
        await _store_generation_metadata(
            quiz_id, successful_batches, failed_batches, total_generated, total_target
        )

        # Determine overall status based on batch results
        if len(successful_batches) == 0:
            # Complete failure - no batches succeeded
            logger.error(
                "generation_workflow_complete_failure",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                total_target=total_target,
                failed_batches=len(failed_batches),
            )
            return "failed", "No questions were generated from any module", None

        elif len(failed_batches) == 0:
            # Complete success - all batches succeeded
            logger.info(
                "generation_workflow_complete_success",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                total_target=total_target,
                successful_batches=len(successful_batches),
            )
            return "completed", None, None

        else:
            # Partial success - some batches succeeded, some failed
            logger.info(
                "generation_workflow_partial_success",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                total_target=total_target,
                successful_batches=len(successful_batches),
                failed_batches=len(failed_batches),
                success_rate=f"{(total_generated/total_target)*100:.1f}%",
            )
            return "partial_success", None, None

    except Exception as e:
        logger.error(
            "generation_workflow_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            question_type=question_type.value,
            exc_info=True,
        )
        return "failed", str(e), e


async def _store_generation_metadata(
    quiz_id: UUID,
    successful_batches: list[dict[str, Any]],
    failed_batches: list[dict[str, Any]],
    total_generated: int,
    total_target: int,
) -> None:
    """Store batch-level generation results in quiz metadata."""
    from src.database import get_async_session
    from src.quiz.models import Quiz

    async with get_async_session() as session:
        quiz = await session.get(Quiz, quiz_id)
        if not quiz:
            return

        # Create generation attempt record
        batch_results_dict: dict[str, Any] = {}

        # Add successful batches to record
        for batch in successful_batches:
            batch_results_dict[batch["batch_key"]] = batch

        # Add failed batches to record
        for batch in failed_batches:
            batch_results_dict[batch["batch_key"]] = batch

        attempt_record = {
            "attempt_number": len(
                quiz.generation_metadata.get("generation_attempts", [])
            )
            + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "partial_success"
            if failed_batches
            else "complete_success",
            "batch_results": batch_results_dict,
        }

        # Update quiz metadata
        if not quiz.generation_metadata:
            quiz.generation_metadata = {}

        if "generation_attempts" not in quiz.generation_metadata:
            quiz.generation_metadata["generation_attempts"] = []

        quiz.generation_metadata["generation_attempts"].append(attempt_record)

        # Update summary information
        quiz.generation_metadata.update(
            {
                "failed_batches": [batch["batch_key"] for batch in failed_batches],
                "successful_batches": [
                    batch["batch_key"] for batch in successful_batches
                ],
                "total_questions_saved": total_generated,
                "total_questions_target": total_target,
                "last_updated": datetime.utcnow().isoformat(),
            }
        )

        await session.commit()

        logger.info(
            "generation_metadata_stored",
            quiz_id=str(quiz_id),
            successful_batches=len(successful_batches),
            failed_batches=len(failed_batches),
            attempt_number=attempt_record["attempt_number"],
        )


async def _execute_export_workflow(
    quiz_id: UUID,
    canvas_token: str,
    quiz_creator: QuizCreatorFunc,
    question_exporter: QuestionExporterFunc,
    export_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the Canvas export workflow with all-or-nothing approach.
    Either all questions export successfully or the entire quiz is rolled back.

    Returns:
        Export result dictionary with success status
    """
    total_questions = len(export_data["questions"])

    logger.info(
        "canvas_export_workflow_started",
        quiz_id=str(quiz_id),
        total_questions=total_questions,
        course_id=export_data["course_id"],
    )

    # Create Canvas quiz using injected function
    canvas_quiz = await quiz_creator(
        canvas_token,
        export_data["course_id"],
        export_data["title"],
        total_questions,
    )

    logger.info(
        "canvas_quiz_created_for_export",
        quiz_id=str(quiz_id),
        canvas_quiz_id=canvas_quiz["id"],
    )

    # Export questions using injected function
    exported_items = await question_exporter(
        canvas_token,
        export_data["course_id"],
        canvas_quiz["id"],
        export_data["questions"],
    )

    # Analyze export results - ALL questions must succeed
    successful_exports = len([r for r in exported_items if r.get("success")])
    failed_exports = total_questions - successful_exports

    logger.info(
        "canvas_export_results_analyzed",
        quiz_id=str(quiz_id),
        canvas_quiz_id=canvas_quiz["id"],
        total_questions=total_questions,
        successful_exports=successful_exports,
        failed_exports=failed_exports,
    )

    # All-or-nothing: Either all questions succeed or we rollback
    if successful_exports == total_questions:
        # Complete success - all questions exported
        logger.info(
            "canvas_export_complete_success",
            quiz_id=str(quiz_id),
            canvas_quiz_id=canvas_quiz["id"],
            message="All questions exported successfully",
        )

        return {
            "success": True,
            "canvas_quiz_id": canvas_quiz["id"],
            "exported_questions": successful_exports,
            "total_questions": total_questions,
            "should_rollback": False,
            "message": "Quiz successfully exported to Canvas",
            "exported_items": exported_items,
        }
    else:
        # Any failure - rollback the entire quiz
        logger.error(
            "canvas_export_failure_rollback_needed",
            quiz_id=str(quiz_id),
            canvas_quiz_id=canvas_quiz["id"],
            successful_exports=successful_exports,
            failed_exports=failed_exports,
            message=f"Export failed: {failed_exports} out of {total_questions} questions failed to export",
        )

        return {
            "success": False,
            "canvas_quiz_id": canvas_quiz["id"],
            "exported_questions": successful_exports,
            "total_questions": total_questions,
            "should_rollback": True,
            "message": f"Export failed: {failed_exports} out of {total_questions} questions failed to export. Quiz will be removed from Canvas.",
            "exported_items": exported_items,
        }


@timeout_operation(OPERATION_TIMEOUTS["content_extraction"])
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
    extracted_content, final_status = await _execute_content_extraction_workflow(
        quiz_id,
        course_id,
        module_ids,
        canvas_token,
        content_extractor,
        content_summarizer,
    )

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
        try:
            await orchestrate_quiz_question_generation(
                quiz_id=quiz_id,
                target_question_count=quiz_settings["target_questions"],
                llm_model=quiz_settings["llm_model"],
                llm_temperature=quiz_settings["llm_temperature"],
                language=quiz_settings["language"],
            )
        except Exception as auto_trigger_error:
            logger.error(
                "auto_trigger_question_generation_failed",
                quiz_id=str(quiz_id),
                error=str(auto_trigger_error),
                error_type=type(auto_trigger_error).__name__,
                exc_info=True,
            )
            # Rollback: Reset status to allow manual retry but keep extracted content
            await _rollback_auto_trigger_failure(quiz_id, auto_trigger_error)
    elif final_status == "no_content":
        logger.info(
            "skipping_question_generation_no_content",
            quiz_id=str(quiz_id),
            reason="no_meaningful_content_extracted",
        )


@timeout_operation(OPERATION_TIMEOUTS["question_generation"])
async def orchestrate_quiz_question_generation(
    quiz_id: UUID,
    target_question_count: int,
    llm_model: str,
    llm_temperature: float,
    language: QuizLanguage,
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
        language: Language for question generation
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
    final_status, error_message, failure_exception = await _execute_generation_workflow(
        quiz_id,
        target_question_count,
        llm_model,
        llm_temperature,
        language,
        question_type,
        generation_service,
    )

    # === Transaction 2: Save the Result ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
        error_message: str | None = None,
        exception: Exception | None = None,
    ) -> None:
        """Save the generation result to the quiz with batch-level status support."""
        from .service import update_quiz_status

        if status == "completed":
            # All batches succeeded - full success
            await update_quiz_status(session, quiz_id, QuizStatus.READY_FOR_REVIEW)
        elif status == "partial_success":
            # Some batches succeeded - partial success, user can review and retry
            await update_quiz_status(
                session, quiz_id, QuizStatus.READY_FOR_REVIEW_PARTIAL
            )
        elif status == "failed":
            # No batches succeeded - complete failure
            from .exceptions import categorize_generation_error

            failure_reason = categorize_generation_error(exception, error_message)
            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason
            )

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        error_message,
        failure_exception,
        isolation_level="REPEATABLE READ",
        retries=3,
    )


async def _rollback_auto_trigger_failure(quiz_id: UUID, error: Exception) -> None:
    """
    Rollback quiz state when auto-trigger question generation fails.

    This prevents the quiz from being stuck in an inconsistent state where
    content is extracted but generation failed silently.

    Args:
        quiz_id: UUID of the quiz to rollback
        error: The exception that caused the auto-trigger failure
    """
    logger.warning(
        "auto_trigger_rollback_initiated",
        quiz_id=str(quiz_id),
        error_type=type(error).__name__,
        error_message=str(error),
    )

    async def _perform_rollback(session: Any, quiz_id: UUID) -> None:
        """Reset quiz to extracting_content status to allow manual retry."""
        from .service import update_quiz_status

        # Reset to EXTRACTING_CONTENT status but keep the extracted content
        # This allows the user to manually trigger question generation
        await update_quiz_status(
            session,
            quiz_id,
            QuizStatus.EXTRACTING_CONTENT,
            None,  # Clear any failure reason
        )

    try:
        await execute_in_transaction(
            _perform_rollback,
            quiz_id,
            isolation_level="REPEATABLE READ",
            retries=3,
        )
        logger.info(
            "auto_trigger_rollback_completed",
            quiz_id=str(quiz_id),
            new_status="extracting_content",
        )
    except Exception as rollback_error:
        logger.error(
            "auto_trigger_rollback_failed",
            quiz_id=str(quiz_id),
            rollback_error=str(rollback_error),
            original_error=str(error),
            exc_info=True,
        )
        # If rollback fails, the quiz might be in an inconsistent state
        # Log this as a critical error for manual intervention


@timeout_operation(OPERATION_TIMEOUTS["canvas_export"])
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
        workflow_result = await _execute_export_workflow(
            quiz_id, canvas_token, quiz_creator, question_exporter, export_data
        )
        canvas_quiz_id = workflow_result["canvas_quiz_id"]
        exported_items = workflow_result["exported_items"]
        export_success = workflow_result["success"]

        # === Handle Export Results ===
        if export_success:
            # === Success: Save Results ===
            async def _save_export_success_results(
                session: Any, quiz_id: UUID
            ) -> dict[str, Any]:
                """Save the successful export results to the quiz."""
                from src.question import service as question_service

                from .service import update_quiz_status

                await update_quiz_status(
                    session,
                    quiz_id,
                    QuizStatus.PUBLISHED,
                    canvas_quiz_id=canvas_quiz_id,
                )

                # Update individual question Canvas IDs
                await question_service.update_question_canvas_ids(
                    session, export_data["questions"], exported_items
                )

                return {
                    "success": True,
                    "canvas_quiz_id": canvas_quiz_id,
                    "exported_questions": workflow_result["exported_questions"],
                    "message": workflow_result["message"],
                }

            result: dict[str, Any] = await execute_in_transaction(
                _save_export_success_results,
                quiz_id,
                isolation_level="REPEATABLE READ",
                retries=3,
            )

            logger.info(
                "quiz_export_orchestration_completed_success",
                quiz_id=str(quiz_id),
                canvas_quiz_id=canvas_quiz_id,
                exported_questions=result["exported_questions"],
            )

            return result

        else:
            # === Failure: Rollback Canvas Quiz ===
            logger.warning(
                "quiz_export_initiating_rollback",
                quiz_id=str(quiz_id),
                canvas_quiz_id=canvas_quiz_id,
                message="Export failed, rolling back Canvas quiz",
            )

            try:
                from src.canvas.service import delete_canvas_quiz

                rollback_success = await delete_canvas_quiz(
                    canvas_token, export_data["course_id"], canvas_quiz_id
                )

                if rollback_success:
                    logger.info(
                        "quiz_export_rollback_completed",
                        quiz_id=str(quiz_id),
                        canvas_quiz_id=canvas_quiz_id,
                        message="Canvas quiz deleted after export failure",
                    )
                else:
                    logger.warning(
                        "quiz_export_rollback_failed",
                        quiz_id=str(quiz_id),
                        canvas_quiz_id=canvas_quiz_id,
                        message="Failed to delete Canvas quiz during rollback",
                    )
            except Exception as rollback_error:
                logger.error(
                    "quiz_export_rollback_error",
                    quiz_id=str(quiz_id),
                    canvas_quiz_id=canvas_quiz_id,
                    error=str(rollback_error),
                    message="Exception occurred during Canvas quiz rollback",
                )
                # Continue with failure handling even if rollback failed

            # Raise specific Canvas export exception to trigger failure handling
            from src.canvas.exceptions import CanvasQuizExportError

            raise CanvasQuizExportError(workflow_result["message"])

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
