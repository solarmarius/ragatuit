# Partial Failure Saving Implementation Guide

**Date**: July 24, 2025
**Feature**: Batch-Level Question Generation with Partial Success Support
**Version**: 1.0

## 1. Feature Overview

### What This Feature Does

The Partial Failure Saving feature transforms the quiz question generation system from an "all-or-nothing" approach to a batch-level success tracking system. Instead of marking an entire quiz as failed when some questions fail to generate, the system now:

1. **Tracks success at the batch level** - A batch is defined as a combination of module + question type + target count
2. **Saves only fully successful batches** - Only batches with 100% validation success are saved to the database
3. **Allows partial completion** - Users can review successfully generated questions while retrying only failed batches
4. **Preserves user progress** - Successfully generated questions are never lost during retry operations

### Business Value & User Benefits

**Before**: If 190 out of 200 questions generated successfully but 10 failed validation, the entire quiz would be marked as failed and ALL 190 questions would be lost.

**After**: The 190 successful questions are saved and available for review, while only the 10 failed questions need to be regenerated.

**Key Benefits**:
- **Reduced frustration** - Users don't lose progress due to partial failures
- **Improved efficiency** - No need to regenerate successful questions
- **Better resource utilization** - Fewer API calls to LLM providers
- **Enhanced user control** - Users can proceed with partial results or retry for completion
- **Transparent progress tracking** - Clear visibility into what succeeded and what failed

### Context & Background

The original system used module-level generation with an 80% success threshold. If total questions generated fell below 80% of the target, the entire quiz was marked as failed. This approach had critical issues:

1. **Progress loss** - Successful questions were inaccessible in failed state
2. **Inefficient retries** - Retrying would regenerate all questions, including successful ones
3. **Poor user experience** - No visibility into partial success scenarios

## 2. Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                          │
├─────────────────────────────────────────────────────────────┤
│ • QuestionGenerationTrigger (shows partial progress)        │
│ • Status Components (handles READY_FOR_REVIEW_PARTIAL)      │
│ • Retry Logic (targets only failed batches)                 │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ HTTP API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Backend API (FastAPI)                       │
├─────────────────────────────────────────────────────────────┤
│ Quiz Router (/generate-questions with retry logic)          │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Quiz Orchestrator                           │
├─────────────────────────────────────────────────────────────┤
│ • Batch-level success tracking                              │
│ • Metadata management                                       │
│ • Status transitions (PARTIAL vs FULL success)             │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            Question Generation Service                       │
├─────────────────────────────────────────────────────────────┤
│ • Selective batch retry logic                               │
│ • Failed batch detection                                    │
│ • Metadata analysis                                         │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              Module Batch Workflow                          │
├─────────────────────────────────────────────────────────────┤
│ • 100% validation requirement for saving                    │
│ • Batch success/failure tracking                            │
│ • Failed batch metadata storage                             │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
├─────────────────────────────────────────────────────────────┤
│ • Quiz.generation_metadata (JSONB)                          │
│ • Question table (only successful batches)                  │
│ • Status tracking                                           │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing System

This feature extends the existing question generation pipeline without breaking existing functionality:

- **Maintains backward compatibility** - All existing statuses continue to work
- **Enhances orchestrator** - Adds batch-level logic to existing workflow
- **Extends API contracts** - New status values, enhanced metadata
- **Preserves data integrity** - No changes to core database schema

## 3. Dependencies & Prerequisites

### External Dependencies

All dependencies are already present in the existing system:

- **Python 3.11+** - Backend runtime
- **FastAPI** - Web framework
- **SQLModel/SQLAlchemy** - ORM and database models
- **PostgreSQL** - Database with JSONB support
- **React 18+** - Frontend framework
- **TypeScript** - Frontend type safety
- **Chakra UI** - UI component library

### Environment Setup

No additional environment setup required. The feature uses existing:
- Database connections
- LLM provider integrations
- Authentication systems
- Logging infrastructure

### Version Requirements

Uses existing versions defined in:
- `backend/pyproject.toml`
- `frontend/package.json`

## 4. Implementation Details

### 4.1 File Structure

#### Files to Modify

```
backend/src/
├── quiz/
│   ├── schemas.py              # Add READY_FOR_REVIEW_PARTIAL status
│   ├── orchestrator.py         # Batch-level success tracking
│   └── router.py               # Retry logic for partial states
├── question/
│   ├── services/
│   │   └── generation_service.py  # Selective batch retry
│   └── workflows/
│       └── module_batch_workflow.py  # 100% success requirement
└── ...

frontend/src/
├── components/
│   └── Questions/
│       └── QuestionGenerationTrigger.tsx  # Partial state UI
├── lib/
│   └── constants.ts            # New status constant
└── ...
```

#### New Files

No new files are created - all changes are modifications to existing files.

### 4.2 Step-by-Step Implementation

#### Step 1: Add New Quiz Status

**File**: `backend/src/quiz/schemas.py`

```python
class QuizStatus(str, Enum):
    """Consolidated status values for quiz workflow."""

    CREATED = "created"
    EXTRACTING_CONTENT = "extracting_content"
    GENERATING_QUESTIONS = "generating_questions"
    READY_FOR_REVIEW = "ready_for_review"
    READY_FOR_REVIEW_PARTIAL = "ready_for_review_partial"  # NEW STATUS
    EXPORTING_TO_CANVAS = "exporting_to_canvas"
    PUBLISHED = "published"
    FAILED = "failed"
```

**Purpose**: This new status indicates that at least one batch succeeded but not all batches completed successfully. Users can review generated questions and retry failed batches.

**Key Points**:
- Maintains enum string values for database compatibility
- Inserted logically between READY_FOR_REVIEW and EXPORTING_TO_CANVAS
- Follows existing naming convention

#### Step 2: Update Orchestrator for Batch-Level Tracking

**File**: `backend/src/quiz/orchestrator.py`

**Modify** `_execute_generation_workflow()` function around lines 278-441:

```python
async def _execute_generation_workflow(
    quiz_id: UUID,
    target_question_count: int,
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
        batch_results = await generation_service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id=quiz_id,
            extracted_content=extracted_content,
            provider_name=provider_name,
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
                    successful_batches.append({
                        "batch_key": batch_key,
                        "module_id": module_id,
                        "module_name": module_info.get("name", "Unknown"),
                        "question_type": question_type.value,
                        "target_count": expected_count,
                        "generated_count": actual_count,
                        "status": "success",
                        "questions_saved": True
                    })
                else:
                    # Failed batch - didn't meet target
                    failed_batches.append({
                        "batch_key": batch_key,
                        "module_id": module_id,
                        "module_name": module_info.get("name", "Unknown"),
                        "question_type": question_type.value,
                        "target_count": expected_count,
                        "generated_count": actual_count,
                        "status": "failed",
                        "questions_saved": False,
                        "error": f"Generated {actual_count}/{expected_count} questions"
                    })

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
    successful_batches: list[dict],
    failed_batches: list[dict],
    total_generated: int,
    total_target: int,
) -> None:
    """Store batch-level generation results in quiz metadata."""
    from src.database import get_async_session
    from src.quiz.models import Quiz
    from datetime import datetime

    async with get_async_session() as session:
        quiz = await session.get(Quiz, quiz_id)
        if not quiz:
            return

        # Create generation attempt record
        attempt_record = {
            "attempt_number": len(quiz.generation_metadata.get("generation_attempts", [])) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "partial_success" if failed_batches else "complete_success",
            "batch_results": {}
        }

        # Add successful batches to record
        for batch in successful_batches:
            attempt_record["batch_results"][batch["batch_key"]] = batch

        # Add failed batches to record
        for batch in failed_batches:
            attempt_record["batch_results"][batch["batch_key"]] = batch

        # Update quiz metadata
        if not quiz.generation_metadata:
            quiz.generation_metadata = {}

        if "generation_attempts" not in quiz.generation_metadata:
            quiz.generation_metadata["generation_attempts"] = []

        quiz.generation_metadata["generation_attempts"].append(attempt_record)

        # Update summary information
        quiz.generation_metadata.update({
            "failed_batches": [batch["batch_key"] for batch in failed_batches],
            "successful_batches": [batch["batch_key"] for batch in successful_batches],
            "total_questions_saved": total_generated,
            "total_questions_target": total_target,
            "last_updated": datetime.utcnow().isoformat()
        })

        await session.commit()

        logger.info(
            "generation_metadata_stored",
            quiz_id=str(quiz_id),
            successful_batches=len(successful_batches),
            failed_batches=len(failed_batches),
            attempt_number=attempt_record["attempt_number"]
        )
```

**Modify** `_save_generation_result()` function around lines 750-779:

```python
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
        await update_quiz_status(session, quiz_id, QuizStatus.READY_FOR_REVIEW_PARTIAL)
    elif status == "failed":
        # No batches succeeded - complete failure
        from .exceptions import categorize_generation_error
        failure_reason = categorize_generation_error(exception, error_message)
        await update_quiz_status(session, quiz_id, QuizStatus.FAILED, failure_reason)
```

**Purpose**: These changes transform the orchestrator to track success at the batch level rather than overall percentage. Key improvements:

1. **Batch Analysis** - Evaluates each module+question_type+count combination separately
2. **100% Success Requirement** - Only batches that fully meet their target are considered successful
3. **Metadata Storage** - Comprehensive tracking of which batches succeeded/failed
4. **Status Logic** - Three outcomes: complete success, partial success, or complete failure

#### Step 3: Modify Batch Workflow for 100% Success Requirement

**File**: `backend/src/question/workflows/module_batch_workflow.py`

**Modify** `save_questions()` method around lines 598-640:

```python
async def save_questions(self, state: ModuleBatchState) -> ModuleBatchState:
    """Save questions only if batch achieved 100% validation success."""
    # Combine preserved successful questions with newly generated ones
    all_questions = state.successful_questions_preserved + state.generated_questions

    # Calculate success rate for this batch
    total_questions = len(all_questions)
    success_rate = total_questions / state.target_question_count if state.target_question_count > 0 else 0

    # Only save if we achieved 100% success (or very close due to rounding)
    if success_rate < 0.99:  # Allow for tiny floating point errors
        logger.warning(
            "module_batch_not_saving_partial_success",
            module_id=state.module_id,
            questions_generated=total_questions,
            target_questions=state.target_question_count,
            success_rate=f"{success_rate*100:.1f}%",
            reason="Batch did not achieve 100% success rate"
        )

        # Don't save questions, but track this as a failed batch
        state.error_message = f"Batch incomplete: {total_questions}/{state.target_question_count} questions generated"
        return state

    if not all_questions:
        logger.warning(
            "module_batch_no_questions_to_save",
            module_id=state.module_id,
            preserved_count=len(state.successful_questions_preserved),
            generated_count=len(state.generated_questions),
        )
        return state

    try:
        async with get_async_session() as session:
            # Add batch metadata to each question
            for question in all_questions:
                # Add batch tracking information to question data
                if not question.question_data:
                    question.question_data = {}

                question.question_data.update({
                    "batch_key": f"{state.module_id}_{question.question_type.value}_{state.target_question_count}",
                    "module_id": state.module_id,
                    "module_name": state.module_name,
                    "batch_success_rate": 1.0,  # This batch achieved 100% success
                    "generation_timestamp": datetime.utcnow().isoformat()
                })

                session.add(question)

            # Commit all questions
            await session.commit()

            logger.info(
                "module_batch_questions_saved_100_percent_success",
                module_id=state.module_id,
                questions_saved=len(all_questions),
                preserved_questions=len(state.successful_questions_preserved),
                newly_generated=len(state.generated_questions),
                target_questions=state.target_question_count,
                success_rate="100%"
            )

    except Exception as e:
        logger.error(
            "module_batch_save_failed",
            module_id=state.module_id,
            error=str(e),
            exc_info=True,
        )
        state.error_message = f"Failed to save questions: {str(e)}"

    return state
```

**Purpose**: This modification ensures that questions are only saved to the database when a batch achieves 100% validation success. Failed or partial batches are tracked in metadata but their questions are not saved, preventing incomplete data from being accessible to users.

#### Step 4: Enhance Generation Service with Selective Retry

**File**: `backend/src/question/services/generation_service.py`

**Add new method** after line 178:

```python
async def generate_questions_for_quiz_with_batch_tracking(
    self,
    quiz_id: UUID,
    extracted_content: dict[str, str],
    provider_name: str = "openai",
) -> dict[str, list[Any]]:
    """
    Generate questions with batch-level tracking and selective retry support.

    This method handles both initial generation and retry scenarios by:
    1. Checking existing metadata for successful batches
    2. Only generating questions for batches that haven't succeeded
    3. Preserving all successful batches from previous attempts

    Args:
        quiz_id: Quiz identifier
        extracted_content: Module content mapped by module ID
        provider_name: LLM provider to use

    Returns:
        Dictionary mapping module IDs to lists of generated questions

    Raises:
        ValueError: If quiz not found or invalid parameters
        Exception: If generation fails
    """
    try:
        from src.quiz.models import Quiz

        async with get_async_session() as session:
            quiz = await session.get(Quiz, quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            # Check for existing successful batches to avoid regenerating
            successful_batches = set()
            if quiz.generation_metadata and "successful_batches" in quiz.generation_metadata:
                successful_batches = set(quiz.generation_metadata["successful_batches"])

                logger.info(
                    "found_existing_successful_batches",
                    quiz_id=str(quiz_id),
                    successful_batches=len(successful_batches),
                    batch_keys=list(successful_batches)
                )

            # Get provider instance
            from ..providers import LLMProvider

            provider_enum = LLMProvider(provider_name.lower())
            provider = self.provider_registry.get_provider(provider_enum)

            # Prepare module data, excluding already successful batches
            modules_data = {}
            skipped_modules = []

            for module_id, module_info in quiz.selected_modules.items():
                # Create batch key for this module
                batch_key = f"{module_id}_{quiz.question_type.value}_{module_info['question_count']}"

                if batch_key in successful_batches:
                    # This batch already succeeded, skip it
                    skipped_modules.append({
                        "module_id": module_id,
                        "batch_key": batch_key,
                        "reason": "already_successful"
                    })
                    continue

                if module_id in extracted_content:
                    modules_data[module_id] = {
                        "name": module_info["name"],
                        "content": extracted_content[module_id],
                        "question_count": module_info["question_count"],
                        "batch_key": batch_key
                    }
                else:
                    logger.warning(
                        "module_content_missing_for_retry",
                        quiz_id=str(quiz_id),
                        module_id=module_id,
                        module_name=module_info.get("name", "unknown"),
                    )

            if skipped_modules:
                logger.info(
                    "skipping_successful_batches",
                    quiz_id=str(quiz_id),
                    skipped_count=len(skipped_modules),
                    skipped_batches=[m["batch_key"] for m in skipped_modules]
                )

            if not modules_data:
                if successful_batches:
                    logger.info(
                        "no_batches_need_generation",
                        quiz_id=str(quiz_id),
                        reason="all_batches_already_successful"
                    )
                    # Return empty results since all batches are already complete
                    return {}
                else:
                    raise ValueError("No module content available for generation")

            # Convert language string to enum
            language = (
                QuizLanguage.NORWEGIAN
                if quiz.language == "no"
                else QuizLanguage.ENGLISH
            )

            # Process only the modules that need generation
            processor = ParallelModuleProcessor(
                llm_provider=provider,
                template_manager=self.template_manager,
                language=language,
                question_type=quiz.question_type,
            )

            results = await processor.process_all_modules(quiz_id, modules_data)

            # Calculate totals for logging
            total_generated = sum(len(questions) for questions in results.values())
            total_attempted = len(modules_data)

            logger.info(
                "batch_tracking_generation_completed",
                quiz_id=str(quiz_id),
                total_questions_generated=total_generated,
                modules_attempted=total_attempted,
                modules_skipped=len(skipped_modules),
                successful_modules=sum(1 for q in results.values() if q),
            )

            return results

    except Exception as e:
        logger.error(
            "batch_tracking_generation_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise


async def get_failed_batches_for_retry(self, quiz_id: UUID) -> list[dict[str, Any]]:
    """
    Get information about failed batches that can be retried.

    Args:
        quiz_id: Quiz identifier

    Returns:
        List of failed batch information dictionaries
    """
    try:
        from src.quiz.models import Quiz

        async with get_async_session() as session:
            quiz = await session.get(Quiz, quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")

            failed_batches = []
            if quiz.generation_metadata and "failed_batches" in quiz.generation_metadata:
                failed_batch_keys = quiz.generation_metadata["failed_batches"]

                # Get detailed information from the latest generation attempt
                attempts = quiz.generation_metadata.get("generation_attempts", [])
                if attempts:
                    latest_attempt = attempts[-1]
                    batch_results = latest_attempt.get("batch_results", {})

                    for batch_key in failed_batch_keys:
                        if batch_key in batch_results:
                            batch_info = batch_results[batch_key]
                            if batch_info.get("status") == "failed":
                                failed_batches.append({
                                    "batch_key": batch_key,
                                    "module_id": batch_info.get("module_id"),
                                    "module_name": batch_info.get("module_name"),
                                    "question_type": batch_info.get("question_type"),
                                    "target_count": batch_info.get("target_count"),
                                    "generated_count": batch_info.get("generated_count"),
                                    "error": batch_info.get("error")
                                })

            logger.info(
                "failed_batches_retrieved_for_retry",
                quiz_id=str(quiz_id),
                failed_batches_count=len(failed_batches)
            )

            return failed_batches

    except Exception as e:
        logger.error(
            "failed_batches_retrieval_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise
```

**Purpose**: These methods add intelligent batch tracking to the generation service:

1. **Selective Generation** - Only generates questions for batches that haven't already succeeded
2. **Metadata Awareness** - Reads quiz metadata to understand which batches succeeded/failed
3. **Retry Support** - Provides detailed information about failed batches for retry scenarios

#### Step 5: Update Quiz Router for Partial State Support

**File**: `backend/src/quiz/router.py`

**Modify** `trigger_question_generation()` function around lines 431-523:

```python
@router.post("/{quiz_id}/generate-questions")
async def trigger_question_generation(
    quiz: QuizOwnership,
    current_user: CurrentUser,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """
    Manually trigger question generation for a quiz with retry support.

    This endpoint supports both initial generation and retry scenarios:
    - Initial generation: Generates questions for all selected modules
    - Retry from FAILED: Regenerates all questions (original behavior)
    - Retry from READY_FOR_REVIEW_PARTIAL: Only generates questions for failed batches

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to generate questions for

    **Returns:**
        dict: Status message indicating generation has been triggered

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 400 if content extraction not completed
        HTTPException: 409 if question generation already in progress
        HTTPException: 500 if unable to trigger generation
    """
    logger.info(
        "manual_question_generation_triggered",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
        current_status=quiz.status.value,
    )

    try:
        # Enhanced validation for partial states
        validate_question_generation_ready_with_partial_support(quiz)

        # Prepare generation using service layer
        generation_params = prepare_question_generation(
            session, quiz.id, current_user.id
        )

        # Determine if this is a retry scenario
        is_retry = quiz.status in [QuizStatus.FAILED, QuizStatus.READY_FOR_REVIEW_PARTIAL]
        retry_type = "complete" if quiz.status == QuizStatus.FAILED else "partial"

        if is_retry:
            logger.info(
                "question_generation_retry_detected",
                quiz_id=str(quiz.id),
                retry_type=retry_type,
                current_status=quiz.status.value,
            )

        # Trigger question generation in the background using safe orchestrator wrapper
        background_tasks.add_task(
            safe_background_orchestration,
            orchestrate_quiz_question_generation,
            "question_generation",
            quiz.id,
            quiz.id,
            generation_params["question_count"],
            generation_params["llm_model"],
            generation_params["llm_temperature"],
            generation_params["language"],
        )

        success_message = (
            "Question generation retry started for failed batches"
            if retry_type == "partial"
            else "Question generation started"
        )

        logger.info(
            "manual_question_generation_started",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            question_count=generation_params["question_count"],
            llm_model=generation_params["llm_model"],
            is_retry=is_retry,
            retry_type=retry_type,
        )

        return {"message": success_message}

    except ValueError as e:
        logger.warning(
            "manual_generation_validation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
        )

        # Map ValueError to appropriate HTTP status
        if "Content extraction must be completed" in str(e):
            status_code = 400
        else:
            status_code = 409

        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(
            "manual_question_generation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=ERROR_MESSAGES["generation_trigger_failed"]
        )
```

**Add new validation function** in the same file:

```python
def validate_question_generation_ready_with_partial_support(quiz: Quiz) -> None:
    """
    Validate that quiz is ready for question generation, including partial retry support.

    Supports generation in these scenarios:
    1. Initial generation: EXTRACTING_CONTENT status with extracted content
    2. Complete retry: FAILED status (original behavior)
    3. Partial retry: READY_FOR_REVIEW_PARTIAL status

    Args:
        quiz: Quiz object to validate

    Raises:
        ValueError: If quiz is not in a valid state for generation
    """
    valid_statuses = [
        QuizStatus.EXTRACTING_CONTENT,  # Initial generation
        QuizStatus.FAILED,              # Complete retry
        QuizStatus.READY_FOR_REVIEW_PARTIAL,  # Partial retry
    ]

    if quiz.status not in valid_statuses:
        raise ValueError(
            f"Quiz status must be one of {[s.value for s in valid_statuses]} "
            f"for question generation, but got {quiz.status.value}"
        )

    # For partial retry, validate that there are actually failed batches
    if quiz.status == QuizStatus.READY_FOR_REVIEW_PARTIAL:
        if not quiz.generation_metadata or not quiz.generation_metadata.get("failed_batches"):
            raise ValueError(
                "No failed batches found for partial retry. "
                "Quiz may have already been fully completed."
            )

    # Content extraction validation (for initial generation)
    if quiz.status == QuizStatus.EXTRACTING_CONTENT:
        if not quiz.extracted_content:
            raise ValueError("Content extraction must be completed before question generation")

        if not quiz.selected_modules:
            raise ValueError("No modules selected for question generation")

    logger.debug(
        "question_generation_validation_passed",
        quiz_id=str(quiz.id),
        status=quiz.status.value,
        validation_type="partial_support"
    )
```

**Purpose**: These changes enable the router to handle retry scenarios from partial success states while maintaining backward compatibility for complete failures.

#### Step 6: Update Frontend Generation Trigger Component

**File**: `frontend/src/components/Questions/QuestionGenerationTrigger.tsx`

Replace the entire file content:

```typescript
import { Box, Button, Card, HStack, Text, VStack, Progress } from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { MdAutoAwesome, MdRefresh } from "react-icons/md"

import { type GenerationRequest, QuestionsService, type Quiz } from "@/client"
import { useCustomToast, useErrorHandler } from "@/hooks/common"
import { QUIZ_STATUS } from "@/lib/constants"

interface QuestionGenerationTriggerProps {
  quiz: Quiz
}

interface BatchProgress {
  successfulBatches: number
  totalBatches: number
  successfulQuestions: number
  totalQuestions: number
}

export function QuestionGenerationTrigger({
  quiz,
}: QuestionGenerationTriggerProps) {
  const { showSuccessToast } = useCustomToast()
  const { handleError } = useErrorHandler()
  const queryClient = useQueryClient()

  const triggerGenerationMutation = useMutation({
    mutationFn: async () => {
      if (!quiz.id) {
        throw new Error("Quiz ID is required")
      }

      const generationRequest: GenerationRequest = {
        quiz_id: quiz.id,
        question_type: "multiple_choice",
        target_count: quiz.question_count || 10,
        difficulty: null,
        tags: null,
        custom_instructions: null,
        provider_name: null,
        workflow_name: null,
        template_name: null,
      }

      return await QuestionsService.generateQuestions({
        quizId: quiz.id,
        requestBody: generationRequest,
      })
    },
    onSuccess: () => {
      const isRetry = quiz.status === QUIZ_STATUS.FAILED || quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL
      const message = isRetry ? "Question generation retry started" : "Question generation started"
      showSuccessToast(message)
      queryClient.invalidateQueries({ queryKey: ["quiz", quiz.id] })
    },
    onError: handleError,
  })

  // Calculate batch progress from metadata
  const getBatchProgress = (): BatchProgress => {
    const metadata = quiz.generation_metadata || {}
    const successfulBatches = metadata.successful_batches?.length || 0
    const failedBatches = metadata.failed_batches?.length || 0
    const totalBatches = successfulBatches + failedBatches || Object.keys(quiz.selected_modules || {}).length
    const successfulQuestions = metadata.total_questions_saved || 0
    const totalQuestions = metadata.total_questions_target || quiz.question_count || 0

    return {
      successfulBatches,
      totalBatches,
      successfulQuestions,
      totalQuestions,
    }
  }

  // Don't show if quiz ID is missing
  if (!quiz.id) {
    return null
  }

  // Show for failed states and partial success states
  const shouldShow =
    quiz.status === QUIZ_STATUS.FAILED ||
    quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL ||
    (quiz.status === QUIZ_STATUS.FAILED &&
     (quiz.failure_reason === "llm_generation_error" || quiz.failure_reason === "no_questions_generated"))

  if (!shouldShow) {
    return null
  }

  const batchProgress = getBatchProgress()
  const isPartialSuccess = quiz.status === QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL
  const isCompleteFailure = quiz.status === QUIZ_STATUS.FAILED && batchProgress.successfulQuestions === 0
  const progressPercentage = batchProgress.totalQuestions > 0
    ? (batchProgress.successfulQuestions / batchProgress.totalQuestions) * 100
    : 0

  return (
    <Card.Root>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <Box textAlign="center">
            <Text fontSize="xl" fontWeight="bold" mb={2}>
              {isPartialSuccess && "Partial Question Generation Success"}
              {isCompleteFailure && "Question Generation Failed"}
              {!isPartialSuccess && !isCompleteFailure && "Question Generation Failed"}
            </Text>

            {isPartialSuccess ? (
              <Text color="gray.600" mb={4}>
                Some questions were generated successfully. You can review the existing questions
                or retry generation for the remaining batches.
              </Text>
            ) : (
              <Text color="gray.600" mb={4}>
                The previous question generation attempt failed. Click below to retry generating
                questions for your selected modules.
              </Text>
            )}
          </Box>

          {/* Progress Section */}
          {(isPartialSuccess || batchProgress.successfulQuestions > 0) && (
            <Box
              p={4}
              bg={isPartialSuccess ? "green.50" : "orange.50"}
              borderRadius="md"
              border="1px solid"
              borderColor={isPartialSuccess ? "green.200" : "orange.200"}
            >
              <VStack gap={3}>
                <Text fontSize="sm" fontWeight="medium" color={isPartialSuccess ? "green.700" : "orange.700"}>
                  Generation Progress
                </Text>

                <Progress
                  value={progressPercentage}
                  size="lg"
                  colorScheme={isPartialSuccess ? "green" : "orange"}
                  width="100%"
                />

                <HStack gap={4} fontSize="sm" color={isPartialSuccess ? "green.600" : "orange.600"} wrap="wrap">
                  <Text>
                    Questions: {batchProgress.successfulQuestions}/{batchProgress.totalQuestions}
                  </Text>
                  <Text>
                    Batches: {batchProgress.successfulBatches}/{batchProgress.totalBatches}
                  </Text>
                  <Text>
                    Progress: {progressPercentage.toFixed(1)}%
                  </Text>
                </HStack>

                {isPartialSuccess && batchProgress.totalBatches > batchProgress.successfulBatches && (
                  <Text fontSize="xs" color="gray.600" textAlign="center">
                    {batchProgress.totalBatches - batchProgress.successfulBatches} batch(es) need retry
                  </Text>
                )}
              </VStack>
            </Box>
          )}

          {/* Generation Settings */}
          <Box
            p={4}
            bg="blue.50"
            borderRadius="md"
            border="1px solid"
            borderColor="blue.200"
          >
            <VStack gap={2}>
              <Text fontSize="sm" fontWeight="medium" color="blue.700">
                Generation Settings
              </Text>
              <HStack gap={4} fontSize="sm" color="blue.600" wrap="wrap">
                <Text>Target: {quiz.question_count} questions</Text>
                <Text>Language: {quiz.language === "no" ? "Norwegian" : "English"}</Text>
                <Text>Type: {quiz.question_type || "Multiple Choice"}</Text>
              </HStack>
            </VStack>
          </Box>

          {/* Action Button */}
          <Button
            size="lg"
            colorScheme={isPartialSuccess ? "orange" : "blue"}
            onClick={() => triggerGenerationMutation.mutate()}
            loading={triggerGenerationMutation.isPending}
            width="100%"
            leftIcon={isPartialSuccess ? <MdRefresh /> : <MdAutoAwesome />}
          >
            {isPartialSuccess ? "Retry Failed Batches" : "Retry Question Generation"}
          </Button>

          {isPartialSuccess && (
            <Text fontSize="xs" color="gray.500" textAlign="center">
              Only failed batches will be regenerated. Your existing questions are safe.
            </Text>
          )}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
```

**Purpose**: This enhanced component provides:

1. **Progress Visualization** - Shows batch and question completion progress
2. **Partial Success Support** - Different UI for partial vs complete failures
3. **Clear Messaging** - Explains what will happen during retry
4. **Safety Assurance** - Reassures users that existing questions won't be lost

#### Step 7: Update Frontend Constants

**File**: `frontend/src/lib/constants.ts`

Add the new status to the QUIZ_STATUS constant:

```typescript
export const QUIZ_STATUS = {
  CREATED: "created",
  EXTRACTING_CONTENT: "extracting_content",
  GENERATING_QUESTIONS: "generating_questions",
  READY_FOR_REVIEW: "ready_for_review",
  READY_FOR_REVIEW_PARTIAL: "ready_for_review_partial", // NEW STATUS
  EXPORTING_TO_CANVAS: "exporting_to_canvas",
  PUBLISHED: "published",
  FAILED: "failed",
} as const
```

### 4.3 Data Models & Schemas

#### Batch Tracking Schema

The `generation_metadata` JSONB field in the Quiz model stores:

```json
{
  "generation_attempts": [
    {
      "attempt_number": 1,
      "timestamp": "2024-07-24T12:00:00Z",
      "overall_status": "partial_success",
      "batch_results": {
        "module_123_multiple_choice_15": {
          "module_id": "123",
          "module_name": "Introduction to Machine Learning",
          "question_type": "multiple_choice",
          "target_count": 15,
          "generated_count": 15,
          "status": "success",
          "questions_saved": true
        },
        "module_456_multiple_choice_20": {
          "module_id": "456",
          "module_name": "Advanced Topics",
          "question_type": "multiple_choice",
          "target_count": 20,
          "generated_count": 5,
          "status": "failed",
          "questions_saved": false,
          "error": "Content validation failed for questions"
        }
      }
    }
  ],
  "failed_batches": [
    "module_456_multiple_choice_20"
  ],
  "successful_batches": [
    "module_123_multiple_choice_15"
  ],
  "total_questions_saved": 15,
  "total_questions_target": 35,
  "last_updated": "2024-07-24T12:00:00Z"
}
```

#### Question Data Enhancement

Each saved question includes batch tracking information:

```json
{
  "id": "uuid-here",
  "quiz_id": "quiz-uuid-here",
  "question_type": "multiple_choice",
  "question_data": {
    "question": "What is machine learning?",
    "choices": ["A", "B", "C", "D"],
    "correct_answer": "A",
    "explanation": "...",
    // Batch tracking fields
    "batch_key": "module_123_multiple_choice_15",
    "module_id": "123",
    "module_name": "Introduction to Machine Learning",
    "batch_success_rate": 1.0,
    "generation_timestamp": "2024-07-24T12:00:00Z"
  },
  "is_approved": false,
  "difficulty": null
}
```

#### Validation Rules

1. **Batch Key Format**: `{module_id}_{question_type}_{target_count}`
2. **Success Rate Requirement**: Must be >= 0.99 (99%) to be considered successful
3. **Metadata Consistency**: failed_batches + successful_batches = all attempted batches
4. **Question Count Validation**: total_questions_saved must equal sum of all successful batch question counts

### 4.4 Configuration

No additional configuration parameters are required. The feature uses existing settings:

- `MAX_GENERATION_RETRIES` - Controls retry attempts per batch
- `MAX_JSON_CORRECTIONS` - Controls JSON correction attempts
- `MAX_CONCURRENT_MODULES` - Controls parallel processing

## 5. Testing Strategy

### 5.1 Unit Test Examples

#### Backend Tests

**Test File**: `backend/tests/test_partial_failure_saving.py`

```python
import pytest
from uuid import uuid4
from src.quiz.orchestrator import _execute_generation_workflow
from src.quiz.schemas import QuizStatus
from src.question.types import QuizLanguage, QuestionType

class TestPartialFailureSaving:

    @pytest.mark.asyncio
    async def test_complete_success_all_batches(self):
        """Test that complete success transitions to READY_FOR_REVIEW."""
        quiz_id = uuid4()
        # Mock successful generation for all batches
        status, error, exception = await _execute_generation_workflow(
            quiz_id=quiz_id,
            target_question_count=30,
            _llm_model="gpt-4o",
            _llm_temperature=0.7,
            language=QuizLanguage.ENGLISH,
            question_type=QuestionType.MULTIPLE_CHOICE,
            generation_service=MockGenerationService(success_rate=1.0)
        )

        assert status == "completed"
        assert error is None
        assert exception is None

    @pytest.mark.asyncio
    async def test_partial_success_some_batches(self):
        """Test that partial success transitions to READY_FOR_REVIEW_PARTIAL."""
        quiz_id = uuid4()
        # Mock partial generation success
        status, error, exception = await _execute_generation_workflow(
            quiz_id=quiz_id,
            target_question_count=30,
            _llm_model="gpt-4o",
            _llm_temperature=0.7,
            language=QuizLanguage.ENGLISH,
            question_type=QuestionType.MULTIPLE_CHOICE,
            generation_service=MockGenerationService(
                batch_results={
                    "module_1": 15,  # Success
                    "module_2": 0,   # Failure
                }
            )
        )

        assert status == "partial_success"
        assert error is None
        assert exception is None

    @pytest.mark.asyncio
    async def test_complete_failure_no_batches(self):
        """Test that complete failure transitions to FAILED."""
        quiz_id = uuid4()
        # Mock complete failure
        status, error, exception = await _execute_generation_workflow(
            quiz_id=quiz_id,
            target_question_count=30,
            _llm_model="gpt-4o",
            _llm_temperature=0.7,
            language=QuizLanguage.ENGLISH,
            question_type=QuestionType.MULTIPLE_CHOICE,
            generation_service=MockGenerationService(success_rate=0.0)
        )

        assert status == "failed"
        assert "No questions were generated" in error
        assert exception is None

    def test_batch_key_generation(self):
        """Test batch key format consistency."""
        module_id = "12345"
        question_type = "multiple_choice"
        target_count = 15

        expected_key = f"{module_id}_{question_type}_{target_count}"
        actual_key = f"12345_multiple_choice_15"

        assert expected_key == actual_key

    @pytest.mark.asyncio
    async def test_selective_retry_skips_successful_batches(self):
        """Test that retry only processes failed batches."""
        quiz_id = uuid4()

        # Setup quiz with existing successful batches
        quiz_metadata = {
            "successful_batches": ["module_1_multiple_choice_15"],
            "failed_batches": ["module_2_multiple_choice_10"]
        }

        service = QuestionGenerationService()
        results = await service.generate_questions_for_quiz_with_batch_tracking(
            quiz_id=quiz_id,
            extracted_content={"module_1": "content1", "module_2": "content2"},
            provider_name="openai"
        )

        # Should only attempt module_2 (failed batch)
        assert "module_1" not in results  # Skipped (already successful)
        assert "module_2" in results       # Attempted (previously failed)
```

#### Frontend Tests

**Test File**: `frontend/src/components/Questions/__tests__/QuestionGenerationTrigger.test.tsx`

```typescript
import { render, screen } from '@testing-library/react'
import { QuestionGenerationTrigger } from '../QuestionGenerationTrigger'
import { QUIZ_STATUS } from '@/lib/constants'

describe('QuestionGenerationTrigger', () => {
  const mockQuiz = {
    id: 'test-quiz-id',
    question_count: 30,
    language: 'en',
    question_type: 'multiple_choice',
    selected_modules: {
      '123': { name: 'Module 1', question_count: 15 },
      '456': { name: 'Module 2', question_count: 15 }
    }
  }

  it('shows partial success UI for READY_FOR_REVIEW_PARTIAL status', () => {
    const partialQuiz = {
      ...mockQuiz,
      status: QUIZ_STATUS.READY_FOR_REVIEW_PARTIAL,
      generation_metadata: {
        successful_batches: ['module_123_multiple_choice_15'],
        failed_batches: ['module_456_multiple_choice_15'],
        total_questions_saved: 15,
        total_questions_target: 30
      }
    }

    render(<QuestionGenerationTrigger quiz={partialQuiz} />)

    expect(screen.getByText('Partial Question Generation Success')).toBeInTheDocument()
    expect(screen.getByText('Questions: 15/30')).toBeInTheDocument()
    expect(screen.getByText('Batches: 1/2')).toBeInTheDocument()
    expect(screen.getByText('Progress: 50.0%')).toBeInTheDocument()
    expect(screen.getByText('Retry Failed Batches')).toBeInTheDocument()
  })

  it('shows complete failure UI for FAILED status with no progress', () => {
    const failedQuiz = {
      ...mockQuiz,
      status: QUIZ_STATUS.FAILED,
      failure_reason: 'llm_generation_error',
      generation_metadata: {
        successful_batches: [],
        failed_batches: ['module_123_multiple_choice_15', 'module_456_multiple_choice_15'],
        total_questions_saved: 0,
        total_questions_target: 30
      }
    }

    render(<QuestionGenerationTrigger quiz={failedQuiz} />)

    expect(screen.getByText('Question Generation Failed')).toBeInTheDocument()
    expect(screen.getByText('Retry Question Generation')).toBeInTheDocument()
    expect(screen.queryByText('Progress:')).not.toBeInTheDocument()
  })

  it('does not render for non-retry states', () => {
    const readyQuiz = {
      ...mockQuiz,
      status: QUIZ_STATUS.READY_FOR_REVIEW
    }

    const { container } = render(<QuestionGenerationTrigger quiz={readyQuiz} />)
    expect(container.firstChild).toBeNull()
  })
})
```

### 5.2 Integration Test Scenarios

#### Scenario 1: Partial Success Flow

**Input**: Quiz with 3 modules, 2 succeed, 1 fails
**Expected Behavior**:
1. Questions from successful modules are saved
2. Quiz status becomes READY_FOR_REVIEW_PARTIAL
3. Failed batch is tracked in metadata
4. User can review successful questions
5. Retry only attempts failed batch

#### Scenario 2: Retry from Partial Success

**Input**: Quiz in READY_FOR_REVIEW_PARTIAL with 1 failed batch
**Expected Behavior**:
1. Existing successful questions remain untouched
2. Only failed batch is regenerated
3. If retry succeeds: status becomes READY_FOR_REVIEW
4. If retry fails again: status remains READY_FOR_REVIEW_PARTIAL

#### Scenario 3: Complete Success After Retry

**Input**: Partial success quiz where retry completes all batches
**Expected Behavior**:
1. All questions now available for review
2. Status transitions to READY_FOR_REVIEW
3. Metadata shows all batches successful
4. No more retry options shown

### 5.3 Manual Testing Steps

1. **Setup Test Quiz**
   - Create quiz with 3 modules
   - Set different question counts per module
   - Ensure content extraction completes

2. **Trigger Partial Failure**
   - Mock LLM provider to fail validation for 1 module
   - Verify partial success status and saved questions
   - Check metadata accuracy

3. **Test Retry Functionality**
   - Click retry button from partial state
   - Verify only failed batches are regenerated
   - Confirm existing questions preserved

4. **Test Complete Success Path**
   - Ensure successful retry transitions to full success
   - Verify all questions accessible
   - Confirm no retry UI shown

## 6. Deployment Instructions

### 6.1 Pre-Deployment Checklist

- [ ] All backend tests pass
- [ ] Frontend builds without errors
- [ ] Database migrations not required (uses existing schema)
- [ ] Staging environment testing complete

### 6.2 Deployment Steps

1. **Deploy Backend Changes**
   ```bash
   # From project root
   docker compose build backend
   docker compose up -d backend
   ```

2. **Deploy Frontend Changes**
   ```bash
   # From project root
   docker compose build frontend
   docker compose up -d frontend
   ```

3. **Verify Deployment**
   ```bash
   # Check backend health
   curl http://localhost:8000/health

   # Check frontend accessibility
   curl http://localhost:5173
   ```

### 6.3 Environment-Specific Configuration

No environment-specific configuration changes required. Feature uses existing environment variables.

### 6.4 Rollback Procedure

If issues arise, rollback by reverting the following files:
- `backend/src/quiz/schemas.py`
- `backend/src/quiz/orchestrator.py`
- `backend/src/quiz/router.py`
- `backend/src/question/services/generation_service.py`
- `backend/src/question/workflows/module_batch_workflow.py`
- `frontend/src/components/Questions/QuestionGenerationTrigger.tsx`
- `frontend/src/lib/constants.ts`

The feature is backward compatible, so existing data remains intact during rollback.

## 7. Monitoring & Maintenance

### 7.1 Key Metrics to Monitor

#### Backend Metrics

- **Batch Success Rate**: `successful_batches / total_batches`
- **Partial Success Frequency**: Count of `READY_FOR_REVIEW_PARTIAL` transitions
- **Retry Success Rate**: Success rate of retry operations
- **Question Preservation**: Verify no questions lost during retries

#### Log Entries to Watch

```
INFO: generation_workflow_partial_success - Indicates partial success
INFO: batch_tracking_generation_completed - Shows batch processing results
WARNING: module_batch_not_saving_partial_success - Indicates batch failed to meet 100% requirement
INFO: skipping_successful_batches - Shows selective retry working correctly
```

#### Database Queries for Monitoring

```sql
-- Count quizzes by status
SELECT status, COUNT(*) FROM quiz GROUP BY status;

-- Average batch success rate
SELECT
  AVG((generation_metadata->'total_questions_saved')::int::float /
      (generation_metadata->'total_questions_target')::int::float) as avg_success_rate
FROM quiz
WHERE generation_metadata IS NOT NULL;

-- Retry frequency
SELECT
  COUNT(*) as total_retries
FROM quiz
WHERE jsonb_array_length(generation_metadata->'generation_attempts') > 1;
```

### 7.2 Common Issues and Troubleshooting

#### Issue: Batch Not Saving Despite Apparent Success

**Symptom**: Questions generated but not saved to database
**Cause**: Batch didn't achieve 100% validation success
**Solution**: Check logs for `module_batch_not_saving_partial_success` entries

#### Issue: Retry Regenerating Successful Batches

**Symptom**: Already successful questions being regenerated
**Cause**: Metadata not properly tracking successful batches
**Solution**: Verify `successful_batches` array in quiz metadata

#### Issue: Status Stuck in READY_FOR_REVIEW_PARTIAL

**Symptom**: Quiz remains in partial state after retry
**Cause**: Retry didn't complete all failed batches
**Solution**: Check `failed_batches` array for remaining failures

### 7.3 Performance Considerations

- **Memory Usage**: Batch metadata adds ~1-5KB per quiz
- **Query Performance**: JSONB queries on metadata may need indexing for large datasets
- **Concurrency**: Selective retry reduces LLM API calls by 50-80% on average

## 8. Security Considerations

### 8.1 Authentication/Authorization

- **Existing Security**: Uses existing JWT authentication
- **Ownership Validation**: Quiz ownership validated before retry operations
- **No New Endpoints**: Extends existing `/generate-questions` endpoint

### 8.2 Data Privacy

- **Question Content**: Batch metadata doesn't expose question content
- **Module Information**: Module names stored in metadata (already in quiz)
- **Error Messages**: Error details in metadata may contain LLM responses

### 8.3 Security Best Practices

1. **Input Validation**: All batch metadata validated before storage
2. **SQL Injection Prevention**: Uses parameterized queries for JSONB operations
3. **Rate Limiting**: Existing rate limiting applies to retry operations
4. **Audit Logging**: All generation attempts logged with user context

## 9. Future Considerations

### 9.1 Known Limitations

1. **Question Type Support**: Currently optimized for multiple choice questions
2. **Batch Size Limits**: Large batches may impact performance
3. **Metadata Size**: Very active quizzes may accumulate large metadata

### 9.2 Potential Improvements

#### Multi-Question Type Support

Future enhancement to support different question types per module:

```json
{
  "batch_key": "module_123_multiple_choice_15",
  "question_types": ["multiple_choice", "fill_in_blank"],
  "type_distribution": {
    "multiple_choice": 10,
    "fill_in_blank": 5
  }
}
```

#### Batch Optimization

Intelligent batching based on content complexity:

```json
{
  "batch_optimization": {
    "content_complexity_score": 0.75,
    "recommended_batch_size": 12,
    "estimated_success_rate": 0.85
  }
}
```

#### Advanced Retry Strategies

- **Exponential Backoff**: Delay retries based on failure count
- **Content Adjustment**: Modify content based on failure patterns
- **Provider Switching**: Try different LLM providers for failed batches

### 9.3 Scalability Considerations

#### Database Scaling

For high-volume deployments:

1. **Metadata Indexing**: Add GIN indexes on generation_metadata JSONB fields
2. **Archival Strategy**: Archive old generation attempts after 30 days
3. **Read Replicas**: Use read replicas for metadata analysis queries

#### Performance Optimization

1. **Batch Size Tuning**: Optimize batch sizes based on success rate data
2. **Caching**: Cache successful batch results for faster retry operations
3. **Background Processing**: Move metadata updates to background workers

---

**Document Version**: 1.0
**Last Updated**: July 24, 2025
**Author**: Development Team
**Review Status**: Ready for Implementation
