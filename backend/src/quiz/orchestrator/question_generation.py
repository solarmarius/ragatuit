"""
Question generation orchestration for quiz operations.

This module handles the module-based question generation workflow with batch tracking
and support for multiple question types per module.
"""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction
from src.question.types import QuizLanguage

from ..constants import OPERATION_TIMEOUTS
from ..schemas import QuizStatus
from .core import timeout_operation

logger = get_logger("quiz_orchestrator_question_generation")


async def _execute_generation_workflow(
    quiz_id: UUID,
    _target_question_count: int,
    _llm_model: str,
    _llm_temperature: float,
    language: QuizLanguage,
    generation_service: Any = None,
) -> tuple[str, str | None, Exception | None, dict[str, list[str]] | None]:
    """
    Execute the module-based question generation workflow with batch-level tracking.

    Now processes multiple question types per module based on quiz configuration.

    Returns:
        Tuple of (final_status, error_message, failure_exception, batch_status)
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
        )

        extracted_content = await prepare_and_validate_content(quiz_id)

        if not extracted_content:
            logger.warning(
                "generation_workflow_no_content_found",
                quiz_id=str(quiz_id),
            )
            return (
                "failed",
                "No valid content found for question generation",
                None,
                None,
            )

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
        (
            batch_results,
            batch_status,
        ) = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id=quiz_id,
            extracted_content=extracted_content,
            provider_name=provider_name,
        )

        # Analyze batch-level results using the new batch structure
        # The generation service now handles batch tracking automatically
        # We get the results and let the generation service update metadata
        total_generated = sum(len(questions) for questions in batch_results.values())

        logger.info(
            "generation_workflow_batch_results_analyzed",
            quiz_id=str(quiz_id),
            modules_processed=len(batch_results),
            total_questions_generated=total_generated,
        )

        # Get quiz to check batch status via generation metadata
        from src.database import get_async_session
        from src.quiz.models import Quiz

        async with get_async_session() as session:
            quiz = await session.get(Quiz, quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            # Refresh to get latest metadata
            await session.refresh(quiz)

            # Calculate total expected batches from quiz configuration
            total_expected_batches = 0
            for module_id, module_data in quiz.selected_modules.items():
                # Only count modules that have content
                if module_id in extracted_content:
                    total_expected_batches += len(
                        module_data.get("question_batches", [])
                    )

            # Get batch status from generation service (current batches processed)
            current_successful_batches = batch_status.get("successful_batches", [])
            current_failed_batches = batch_status.get("failed_batches", [])

            # Get previously successful batches from metadata to calculate total
            generation_metadata = quiz.generation_metadata or {}
            previous_successful_batches = generation_metadata.get(
                "successful_batches", []
            )

            # Total successful = previous + current successful (removing duplicates)
            all_successful_batches = set(
                previous_successful_batches + current_successful_batches
            )
            total_successful_batches = len(all_successful_batches)

            logger.info(
                "generation_workflow_batch_status_check",
                quiz_id=str(quiz_id),
                total_expected_batches=total_expected_batches,
                total_successful_batches=total_successful_batches,
                current_successful_batches=len(current_successful_batches),
                current_failed_batches=len(current_failed_batches),
            )

        # Determine overall status based on batch results
        if total_successful_batches == 0:
            # Complete failure - no batches succeeded
            logger.error(
                "generation_workflow_complete_failure",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                failed_batches=len(current_failed_batches),
            )
            return "failed", "No questions were generated from any module", None, None

        elif total_successful_batches >= total_expected_batches:
            # Complete success - all expected batches succeeded
            logger.info(
                "generation_workflow_complete_success",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                successful_batches=total_successful_batches,
                total_expected_batches=total_expected_batches,
            )
            return "completed", None, None, batch_status

        else:
            # Partial success - some batches succeeded, but not all
            logger.info(
                "generation_workflow_partial_success",
                quiz_id=str(quiz_id),
                total_generated=total_generated,
                successful_batches=total_successful_batches,
                failed_batches=len(current_failed_batches),
                total_expected_batches=total_expected_batches,
            )
            return "partial_success", None, None, batch_status

    except Exception as e:
        logger.error(
            "generation_workflow_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return "failed", str(e), e, None


@timeout_operation(OPERATION_TIMEOUTS["question_generation"])
async def orchestrate_quiz_question_generation(
    quiz_id: UUID,
    target_question_count: int,
    llm_model: str,
    llm_temperature: float,
    language: QuizLanguage,
    generation_service: Any = None,
) -> None:
    """
    Orchestrate the complete question generation workflow for a quiz.

    This function now processes multiple question types per module based on
    the quiz's selected_modules configuration with question_batches.

    Args:
        quiz_id: UUID of the quiz to generate questions for
        target_question_count: Number of questions to generate (informational)
        llm_model: LLM model to use for generation
        llm_temperature: Temperature setting for LLM
        language: Language for question generation
        generation_service: Optional injected generation service (creates default if None)
    """
    logger.info(
        "quiz_question_generation_orchestration_started",
        quiz_id=str(quiz_id),
        target_questions=target_question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
        language=language.value,
    )

    # === Transaction 1: Reserve the Job ===
    async def _reserve_generation_job(session: Any, quiz_id: UUID) -> bool:
        """Reserve the question generation job."""
        from ..service import reserve_quiz_job

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
    (
        final_status,
        error_message,
        failure_exception,
        batch_status,
    ) = await _execute_generation_workflow(
        quiz_id,
        target_question_count,
        llm_model,
        llm_temperature,
        language,
        generation_service,
    )

    # === Helper: Update Generation Metadata ===
    async def _update_generation_metadata_in_session(
        session: Any,
        quiz_id: UUID,
        batch_status: dict[str, list[str]],
    ) -> None:
        """Update quiz generation metadata with batch results within existing session."""
        from ..service import get_quiz_for_update

        # Use get_quiz_for_update to ensure proper tracking (same as update_quiz_status)
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            return

        successful_batches = batch_status.get("successful_batches", [])
        failed_batches = batch_status.get("failed_batches", [])

        # Initialize metadata if needed
        if not quiz.generation_metadata:
            quiz.generation_metadata = {}

        # Update successful batches
        existing_successful = set(
            quiz.generation_metadata.get("successful_batches", [])
        )
        existing_successful.update(successful_batches)

        # Update failed batches (remove any that succeeded)
        existing_failed = set(quiz.generation_metadata.get("failed_batches", []))
        existing_failed.update(failed_batches)  # Add new failures from current run
        existing_failed -= existing_successful  # Remove batches that succeeded in any run (current + historical)

        # Create completely new metadata object
        new_metadata = {
            "successful_batches": list(existing_successful),
            "failed_batches": list(existing_failed),
        }

        # Assign the new metadata object
        quiz.generation_metadata = new_metadata

    # === Transaction 2: Save the Result ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
        error_message: str | None = None,
        exception: Exception | None = None,
        batch_status: dict[str, list[str]] | None = None,
    ) -> None:
        """Save the generation result to the quiz with batch-level status support and metadata update."""
        from ..service import update_quiz_status

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
            from ..exceptions import categorize_generation_error

            failure_reason = categorize_generation_error(exception, error_message)
            await update_quiz_status(
                session, quiz_id, QuizStatus.FAILED, failure_reason
            )

        # Update generation metadata if batch_status is provided
        if batch_status:
            await _update_generation_metadata_in_session(session, quiz_id, batch_status)

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        error_message,
        failure_exception,
        batch_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )
