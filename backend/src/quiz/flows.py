"""
Quiz module orchestration flows.

This module orchestrates quiz operations using functional composition:
- Content extraction flows for Canvas module content processing
- Question generation flows for LLM-based MCQ generation
- Export flows for Canvas quiz export operations
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.canvas.flows import (
    export_quiz_to_canvas_flow,
    extract_content_for_modules,
    get_content_summary,
)
from src.database import execute_in_transaction
from src.logging_config import get_logger
from src.question.mcq_generation_service import MCQGenerationService

from .service import get_quiz_for_update

logger = get_logger("quiz_flows")


async def quiz_content_extraction_flow(
    quiz_id: UUID, course_id: int, module_ids: list[int], canvas_token: str
) -> None:
    """
    Orchestrates the content extraction task using a robust two-transaction approach.

    Transaction 1: Reserve the job (very fast)
    I/O Operation: Extract content from Canvas (outside transaction)
    Transaction 2: Save the result (very fast)

    Args:
        quiz_id: UUID of the quiz to extract content for
        course_id: Canvas course ID
        module_ids: List of Canvas module IDs to process
        canvas_token: Canvas API authentication token
    """
    logger.info(
        "content_extraction_started",
        quiz_id=str(quiz_id),
        course_id=course_id,
        module_count=len(module_ids),
    )

    # === Transaction 1: Reserve the Job (very fast) ===
    async def _reserve_job(session: Any, quiz_id: UUID) -> dict[str, Any] | None:
        """Reserve the extraction job and return quiz settings if successful."""
        quiz = await get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("content_extraction_quiz_not_found", quiz_id=str(quiz_id))
            return None

        if quiz.content_extraction_status in ["processing", "completed"]:
            logger.info(
                "content_extraction_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.content_extraction_status,
            )
            return None  # Job already taken or completed

        # Reserve the job
        quiz.content_extraction_status = "processing"
        await session.flush()  # Make status visible immediately

        # Return quiz settings for later use
        return {
            "target_questions": quiz.question_count,
            "llm_model": quiz.llm_model,
            "llm_temperature": quiz.llm_temperature,
        }

    quiz_settings = await execute_in_transaction(
        _reserve_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not quiz_settings:
        logger.info(
            "content_extraction_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Slow I/O Operation (occurs outside any transaction) ===
    try:
        # Use functional content extraction flows
        extracted_content = await extract_content_for_modules(
            canvas_token, course_id, module_ids
        )
        content_summary = get_content_summary(extracted_content)

        logger.info(
            "content_extraction_completed",
            quiz_id=str(quiz_id),
            course_id=course_id,
            modules_processed=content_summary["modules_processed"],
            total_pages=content_summary["total_pages"],
            total_word_count=content_summary["total_word_count"],
        )

        final_status = "completed"

    except Exception as e:
        logger.error(
            "content_extraction_failed_during_api_call",
            quiz_id=str(quiz_id),
            course_id=course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        extracted_content = None
        final_status = "failed"

    # === Transaction 2: Save the Result (very fast) ===
    async def _save_result(
        session: Any,
        quiz_id: UUID,
        content: dict[str, Any] | None,
        status: str,
    ) -> None:
        """Save the extraction result to the quiz."""
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error(
                "content_extraction_quiz_not_found_during_save", quiz_id=str(quiz_id)
            )
            return

        quiz.content_extraction_status = status
        if status == "completed" and content is not None:
            quiz.extracted_content = content
            quiz.content_extracted_at = datetime.now(timezone.utc)

    await execute_in_transaction(
        _save_result,
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
        await quiz_question_generation_flow(
            quiz_id=quiz_id,
            target_question_count=quiz_settings["target_questions"],
            llm_model=quiz_settings["llm_model"],
            llm_temperature=quiz_settings["llm_temperature"],
        )


async def quiz_question_generation_flow(
    quiz_id: UUID, target_question_count: int, llm_model: str, llm_temperature: float
) -> None:
    """
    Orchestrates the question generation task using a robust two-transaction approach.

    Transaction 1: Reserve the job (very fast)
    I/O Operation: Generate questions via LLM (outside transaction)
    Transaction 2: Save the result (very fast)

    Args:
        quiz_id: UUID of the quiz to generate questions for
        target_question_count: Number of questions to generate
        llm_model: LLM model to use for generation
        llm_temperature: Temperature setting for LLM
    """
    logger.info(
        "question_generation_started",
        quiz_id=str(quiz_id),
        target_questions=target_question_count,
        llm_model=llm_model,
        llm_temperature=llm_temperature,
    )

    # === Transaction 1: Reserve the Job (very fast) ===
    async def _reserve_generation_job(session: Any, quiz_id: UUID) -> bool:
        """Reserve the question generation job."""
        quiz = await get_quiz_for_update(session, quiz_id)

        if not quiz:
            logger.error("question_generation_quiz_not_found", quiz_id=str(quiz_id))
            return False

        if quiz.llm_generation_status in ["processing", "completed"]:
            logger.info(
                "question_generation_job_already_taken",
                quiz_id=str(quiz_id),
                current_status=quiz.llm_generation_status,
            )
            return False  # Job already taken or completed

        # Reserve the job
        quiz.llm_generation_status = "processing"
        await session.flush()  # Make status visible immediately
        return True

    should_proceed = await execute_in_transaction(
        _reserve_generation_job, quiz_id, isolation_level="REPEATABLE READ", retries=3
    )

    if not should_proceed:
        logger.info(
            "question_generation_skipped",
            quiz_id=str(quiz_id),
            reason="job_already_running_or_complete",
        )
        return

    # === Slow I/O Operation (occurs outside any transaction) ===
    try:
        mcq_service = MCQGenerationService()
        results = await mcq_service.generate_mcqs_for_quiz(
            quiz_id=quiz_id,
            target_question_count=target_question_count,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
        )

        if results["success"]:
            final_status = "completed"
            logger.info(
                "question_generation_completed",
                quiz_id=str(quiz_id),
                questions_generated=results["questions_generated"],
                target_questions=target_question_count,
            )
        else:
            final_status = "failed"
            logger.error(
                "question_generation_failed_during_llm_call",
                quiz_id=str(quiz_id),
                error_message=results["error_message"],
            )

    except Exception as e:
        logger.error(
            "question_generation_failed_during_llm_call",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        final_status = "failed"

    # === Transaction 2: Save the Result (very fast) ===
    async def _save_generation_result(
        session: Any,
        quiz_id: UUID,
        status: str,
    ) -> None:
        """Save the generation result to the quiz."""
        quiz = await get_quiz_for_update(session, quiz_id)
        if not quiz:
            logger.error(
                "question_generation_quiz_not_found_during_save", quiz_id=str(quiz_id)
            )
            return

        quiz.llm_generation_status = status

    await execute_in_transaction(
        _save_generation_result,
        quiz_id,
        final_status,
        isolation_level="REPEATABLE READ",
        retries=3,
    )


async def quiz_export_background_flow(quiz_id: UUID, canvas_token: str) -> None:
    """
    Background task flow to export a quiz to Canvas LMS.

    Simple wrapper around the main export flow which handles
    proper transaction management for background task compatibility.

    Args:
        quiz_id: UUID of the quiz to export
        canvas_token: Canvas API authentication token
    """
    logger.info(
        "canvas_export_background_task_started",
        quiz_id=str(quiz_id),
    )

    try:
        # Use the main export flow which properly handles transactions
        result = await export_quiz_to_canvas_flow(quiz_id, canvas_token)

        logger.info(
            "canvas_export_background_task_completed",
            quiz_id=str(quiz_id),
            success=result.get("success", False),
            canvas_quiz_id=result.get("canvas_quiz_id"),
            exported_questions=result.get("exported_questions", 0),
        )

    except Exception as e:
        logger.error(
            "canvas_export_background_task_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
