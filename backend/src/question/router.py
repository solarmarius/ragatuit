"""Updated question router with polymorphic question support."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

# Removed unused AsyncSession import
from src.auth.dependencies import CurrentUser
from src.config import get_logger
from src.database import get_async_session
from src.question.types import QuizLanguage
from src.quiz.orchestrator import orchestrate_quiz_question_generation

from . import service
from .config.service import get_configuration_service
from .formatters import format_question_for_display
from .schemas import (
    BatchGenerationRequest,
    BatchGenerationResponse,
    GenerationRequest,
    GenerationResponse,
    QuestionCreateRequest,
    QuestionResponse,
    QuestionUpdateRequest,
)
from .types import QuestionType

router = APIRouter(prefix="/questions", tags=["questions"])
logger = get_logger("questions_v2")


@router.get("/{quiz_id}", response_model=list[QuestionResponse])
async def get_quiz_questions(
    quiz_id: UUID,
    current_user: CurrentUser,
    question_type: QuestionType | None = Query(
        None, description="Filter by question type"
    ),
    approved_only: bool = Query(False, description="Only return approved questions"),
    limit: int | None = Query(
        None, ge=1, le=100, description="Maximum questions to return"
    ),
    offset: int = Query(0, ge=0, description="Number of questions to skip"),
) -> list[dict[str, Any]]:
    """
    Retrieve questions for a quiz with filtering support.

    **Parameters:**
        quiz_id: Quiz identifier
        question_type: Filter by question type (optional)
        approved_only: Only return approved questions
        limit: Maximum number of questions to return
        offset: Number of questions to skip for pagination

    **Returns:**
        List of questions with formatted display data
    """
    logger.info(
        "quiz_questions_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_type=question_type.value if question_type else None,
        approved_only=approved_only,
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        # Get formatted questions (handled within single session)
        async with get_async_session() as session:
            formatted_questions = await service.get_formatted_questions_by_quiz(
                session=session,
                quiz_id=quiz_id,
                question_type=question_type,
                approved_only=approved_only,
                limit=limit,
                offset=offset,
            )

        logger.info(
            "quiz_questions_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            questions_found=len(formatted_questions),
        )

        return formatted_questions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "quiz_questions_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve questions. Please try again."
        )


@router.get("/{quiz_id}/{question_id}", response_model=QuestionResponse)
async def get_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Retrieve a specific question by ID.

    **Parameters:**
        quiz_id: Quiz identifier
        question_id: Question identifier

    **Returns:**
        Question with formatted display data
    """
    logger.info(
        "question_retrieval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        async with get_async_session() as session:
            # Get question
            question = await service.get_question_by_id(session, question_id)

            if not question or question.quiz_id != quiz_id:
                raise HTTPException(status_code=404, detail="Question not found")

            # Format question for display
            formatted_question = format_question_for_display(question)

        logger.info(
            "question_retrieval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return formatted_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_retrieval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve question. Please try again."
        )


@router.post("/{quiz_id}", response_model=QuestionResponse)
async def create_question(
    quiz_id: UUID,
    question_request: QuestionCreateRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Create a new question for a quiz.

    **Parameters:**
        quiz_id: Quiz identifier
        question_request: Question creation data

    **Returns:**
        Created question with formatted display data
    """
    logger.info(
        "question_creation_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_type=question_request.question_type.value,
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        # Ensure quiz_id matches
        if question_request.quiz_id != quiz_id:
            raise HTTPException(status_code=400, detail="Quiz ID mismatch")

        # Save question
        async with get_async_session() as session:
            result = await service.save_questions(
                session=session,
                quiz_id=quiz_id,
                question_type=question_request.question_type,
                questions_data=[
                    {
                        "quiz_id": quiz_id,
                        "difficulty": question_request.difficulty,
                        "tags": question_request.tags,
                        **question_request.question_data,
                    }
                ],
            )

        if result["saved_count"] == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Question validation failed: {result['errors']}",
            )

        # Get the created question
        async with get_async_session() as session:
            question_id = UUID(result["question_ids"][0])
            question = await service.get_question_by_id(session, question_id)

            if not question:
                raise HTTPException(
                    status_code=500, detail="Failed to retrieve created question"
                )

            # Format question for display
            formatted_question = format_question_for_display(question)

        logger.info(
            "question_creation_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            question_type=question_request.question_type.value,
        )

        return formatted_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_creation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to create question. Please try again."
        )


@router.put("/{quiz_id}/{question_id}", response_model=QuestionResponse)
async def update_question(
    quiz_id: UUID,
    question_id: UUID,
    question_update: QuestionUpdateRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Update a question.

    **Parameters:**
        quiz_id: Quiz identifier
        question_id: Question identifier
        question_update: Question update data

    **Returns:**
        Updated question with formatted display data
    """
    logger.info(
        "question_update_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        async with get_async_session() as session:
            # Verify question exists and belongs to quiz
            question = await service.get_question_by_id(session, question_id)
            if not question or question.quiz_id != quiz_id:
                raise HTTPException(status_code=404, detail="Question not found")

            # Update question
            updates: dict[str, Any] = {}
            if question_update.question_data is not None:
                updates["question_data"] = question_update.question_data
            if question_update.difficulty is not None:
                updates["difficulty"] = question_update.difficulty
            if question_update.tags is not None:
                updates["tags"] = question_update.tags

            updated_question = await service.update_question(
                session, question_id, updates
            )

            if not updated_question:
                raise HTTPException(status_code=500, detail="Failed to update question")

            # Format question for display
            formatted_question = format_question_for_display(updated_question)

        logger.info(
            "question_update_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return formatted_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_update_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to update question. Please try again."
        )


@router.put("/{quiz_id}/{question_id}/approve", response_model=QuestionResponse)
async def approve_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Approve a question for inclusion in the final quiz.

    **Parameters:**
        quiz_id: Quiz identifier
        question_id: Question identifier

    **Returns:**
        Approved question with formatted display data
    """
    logger.info(
        "question_approval_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        async with get_async_session() as session:
            # Verify question exists and belongs to quiz
            question = await service.get_question_by_id(session, question_id)
            if not question or question.quiz_id != quiz_id:
                raise HTTPException(status_code=404, detail="Question not found")

            # Approve question
            approved_question = await service.approve_question(session, question_id)

            if not approved_question:
                raise HTTPException(
                    status_code=500, detail="Failed to approve question"
                )

            # Format question for display
            formatted_question = format_question_for_display(approved_question)

        logger.info(
            "question_approval_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return formatted_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_approval_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to approve question. Please try again."
        )


@router.delete("/{quiz_id}/{question_id}")
async def delete_question(
    quiz_id: UUID,
    question_id: UUID,
    current_user: CurrentUser,
) -> dict[str, str]:
    """
    Delete a question from the quiz.

    **Parameters:**
        quiz_id: Quiz identifier
        question_id: Question identifier

    **Returns:**
        Confirmation message
    """
    logger.info(
        "question_deletion_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_id=str(question_id),
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        # Delete question
        async with get_async_session() as session:
            success = await service.delete_question(
                session, question_id, current_user.id
            )

        if not success:
            raise HTTPException(status_code=404, detail="Question not found")

        logger.info(
            "question_deletion_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
        )

        return {"message": "Question deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_deletion_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            question_id=str(question_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete question. Please try again."
        )


@router.post("/{quiz_id}/generate", response_model=GenerationResponse)
async def generate_questions(
    quiz_id: UUID,
    generation_request: GenerationRequest,
    current_user: CurrentUser,
) -> GenerationResponse:
    """
    Generate questions for a quiz using module-based AI generation.

    **Parameters:**
        quiz_id: Quiz identifier
        generation_request: Generation parameters

    **Returns:**
        Generation result with statistics
    """
    logger.info(
        "question_generation_initiated",
        user_id=str(current_user.id),
        quiz_id=str(quiz_id),
        question_type=generation_request.question_type.value,
        target_count=generation_request.target_count,
    )

    try:
        # Verify quiz ownership
        await _verify_quiz_ownership(quiz_id, current_user.id)

        # Ensure quiz_id matches
        if generation_request.quiz_id != quiz_id:
            raise HTTPException(status_code=400, detail="Quiz ID mismatch")

        # Get quiz to access language and other settings
        async with get_async_session() as session:
            from src.quiz.models import Quiz

            quiz = await session.get(Quiz, quiz_id)
            if not quiz:
                raise HTTPException(status_code=404, detail="Quiz not found")

        # Extract language from quiz or use default
        language = (
            quiz.language
            if hasattr(quiz, "language") and quiz.language
            else QuizLanguage.ENGLISH
        )

        # Get the current question count before generation
        async with get_async_session() as session:
            questions_before = await service.get_questions_by_quiz(session, quiz_id)
            initial_count = len(questions_before)

        # Get default configuration
        config_service = get_configuration_service()
        provider_config = config_service.get_provider_config()

        # Trigger orchestrated generation
        await orchestrate_quiz_question_generation(
            quiz_id=quiz_id,
            target_question_count=generation_request.target_count,
            llm_model=generation_request.provider_name or provider_config.model,
            llm_temperature=provider_config.temperature,
            language=language,
            question_type=generation_request.question_type,
        )

        # Check the results after generation
        async with get_async_session() as session:
            questions_after = await service.get_questions_by_quiz(session, quiz_id)
            final_count = len(questions_after)
            questions_generated = final_count - initial_count

        logger.info(
            "question_generation_completed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            questions_generated=questions_generated,
            target_count=generation_request.target_count,
        )

        from datetime import datetime

        return GenerationResponse(
            success=questions_generated > 0,
            questions_generated=questions_generated,
            target_questions=generation_request.target_count,
            error_message=None
            if questions_generated > 0
            else "No questions were generated",
            metadata={
                "provider_name": generation_request.provider_name or "openai",
                "question_type": generation_request.question_type.value,
                "language": language.value,
                "initial_count": initial_count,
                "final_count": final_count,
            },
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "question_generation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to generate questions. Please try again."
        )


@router.post("/batch/generate", response_model=BatchGenerationResponse)
async def batch_generate_questions(
    batch_request: BatchGenerationRequest,
    current_user: CurrentUser,
) -> BatchGenerationResponse:
    """
    Generate questions for multiple quizzes in batch using module-based generation.

    **Parameters:**
        batch_request: Batch generation requests

    **Returns:**
        Batch generation results
    """
    logger.info(
        "batch_question_generation_initiated",
        user_id=str(current_user.id),
        request_count=len(batch_request.requests),
    )

    try:
        # Verify ownership of all quizzes
        for request in batch_request.requests:
            await _verify_quiz_ownership(request.quiz_id, current_user.id)

        # Use orchestrator for each quiz in batch
        from datetime import datetime

        from src.question.types import QuizLanguage
        from src.quiz.orchestrator import orchestrate_quiz_question_generation

        response_results = []

        for request in batch_request.requests:
            try:
                # Get quiz to access language and other settings
                async with get_async_session() as session:
                    from src.quiz.models import Quiz

                    quiz = await session.get(Quiz, request.quiz_id)
                    if not quiz:
                        raise ValueError(f"Quiz {request.quiz_id} not found")

                # Extract language from quiz or use default
                language = (
                    quiz.language
                    if hasattr(quiz, "language") and quiz.language
                    else QuizLanguage.ENGLISH
                )

                # Get the current question count before generation
                async with get_async_session() as session:
                    questions_before = await service.get_questions_by_quiz(
                        session, request.quiz_id
                    )
                    initial_count = len(questions_before)

                # Get default configuration
                config_service = get_configuration_service()
                provider_config = config_service.get_provider_config()

                # Trigger orchestrated generation
                await orchestrate_quiz_question_generation(
                    quiz_id=request.quiz_id,
                    target_question_count=request.target_count,
                    llm_model=request.provider_name or provider_config.model,
                    llm_temperature=provider_config.temperature,
                    language=language,
                    question_type=request.question_type,
                )

                # Check the results after generation
                async with get_async_session() as session:
                    questions_after = await service.get_questions_by_quiz(
                        session, request.quiz_id
                    )
                    final_count = len(questions_after)
                    questions_generated = final_count - initial_count

                # Add successful result
                response_results.append(
                    GenerationResponse(
                        success=questions_generated > 0,
                        questions_generated=questions_generated,
                        target_questions=request.target_count,
                        error_message=None
                        if questions_generated > 0
                        else "No questions were generated",
                        metadata={
                            "provider_name": request.provider_name or "openai",
                            "question_type": request.question_type.value,
                            "language": language.value,
                            "quiz_id": str(request.quiz_id),
                        },
                        generated_at=datetime.utcnow(),
                    )
                )

            except Exception as quiz_error:
                # Add failed result for this quiz
                logger.error(
                    "batch_quiz_generation_failed",
                    quiz_id=str(request.quiz_id),
                    error=str(quiz_error),
                    exc_info=True,
                )

                response_results.append(
                    GenerationResponse(
                        success=False,
                        questions_generated=0,
                        target_questions=request.target_count,
                        error_message=f"Generation failed: {str(quiz_error)}",
                        metadata={
                            "provider_name": request.provider_name or "openai",
                            "question_type": request.question_type.value,
                            "quiz_id": str(request.quiz_id),
                            "error_type": type(quiz_error).__name__,
                        },
                        generated_at=datetime.utcnow(),
                    )
                )

        # Calculate batch statistics
        successful_requests = sum(1 for r in response_results if r.success)
        total_questions = sum(r.questions_generated for r in response_results)

        logger.info(
            "batch_question_generation_completed",
            user_id=str(current_user.id),
            total_requests=len(batch_request.requests),
            successful_requests=successful_requests,
            total_questions_generated=total_questions,
        )

        return BatchGenerationResponse(
            results=response_results,
            total_requests=len(batch_request.requests),
            successful_requests=successful_requests,
            failed_requests=len(batch_request.requests) - successful_requests,
            total_questions_generated=total_questions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "batch_question_generation_failed",
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate questions in batch. Please try again.",
        )


async def _verify_quiz_ownership(quiz_id: UUID, user_id: UUID) -> None:
    """
    Verify that a user owns a quiz.

    Args:
        quiz_id: Quiz identifier
        user_id: User identifier

    Raises:
        HTTPException: If quiz not found or user doesn't own it
    """
    from src.database import get_async_session
    from src.quiz.service import get_quiz_for_update

    async with get_async_session() as session:
        quiz = await get_quiz_for_update(session, quiz_id)

        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if quiz.owner_id != user_id:
            raise HTTPException(status_code=404, detail="Quiz not found")
