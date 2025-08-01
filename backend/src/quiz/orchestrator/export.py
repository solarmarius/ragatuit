"""
Canvas export orchestration for quiz operations.

This module handles the complete Canvas export workflow with all-or-nothing
approach and automatic rollback on failures.
"""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import execute_in_transaction

from ..constants import OPERATION_TIMEOUTS
from ..schemas import FailureReason, QuizStatus
from .core import QuestionExporterFunc, QuizCreatorFunc, timeout_operation

logger = get_logger("quiz_orchestrator_export")


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
        from ..service import reserve_quiz_job

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

                from ..service import update_quiz_status

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
            from ..service import update_quiz_status

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
