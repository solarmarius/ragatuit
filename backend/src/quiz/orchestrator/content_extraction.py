"""
Content extraction orchestration for quiz operations.

This module handles the unified content extraction workflow supporting both
Canvas modules and manual modules, with automatic question generation triggering.
"""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction

from ..constants import OPERATION_TIMEOUTS
from ..schemas import FailureReason, QuizStatus
from .core import ContentExtractorFunc, ContentSummaryFunc, timeout_operation

logger = get_logger("quiz_orchestrator_content_extraction")


async def _execute_content_extraction_workflow(
    quiz_id: UUID,
    canvas_course_id: int,
    canvas_token: str,
    selected_modules: dict[str, dict[str, Any]],
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> tuple[dict[str, Any] | None, str, dict[str, dict[str, Any]] | None]:
    """
    Execute unified content extraction workflow for any combination of source types.

    This function handles Canvas modules, manual modules, and any future source types
    in a single, elegant workflow. It automatically detects source types and processes
    each appropriately.

    Args:
        quiz_id: UUID of the quiz to extract content for
        canvas_course_id: Canvas course ID
        canvas_token: Canvas API authentication token
        selected_modules: Dictionary of selected modules with source_type info
        content_extractor: Function to extract content from Canvas modules
        content_summarizer: Function to generate content summary

    Returns:
        Tuple of (extracted_content, final_status, cleaned_selected_modules)
    """
    logger.info(
        "content_extraction_workflow_started",
        quiz_id=str(quiz_id),
        canvas_course_id=canvas_course_id,
        total_modules=len(selected_modules),
    )

    try:
        all_extracted_content = {}
        canvas_modules = []
        manual_modules = []

        # Categorize modules by source_type - this is the key to elegant handling
        for module_id, module_data in selected_modules.items():
            source_type = module_data.get(
                "source_type", "canvas"
            )  # Default to canvas for backward compatibility

            if source_type == "canvas":
                canvas_modules.append(int(module_id))
            elif source_type == "manual":
                manual_modules.append((module_id, module_data))
            else:
                # Future extensibility: log warning about unknown source types
                logger.warning(
                    "unknown_source_type_encountered",
                    quiz_id=str(quiz_id),
                    module_id=module_id,
                    source_type=source_type,
                    message="Treating as canvas module",
                )
                # Treat unknown source types as canvas modules for safety
                try:
                    canvas_modules.append(int(module_id))
                except ValueError:
                    logger.error(
                        "invalid_module_id_for_canvas_fallback",
                        quiz_id=str(quiz_id),
                        module_id=module_id,
                        source_type=source_type,
                    )

        logger.info(
            "content_modules_categorized",
            quiz_id=str(quiz_id),
            canvas_module_count=len(canvas_modules),
            manual_module_count=len(manual_modules),
        )

        # Extract Canvas content if there are Canvas modules
        if canvas_modules:
            logger.info(
                "extracting_canvas_content",
                quiz_id=str(quiz_id),
                canvas_module_ids=canvas_modules,
            )
            canvas_content = await content_extractor(
                canvas_token, canvas_course_id, canvas_modules
            )
            all_extracted_content.update(canvas_content)

        # Process manual content if there are manual modules
        if manual_modules:
            logger.info(
                "processing_manual_content",
                quiz_id=str(quiz_id),
                manual_module_count=len(manual_modules),
            )
            for module_id, module_data in manual_modules:
                # Manual modules already have processed content from quiz creation
                # Format as single-page content to match Canvas structure
                all_extracted_content[module_id] = [
                    {
                        "content": module_data.get("content", ""),
                        "word_count": module_data.get("word_count", 0),
                        "source_type": "manual",
                        "processing_metadata": module_data.get(
                            "processing_metadata", {}
                        ),
                        "content_type": module_data.get("content_type", "text"),
                        "title": module_data["name"],
                    }
                ]

        # Clean selected_modules to prevent content duplication
        # Keep only essential fields needed for question generation
        cleaned_selected_modules = {}
        for module_id, module_data in selected_modules.items():
            cleaned_selected_modules[module_id] = {
                key: value
                for key, value in module_data.items()
                if key in ["name", "source_type", "question_batches"]
            }

        # Generate content summary for all modules
        content_summary = content_summarizer(all_extracted_content)

        logger.info(
            "content_extraction_workflow_completed",
            quiz_id=str(quiz_id),
            canvas_course_id=canvas_course_id,
            modules_processed=content_summary["modules_processed"],
            total_pages=content_summary["total_pages"],
            total_word_count=content_summary["total_word_count"],
            canvas_modules_processed=len(canvas_modules),
            manual_modules_processed=len(manual_modules),
        )

        # Check if meaningful content was extracted
        total_word_count = content_summary.get("total_word_count", 0)
        total_pages = content_summary.get("total_pages", 0)

        if total_word_count == 0 or total_pages == 0:
            logger.warning(
                "extraction_completed_but_no_content_found",
                quiz_id=str(quiz_id),
                canvas_course_id=canvas_course_id,
                total_word_count=total_word_count,
                total_pages=total_pages,
            )
            return None, "no_content", cleaned_selected_modules
        else:
            return all_extracted_content, "completed", cleaned_selected_modules

    except Exception as e:
        logger.error(
            "content_extraction_workflow_failed",
            quiz_id=str(quiz_id),
            canvas_course_id=canvas_course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None, "failed", selected_modules


@timeout_operation(OPERATION_TIMEOUTS["content_extraction"])
async def orchestrate_content_extraction(
    quiz_id: UUID,
    canvas_course_id: int,
    canvas_token: str,
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> None:
    """
    Orchestrate unified content extraction workflow for any combination of source types.

    This unified orchestrator elegantly handles Canvas-only, manual-only, or mixed
    quizzes without requiring complex detection logic. It automatically determines
    the source types from the quiz's selected_modules and processes accordingly.

    Args:
        quiz_id: UUID of the quiz to extract content for
        canvas_course_id: Canvas course ID
        canvas_token: Canvas API authentication token
        content_extractor: Function to extract content from Canvas
        content_summarizer: Function to generate content summary
    """
    logger.info(
        "content_extraction_orchestration_started",
        quiz_id=str(quiz_id),
        canvas_course_id=canvas_course_id,
    )

    # === Transaction 1: Reserve the Job and Get Quiz Settings ===
    async def _reserve_extraction_job(
        session: Any, quiz_id: UUID
    ) -> dict[str, Any] | None:
        """Reserve extraction job and return quiz settings with selected_modules."""
        from ..service import reserve_quiz_job

        return await reserve_quiz_job(session, quiz_id, "extraction")

    quiz_settings = await execute_in_transaction(
        _reserve_extraction_job,
        quiz_id,
        isolation_level="REPEATABLE READ",
        retries=3,
    )

    if not quiz_settings:
        logger.info(
            "extraction_orchestration_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # Get selected_modules from quiz settings
    selected_modules = quiz_settings.get("selected_modules", {})

    # === Unified Content Extraction (outside transaction) ===
    (
        extracted_content,
        final_status,
        cleaned_selected_modules,
    ) = await _execute_content_extraction_workflow(
        quiz_id,
        canvas_course_id,
        canvas_token,
        selected_modules,
        content_extractor,
        content_summarizer,
    )

    # === Transaction 2: Save the Result ===
    async def _save_extraction_result(
        session: Any,
        quiz_id: UUID,
        content: dict[str, Any] | None,
        status: str,
        cleaned_modules: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Save the extraction result to the quiz."""
        from ..service import update_quiz_status

        additional_fields = {}
        if status == "completed" and content is not None:
            additional_fields["extracted_content"] = content

        # Save cleaned selected_modules to prevent content duplication
        if cleaned_modules is not None:
            additional_fields["selected_modules"] = cleaned_modules

        if status == "completed":
            # Keep status as EXTRACTING_CONTENT to allow question generation to proceed
            await update_quiz_status(
                session,
                quiz_id,
                QuizStatus.EXTRACTING_CONTENT,
                None,
                **additional_fields,
            )
        elif status == "no_content":
            # No meaningful content was extracted
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
        cleaned_selected_modules,
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
            # Import here to avoid circular imports
            from .question_generation import orchestrate_quiz_question_generation

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
        from ..service import update_quiz_status

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
