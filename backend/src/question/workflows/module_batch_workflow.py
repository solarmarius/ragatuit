"""Module batch workflow for parallel question generation."""

import asyncio
import json
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.config import get_logger, settings
from src.database import get_async_session

from ..providers import BaseLLMProvider, LLMMessage
from ..templates.manager import TemplateManager, get_template_manager
from ..types import (
    GenerationParameters,
    Question,
    QuestionDifficulty,
    QuestionType,
    QuizLanguage,
)

logger = get_logger("module_batch_workflow")


class ModuleBatchState(BaseModel):
    """State for module batch generation workflow."""

    # Input parameters
    quiz_id: UUID
    module_id: str
    module_name: str
    module_content: str
    target_question_count: int
    language: QuizLanguage = QuizLanguage.ENGLISH
    question_type: QuestionType  # Now passed per batch, not at init
    difficulty: QuestionDifficulty | None = None  # Difficulty level for this batch
    tone: str | None = None

    # Provider configuration
    llm_provider: BaseLLMProvider
    template_manager: TemplateManager

    # Workflow state
    generated_questions: list[Question] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = Field(default_factory=lambda: settings.MAX_GENERATION_RETRIES)

    # JSON correction state
    parsing_error: bool = False
    correction_attempts: int = 0
    max_corrections: int = Field(default_factory=lambda: settings.MAX_JSON_CORRECTIONS)

    # Validation error state
    validation_error: bool = False
    validation_error_details: list[str] = Field(default_factory=list)
    validation_correction_attempts: int = 0
    max_validation_corrections: int = Field(
        default_factory=lambda: settings.MAX_JSON_CORRECTIONS
    )

    # Smart retry state for failed question tracking
    failed_questions_data: list[dict[str, Any]] = Field(default_factory=list)
    failed_questions_errors: list[str] = Field(default_factory=list)
    successful_questions_preserved: list[Question] = Field(default_factory=list)

    # Current LLM interaction
    system_prompt: str = ""
    user_prompt: str = ""
    raw_response: str = ""

    # Error handling
    error_message: str | None = None

    # Metadata
    workflow_metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ModuleBatchWorkflow:
    """
    Workflow for generating multiple questions per module in batch.

    This workflow implements a self-healing JSON correction mechanism:
    1. If JSON parsing fails, it triggers a correction path
    2. The correction prompt includes the error and malformed JSON
    3. The LLM is asked to fix and return only valid JSON
    4. This can happen up to max_corrections times before failing

    This makes the system robust against common LLM formatting errors.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
        tone: str | None = None,
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language
        self.tone = tone
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build the module batch workflow graph."""
        workflow = StateGraph(ModuleBatchState)

        # Add nodes
        workflow.add_node("prepare_prompt", self.prepare_prompt)
        workflow.add_node("generate_batch", self.generate_batch)
        workflow.add_node("validate_batch", self.validate_batch)
        workflow.add_node("check_completion", self.check_completion)
        workflow.add_node("prepare_correction", self.prepare_correction)
        workflow.add_node(
            "prepare_validation_correction", self.prepare_validation_correction
        )
        workflow.add_node("retry_generation", self.retry_generation)
        workflow.add_node("save_questions", self.save_questions)

        # Add edges
        workflow.add_edge(START, "prepare_prompt")
        workflow.add_edge("prepare_prompt", "generate_batch")
        workflow.add_edge("generate_batch", "validate_batch")

        # Conditional edge from validate_batch
        workflow.add_conditional_edges(
            "validate_batch",
            self.check_error_type,
            {
                "needs_json_correction": "prepare_correction",
                "needs_validation_correction": "prepare_validation_correction",
                "continue": "check_completion",
            },
        )

        workflow.add_edge("prepare_correction", "generate_batch")
        workflow.add_edge("prepare_validation_correction", "generate_batch")

        # Conditional edges from check_completion
        workflow.add_conditional_edges(
            "check_completion",
            self.should_retry,
            {
                "retry": "retry_generation",
                "complete": "save_questions",
                "failed": END,
            },
        )

        workflow.add_edge("retry_generation", "prepare_prompt")
        workflow.add_edge("save_questions", END)

        return workflow.compile()

    async def prepare_prompt(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare the prompt for batch generation."""
        try:
            # Calculate remaining questions needed (accounting for preserved questions)
            remaining_questions = (
                state.target_question_count
                - len(state.generated_questions)
                - len(state.successful_questions_preserved)
            )

            # Create generation parameters
            generation_parameters = GenerationParameters(
                target_count=remaining_questions,
                difficulty=state.difficulty,
                language=self.language,
            )

            # Debug: Log content being passed to template
            logger.debug(
                "module_batch_template_variables",
                module_id=state.module_id,
                module_content_length=len(state.module_content),
                module_content_preview=state.module_content[:200]
                if state.module_content
                else "EMPTY_CONTENT",
                module_name=state.module_name,
                question_count=remaining_questions,
                question_type=state.question_type.value,
            )

            # Create messages using template
            # Template will be automatically selected based on question type and language
            messages = await self.template_manager.create_messages(
                state.question_type,
                state.module_content,
                generation_parameters,
                template_name=None,  # Let template manager select based on question type
                language=self.language,
                extra_variables={
                    "module_name": state.module_name,
                    "question_count": remaining_questions,
                    "tone": state.tone or self.tone,
                },
            )

            # Store system and user prompts separately
            state.system_prompt = messages[0].content
            state.user_prompt = messages[1].content

            logger.info(
                "module_batch_prompt_prepared",
                module_id=state.module_id,
                target_questions=state.target_question_count
                - len(state.generated_questions),
                language=self.language.value,
            )

        except Exception as e:
            logger.error(
                "module_batch_prompt_preparation_failed",
                module_id=state.module_id,
                error=str(e),
                exc_info=True,
            )
            state.error_message = f"Failed to prepare prompt: {str(e)}"

        return state

    async def generate_batch(self, state: ModuleBatchState) -> ModuleBatchState:
        """Generate multiple questions in a single LLM call."""
        try:
            # Create messages for LLM
            messages = [
                LLMMessage(
                    role="system",
                    content=state.system_prompt,
                ),
                LLMMessage(role="user", content=state.user_prompt),
            ]

            # Generate questions using LLM provider
            response = await self.llm_provider.generate_with_retry(messages)

            state.raw_response = response.content

            # Update metadata
            state.workflow_metadata.update(
                {
                    "last_generation_time": response.response_time,
                    "total_tokens_used": state.workflow_metadata.get(
                        "total_tokens_used", 0
                    )
                    + (response.total_tokens or 0),
                    "last_model_used": response.model,
                }
            )

            logger.info(
                "module_batch_generation_completed",
                module_id=state.module_id,
                response_length=len(state.raw_response),
                response_time=response.response_time,
            )

        except Exception as e:
            logger.error(
                "module_batch_generation_failed",
                module_id=state.module_id,
                error=str(e),
                exc_info=True,
            )
            state.error_message = f"Batch generation failed: {str(e)}"

        return state

    async def validate_batch(self, state: ModuleBatchState) -> ModuleBatchState:
        """Validate and parse the generated questions with smart retry support."""
        if not state.raw_response or state.error_message:
            return state

        try:
            # Parse the response to extract individual questions
            questions_data = self._parse_batch_response(state.raw_response)

            # Track validation state for smart retry
            questions_before_validation = len(state.generated_questions)
            failed_questions = []
            failed_errors = []

            # Validate and create question objects
            for q_data in questions_data:
                try:
                    # Remove difficulty from question data if LLM provided it (we use batch difficulty instead)
                    q_data.pop("difficulty", None)

                    # Use dynamic validation based on question type
                    from ..types.registry import get_question_type_registry

                    registry = get_question_type_registry()
                    question_type_impl = registry.get_question_type(state.question_type)
                    validated_data = question_type_impl.validate_data(q_data)

                    # Create question object with validated data
                    # Always use batch difficulty (manually set, not from LLM)
                    question = Question(
                        quiz_id=state.quiz_id,
                        question_type=state.question_type,
                        question_data=validated_data.model_dump(),
                        difficulty=state.difficulty,
                        is_approved=False,
                    )
                    state.generated_questions.append(question)

                except Exception as e:
                    # Smart retry: Store failed question data and error for targeted retry
                    error_detail = f"Question validation failed: {str(e)}"
                    failed_questions.append(q_data)
                    failed_errors.append(error_detail)

                    logger.warning(
                        "module_batch_question_validation_failed",
                        module_id=state.module_id,
                        question_data=q_data,
                        error=str(e),
                    )
                    continue

            # Smart retry logic: Handle mixed success/failure scenarios
            if failed_questions:
                # Store failed question data for targeted retry
                state.failed_questions_data = failed_questions
                state.failed_questions_errors = failed_errors
                state.validation_error = True

                # Preserve newly successful questions for combination later
                newly_successful = state.generated_questions[
                    questions_before_validation:
                ]
                state.successful_questions_preserved.extend(newly_successful)

                # Remove newly successful questions from generated_questions
                # This ensures retry logic counts correctly
                state.generated_questions = state.generated_questions[
                    :questions_before_validation
                ]

                logger.warning(
                    "module_batch_validation_errors_detected_smart_retry",
                    module_id=state.module_id,
                    failed_questions=len(failed_questions),
                    successful_questions=len(newly_successful),
                    total_questions_attempted=len(questions_data),
                )

            logger.info(
                "module_batch_validation_completed",
                module_id=state.module_id,
                questions_validated=len(state.generated_questions),
                questions_parsed=len(questions_data),
                questions_preserved=len(state.successful_questions_preserved),
            )

        except ValueError as e:
            # JSON parsing error - set error for retry with correction
            logger.error(
                "module_batch_json_parsing_failed",
                module_id=state.module_id,
                error=str(e),
                response_preview=state.raw_response[:500]
                if state.raw_response
                else "empty",
            )
            state.error_message = f"JSON_PARSE_ERROR: {str(e)}"
            state.parsing_error = True

        except Exception as e:
            logger.error(
                "module_batch_validation_failed",
                module_id=state.module_id,
                error=str(e),
                exc_info=True,
            )
            state.error_message = f"Batch validation failed: {str(e)}"

        return state

    def check_error_type(self, state: ModuleBatchState) -> str:
        """Check what type of error we have and determine correction path."""
        # Check for JSON parsing errors first
        if state.parsing_error and state.correction_attempts < state.max_corrections:
            return "needs_json_correction"

        # Check for validation errors
        if (
            state.validation_error
            and state.validation_correction_attempts < state.max_validation_corrections
        ):
            return "needs_validation_correction"

        return "continue"

    async def check_completion(self, state: ModuleBatchState) -> ModuleBatchState:
        """Check if we have generated enough questions."""
        # This is a pass-through node that just passes the state to should_retry
        return state

    async def prepare_correction(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare a corrective prompt for JSON parsing errors."""
        if not state.parsing_error or not state.raw_response:
            return state

        try:
            error_details = (
                state.error_message.replace("JSON_PARSE_ERROR: ", "")
                if state.error_message
                else ""
            )

            # Create a focused correction prompt
            correction_prompt = (
                "Your previous response resulted in a JSON parsing error. "
                "Please fix the following invalid JSON and return ONLY the corrected, valid JSON array.\\n\\n"
                f"Error: {error_details}\\n\\n"
                f"Invalid JSON (first 1000 chars):\\n{state.raw_response[:1000]}\\n\\n"
                "Requirements:\\n"
                "1. Return ONLY a valid JSON array\\n"
                "2. No markdown code blocks (```json or ```)\\n"
                "3. No explanatory text before or after the JSON\\n"
                "4. Ensure all quotes are properly escaped\\n"
                "5. Ensure the array contains the requested number of question objects\\n\\n"
                "Please provide the corrected JSON array:"
            )

            state.user_prompt = correction_prompt

            # Increment correction attempts
            state.correction_attempts += 1

            # Reset error state for retry
            state.parsing_error = False
            state.error_message = None
            state.raw_response = ""

            logger.info(
                "module_batch_correction_prepared",
                module_id=state.module_id,
                correction_attempt=state.correction_attempts,
                max_corrections=state.max_corrections,
            )

        except Exception as e:
            logger.error(
                "module_batch_correction_preparation_failed",
                module_id=state.module_id,
                error=str(e),
                exc_info=True,
            )
            state.error_message = f"Failed to prepare correction: {str(e)}"

        return state

    async def prepare_validation_correction(
        self, state: ModuleBatchState
    ) -> ModuleBatchState:
        """Prepare a corrective prompt to fix specific failed questions."""
        if not state.validation_error or not state.failed_questions_data:
            return state

        try:
            # Build detailed context for each failed question
            failed_questions_context = []
            for i, (q_data, error) in enumerate(
                zip(
                    state.failed_questions_data,
                    state.failed_questions_errors,
                    strict=False,
                )
            ):
                context = f"FAILED QUESTION {i+1}:"
                context += f"\nOriginal Data: {json.dumps(q_data, indent=2)}"
                context += f"\nValidation Error: {error}"
                failed_questions_context.append(context)

            questions_context = "\n\n".join(failed_questions_context)

            # Create targeted correction prompt
            correction_prompt = (
                f"The following {len(state.failed_questions_data)} questions failed validation. "
                f"Please fix ONLY these specific questions and return them in the same JSON array format.\n\n"
                f"{questions_context}\n\n"
                f"Requirements:\n"
                f"1. Return ONLY a JSON array containing the {len(state.failed_questions_data)} corrected questions\n"
                f"2. Fix the validation errors mentioned above\n"
                f"3. Preserve the original question intent and content where possible\n"
                f"4. Each question must follow the correct format for {state.question_type.value} questions\n"
                f"5. No markdown code blocks or explanatory text\n"
                f"6. Do not generate new questions - fix the existing ones provided\n\n"
                f"Please provide the corrected questions as a JSON array:"
            )

            state.user_prompt = correction_prompt
            # Clear system prompt to avoid conflicting instructions
            state.system_prompt = ""

            # Increment validation correction attempts
            state.validation_correction_attempts += 1

            # Reset error state for retry
            state.validation_error = False
            state.validation_error_details = []
            state.error_message = None
            state.raw_response = ""

            logger.info(
                "module_batch_validation_correction_prepared_smart_retry",
                module_id=state.module_id,
                failed_questions_count=len(state.failed_questions_data),
                successful_questions_preserved=len(
                    state.successful_questions_preserved
                ),
                correction_attempt=state.validation_correction_attempts,
                max_corrections=state.max_validation_corrections,
            )

        except Exception as e:
            logger.error(
                "module_batch_validation_correction_preparation_failed",
                module_id=state.module_id,
                error=str(e),
                exc_info=True,
            )
            state.error_message = f"Failed to prepare validation correction: {str(e)}"

        return state

    def should_retry(self, state: ModuleBatchState) -> str:
        """Determine if we should retry generation with smart question counting."""
        if state.error_message:
            return "failed"

        # Calculate total questions: generated + preserved successful questions
        total_questions = len(state.generated_questions) + len(
            state.successful_questions_preserved
        )
        questions_needed = state.target_question_count - total_questions

        if questions_needed <= 0:
            return "complete"

        if state.retry_count < state.max_retries:
            logger.info(
                "module_batch_retry_needed",
                module_id=state.module_id,
                questions_needed=questions_needed,
                questions_generated=len(state.generated_questions),
                questions_preserved=len(state.successful_questions_preserved),
                total_questions=total_questions,
                target_questions=state.target_question_count,
                retry_count=state.retry_count + 1,
                max_retries=state.max_retries,
            )
            return "retry"

        logger.warning(
            "module_batch_max_retries_reached",
            module_id=state.module_id,
            questions_generated=total_questions,
            target_questions=state.target_question_count,
            final_preserved_count=len(state.successful_questions_preserved),
            final_generated_count=len(state.generated_questions),
        )
        return "complete"

    async def retry_generation(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare for retry with smart state management."""
        state.retry_count += 1
        state.error_message = None
        state.raw_response = ""

        # Clear failed question data for fresh retry
        # Note: We keep successful_questions_preserved across retries
        state.failed_questions_data = []
        state.failed_questions_errors = []

        # Add exponential backoff
        await asyncio.sleep(1 * state.retry_count)

        logger.info(
            "module_batch_retry_generation_prepared",
            module_id=state.module_id,
            retry_count=state.retry_count,
            preserved_questions=len(state.successful_questions_preserved),
        )

        return state

    async def save_questions(self, state: ModuleBatchState) -> ModuleBatchState:
        """Save questions with proper truncation for over-generation."""
        # Combine preserved successful questions with newly generated ones
        all_questions = state.successful_questions_preserved + state.generated_questions

        # Get initial count before truncation
        initial_count = len(all_questions)

        # Truncate if we have too many questions
        if len(all_questions) > state.target_question_count:
            excess_count = len(all_questions) - state.target_question_count
            logger.info(
                "module_batch_truncating_excess_questions",
                module_id=state.module_id,
                initial_questions=initial_count,
                target_questions=state.target_question_count,
                excess_questions=excess_count,
            )

            # Truncate to exact target count (keep first N questions)
            # We use first-N strategy for deterministic behavior and simplicity.
            # Alternative approaches (random selection, quality-based) would require
            # additional complexity and metadata that isn't currently available.
            all_questions = all_questions[: state.target_question_count]

        # Calculate success rate after truncation
        total_questions = len(all_questions)
        success_rate = (
            total_questions / state.target_question_count
            if state.target_question_count > 0
            else 0
        )

        # Only save if we have sufficient questions (allow for tiny floating point errors)
        if success_rate < 0.99:
            logger.warning(
                "module_batch_not_saving_partial_success",
                module_id=state.module_id,
                questions_generated=total_questions,
                target_questions=state.target_question_count,
                success_rate=f"{success_rate*100:.1f}%",
                reason="Batch did not achieve minimum success rate",
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
                # Add all questions to session
                for question in all_questions:
                    session.add(question)

                # Commit all questions
                await session.commit()

                logger.info(
                    "module_batch_questions_saved",
                    module_id=state.module_id,
                    questions_saved=len(all_questions),
                    preserved_questions=len(state.successful_questions_preserved),
                    newly_generated=len(state.generated_questions),
                    target_questions=state.target_question_count,
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

    def _parse_batch_response(self, response: str) -> list[dict[str, Any]]:
        """
        Parse the LLM response to extract multiple questions.

        IMPORTANT: This method ONLY accepts valid JSON arrays.
        No fallbacks to text parsing to ensure reliability.
        """
        try:
            # Clean the response - remove any markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```

            # Parse as JSON - this is the ONLY accepted format
            parsed = json.loads(cleaned_response)

            # Validate it's an array
            if not isinstance(parsed, list):
                raise ValueError("Response must be a JSON array")

            return parsed

        except json.JSONDecodeError as e:
            logger.error(
                "module_batch_json_decode_error",
                error=str(e),
                response_preview=response[:500] if response else "empty",
            )
            raise ValueError(f"LLM response was not valid JSON: {str(e)}")
        except Exception as e:
            logger.error(
                "module_batch_parse_error",
                error=str(e),
                exc_info=True,
            )
            raise

    async def process_module(
        self,
        quiz_id: UUID,
        module_id: str,
        module_name: str,
        module_content: str,
        question_count: int,
        question_type: QuestionType,  # Now passed as parameter
        difficulty: QuestionDifficulty | None = None,  # Difficulty for this batch
    ) -> list[Question]:
        """Process a single module to generate questions."""
        initial_state = ModuleBatchState(
            quiz_id=quiz_id,
            module_id=module_id,
            module_name=module_name,
            module_content=module_content,
            target_question_count=question_count,
            language=self.language,
            question_type=question_type,  # Set from parameter
            difficulty=difficulty,  # Difficulty level for this batch
            tone=self.tone,
            llm_provider=self.llm_provider,
            template_manager=self.template_manager,
        )

        logger.info(
            "module_batch_processing_started",
            module_id=module_id,
            target_questions=question_count,
            content_length=len(module_content),
            content_preview=module_content[:200] if module_content else "EMPTY_CONTENT",
        )

        try:
            final_state_dict = await self.graph.ainvoke(initial_state)

            # Convert dict result back to ModuleBatchState for type safety
            final_state = ModuleBatchState(**final_state_dict)

            # Calculate total questions (preserved + newly generated)
            total_questions = len(final_state.successful_questions_preserved) + len(
                final_state.generated_questions
            )

            logger.info(
                "module_batch_processing_completed",
                module_id=module_id,
                questions_generated=total_questions,
                questions_preserved=len(final_state.successful_questions_preserved),
                questions_newly_generated=len(final_state.generated_questions),
                target_questions=question_count,
                success=final_state.error_message is None,
            )

            # Return all questions (preserved + newly generated)
            all_questions = (
                final_state.successful_questions_preserved
                + final_state.generated_questions
            )
            return list(all_questions)

        except Exception as e:
            logger.error(
                "module_batch_processing_failed",
                module_id=module_id,
                error=str(e),
                exc_info=True,
            )
            return []


class ParallelModuleProcessor:
    """Handles parallel processing of multiple modules."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
        tone: str | None = None,
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language
        self.tone = tone

    async def process_all_modules_with_batches(
        self,
        quiz_id: UUID,
        modules_data: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, list[Question]], dict[str, list[str]]]:
        """
        Process all modules with their batches in parallel.

        Args:
            quiz_id: The quiz identifier
            modules_data: Dictionary with module data including batches:
                {
                    "module_id": {
                        "name": "Module Name",
                        "content": "...",
                        "batches": [
                            {"question_type": QuestionType, "count": int, "batch_key": str},
                            ...
                        ]
                    }
                }

        Returns:
            Dictionary mapping module IDs to lists of generated questions
        """
        # Create tasks for all batches across all modules
        tasks = []
        batch_info_map = {}  # Track which task belongs to which module/batch

        for module_id, module_info in modules_data.items():
            module_name = module_info["name"]
            module_content = module_info["content"]

            for batch in module_info["batches"]:
                question_type = batch["question_type"]
                count = batch["count"]
                difficulty_str = batch.get(
                    "difficulty", "medium"
                )  # Default to medium for backward compatibility
                # Convert to enum here, like how language is handled
                try:
                    difficulty = QuestionDifficulty(difficulty_str)
                except ValueError:
                    difficulty = QuestionDifficulty.MEDIUM
                batch_key = batch["batch_key"]

                # Create workflow for this specific batch
                workflow = ModuleBatchWorkflow(
                    llm_provider=self.llm_provider,
                    template_manager=self.template_manager,
                    language=self.language,
                    tone=self.tone,
                )

                # Create task for this batch
                task = asyncio.create_task(
                    self._process_single_batch(
                        workflow,
                        module_id,
                        module_name,
                        module_content,
                        quiz_id,
                        count,
                        question_type,
                        difficulty,
                        batch_key,
                    )
                )

                tasks.append(task)
                batch_info_map[id(task)] = {
                    "module_id": module_id,
                    "batch_key": batch_key,
                    "question_type": question_type,
                }

        # Execute all batch tasks in parallel
        logger.info(
            "parallel_batch_processing_started",
            quiz_id=str(quiz_id),
            total_batches=len(tasks),
            modules_count=len(modules_data),
        )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and organize by module
        final_results: dict[str, list[Question]] = {}
        successful_batches = []
        failed_batches = []

        for task_idx, result in enumerate(results):
            task = tasks[task_idx]
            batch_info = batch_info_map[id(task)]
            module_id = batch_info["module_id"]
            batch_key = batch_info["batch_key"]

            if isinstance(result, BaseException):
                logger.error(
                    "parallel_batch_processing_batch_failed",
                    quiz_id=str(quiz_id),
                    module_id=module_id,
                    batch_key=batch_key,
                    error=str(result),
                )
                failed_batches.append(batch_key)
            else:
                questions, metadata = result

                # Initialize module results if needed
                if module_id not in final_results:
                    final_results[module_id] = []

                # Add questions from this batch
                final_results[module_id].extend(questions)

                # Check if batch was successful based on metadata
                batch_success = metadata.get("success", False)

                if batch_success:
                    successful_batches.append(batch_key)
                    logger.info(
                        "parallel_batch_processing_batch_completed",
                        quiz_id=str(quiz_id),
                        module_id=module_id,
                        batch_key=batch_key,
                        questions_generated=len(questions),
                    )
                else:
                    failed_batches.append(batch_key)
                    logger.warning(
                        "parallel_batch_processing_batch_failed_partial",
                        quiz_id=str(quiz_id),
                        module_id=module_id,
                        batch_key=batch_key,
                        questions_generated=len(questions),
                        target_count=metadata.get("target_count", 0),
                        reason="Batch did not meet target question count",
                    )

        # Note: Metadata update moved to orchestrator's transaction context
        # to ensure atomicity with quiz status updates

        logger.info(
            "parallel_batch_processing_completed",
            quiz_id=str(quiz_id),
            successful_batches=len(successful_batches),
            failed_batches=len(failed_batches),
            total_questions=sum(len(q) for q in final_results.values()),
        )

        # Return results with batch tracking information
        return final_results, {
            "successful_batches": successful_batches,
            "failed_batches": failed_batches,
        }

    async def _process_single_batch(
        self,
        workflow: ModuleBatchWorkflow,
        module_id: str,
        module_name: str,
        module_content: str,
        quiz_id: UUID,
        target_count: int,
        question_type: QuestionType,
        difficulty: QuestionDifficulty,
        batch_key: str,
    ) -> tuple[list[Question], dict[str, Any]]:
        """
        Process a single batch for a module.

        Returns:
            Tuple of (questions, metadata)
        """
        try:
            logger.info(
                "processing_single_batch",
                quiz_id=str(quiz_id),
                module_id=module_id,
                batch_key=batch_key,
                question_type=question_type.value,
                target_count=target_count,
            )

            questions = await workflow.process_module(
                module_id=module_id,
                module_name=module_name,
                module_content=module_content,
                quiz_id=quiz_id,
                question_count=target_count,
                question_type=question_type,
                difficulty=difficulty,
            )

            # Determine if batch was successful based on question count vs target
            success = len(questions) >= target_count

            metadata = {
                "batch_key": batch_key,
                "questions_generated": len(questions),
                "target_count": target_count,
                "question_type": question_type.value,
                "success": success,
            }

            return questions, metadata

        except Exception as e:
            logger.error(
                "batch_processing_error",
                quiz_id=str(quiz_id),
                module_id=module_id,
                batch_key=batch_key,
                error=str(e),
                exc_info=True,
            )
            raise
