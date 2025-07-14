"""Module batch workflow for parallel question generation."""

import asyncio
import json
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.config import get_logger
from src.database import get_async_session

from ..providers import BaseLLMProvider, LLMMessage
from ..templates.manager import TemplateManager, get_template_manager
from ..types import GenerationParameters, Question, QuestionType, QuizLanguage

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

    # Provider configuration
    llm_provider: BaseLLMProvider
    template_manager: TemplateManager

    # Workflow state
    generated_questions: list[Question] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    # JSON correction state
    parsing_error: bool = False
    correction_attempts: int = 0
    max_corrections: int = 2

    # Current LLM interaction
    current_prompt: str = ""
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
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language
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
        workflow.add_node("retry_generation", self.retry_generation)
        workflow.add_node("save_questions", self.save_questions)

        # Add edges
        workflow.add_edge(START, "prepare_prompt")
        workflow.add_edge("prepare_prompt", "generate_batch")
        workflow.add_edge("generate_batch", "validate_batch")

        # Conditional edge from validate_batch
        workflow.add_conditional_edges(
            "validate_batch",
            self.check_json_error,
            {
                "needs_correction": "prepare_correction",
                "continue": "check_completion",
            },
        )

        workflow.add_edge("prepare_correction", "generate_batch")

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

        workflow.add_edge("retry_generation", "generate_batch")
        workflow.add_edge("save_questions", END)

        return workflow.compile()

    async def prepare_prompt(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare the prompt for batch generation."""
        try:
            # Get template based on language
            template_name = f"batch_multiple_choice{'_no' if self.language == QuizLanguage.NORWEGIAN else ''}"

            # Create generation parameters
            generation_parameters = GenerationParameters(
                target_count=state.target_question_count
                - len(state.generated_questions),
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
                question_count=state.target_question_count
                - len(state.generated_questions),
            )

            # Create messages using template
            messages = await self.template_manager.create_messages(
                QuestionType.MULTIPLE_CHOICE,
                state.module_content,
                generation_parameters,
                template_name,
                self.language,
                extra_variables={
                    "module_name": state.module_name,
                    "question_count": state.target_question_count
                    - len(state.generated_questions),
                },
            )

            # Extract the user prompt (combine system and user for simplicity)
            state.current_prompt = "\\n\\n".join([msg.content for msg in messages])

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
                    content="You are an expert educator creating quiz questions.",
                ),
                LLMMessage(role="user", content=state.current_prompt),
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
        """Validate and parse the generated questions."""
        if not state.raw_response or state.error_message:
            return state

        try:
            # Parse the response to extract individual questions
            questions_data = self._parse_batch_response(state.raw_response)

            # Validate and create question objects
            for q_data in questions_data:
                try:
                    # Validate required fields
                    self._validate_mcq_structure(q_data)

                    # Extract difficulty from question data (if present)
                    difficulty_str = q_data.pop("difficulty", None)
                    difficulty = None
                    if difficulty_str:
                        try:
                            from ..types.base import QuestionDifficulty

                            difficulty = QuestionDifficulty(difficulty_str.lower())
                        except (ValueError, AttributeError):
                            logger.warning(
                                "module_batch_invalid_difficulty",
                                module_id=state.module_id,
                                difficulty_value=difficulty_str,
                            )

                    # Create question object with difficulty at model level
                    question = Question(
                        quiz_id=state.quiz_id,
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        question_data=q_data,  # Now without difficulty field
                        difficulty=difficulty,
                        is_approved=False,
                    )
                    state.generated_questions.append(question)

                except Exception as e:
                    logger.warning(
                        "module_batch_question_validation_failed",
                        module_id=state.module_id,
                        question_data=q_data,
                        error=str(e),
                    )
                    continue

            logger.info(
                "module_batch_validation_completed",
                module_id=state.module_id,
                questions_validated=len(state.generated_questions),
                questions_parsed=len(questions_data),
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

    def check_json_error(self, state: ModuleBatchState) -> str:
        """Check if we have a JSON parsing error that needs correction."""
        if state.parsing_error and state.correction_attempts < state.max_corrections:
            return "needs_correction"
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

            state.current_prompt = correction_prompt

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

    def should_retry(self, state: ModuleBatchState) -> str:
        """Determine if we should retry generation."""
        if state.error_message:
            return "failed"

        questions_needed = state.target_question_count - len(state.generated_questions)

        if questions_needed <= 0:
            return "complete"

        if state.retry_count < state.max_retries:
            logger.info(
                "module_batch_retry_needed",
                module_id=state.module_id,
                questions_needed=questions_needed,
                retry_count=state.retry_count + 1,
                max_retries=state.max_retries,
            )
            return "retry"

        logger.warning(
            "module_batch_max_retries_reached",
            module_id=state.module_id,
            questions_generated=len(state.generated_questions),
            target_questions=state.target_question_count,
        )
        return "complete"

    async def retry_generation(self, state: ModuleBatchState) -> ModuleBatchState:
        """Prepare for retry with adjusted parameters."""
        state.retry_count += 1
        state.error_message = None
        state.raw_response = ""

        # Add exponential backoff
        await asyncio.sleep(1 * state.retry_count)

        return state

    async def save_questions(self, state: ModuleBatchState) -> ModuleBatchState:
        """Save all generated questions to the database."""
        if not state.generated_questions:
            return state

        try:
            async with get_async_session() as session:
                # Add questions to session
                for question in state.generated_questions:
                    session.add(question)

                # Commit all questions
                await session.commit()

                logger.info(
                    "module_batch_questions_saved",
                    module_id=state.module_id,
                    questions_saved=len(state.generated_questions),
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

    def _validate_mcq_structure(self, question_data: dict[str, Any]) -> None:
        """
        Validate MCQ question data structure.

        Args:
            question_data: Question data to validate

        Raises:
            ValueError: If data structure is invalid
        """
        required_fields = [
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_answer",
        ]

        for field in required_fields:
            if field not in question_data:
                raise ValueError(f"Missing required field: {field}")

        # Validate correct answer format
        if question_data["correct_answer"] not in ["A", "B", "C", "D"]:
            raise ValueError(
                f"Invalid correct answer: {question_data['correct_answer']}"
            )

        # Validate text lengths
        if len(question_data["question_text"]) < 10:
            raise ValueError("Question text too short")

        for option_key in ["option_a", "option_b", "option_c", "option_d"]:
            if len(question_data[option_key]) < 1:
                raise ValueError(f"Option {option_key} is empty")

    async def process_module(
        self,
        quiz_id: UUID,
        module_id: str,
        module_name: str,
        module_content: str,
        question_count: int,
    ) -> list[Question]:
        """Process a single module to generate questions."""
        initial_state = ModuleBatchState(
            quiz_id=quiz_id,
            module_id=module_id,
            module_name=module_name,
            module_content=module_content,
            target_question_count=question_count,
            language=self.language,
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

            logger.info(
                "module_batch_processing_completed",
                module_id=module_id,
                questions_generated=len(final_state.generated_questions),
                target_questions=question_count,
                success=final_state.error_message is None,
            )

            # Ensure we return a list of Questions
            return list(final_state.generated_questions)

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
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language

    async def process_all_modules(
        self,
        quiz_id: UUID,
        modules_data: dict[str, dict[str, Any]],
    ) -> dict[str, list[Question]]:
        """Process all modules in parallel."""
        logger.info(
            "parallel_module_processing_started",
            quiz_id=str(quiz_id),
            modules_count=len(modules_data),
        )

        # Create tasks for each module
        tasks = []
        for module_id, module_info in modules_data.items():
            workflow = ModuleBatchWorkflow(
                llm_provider=self.llm_provider,
                template_manager=self.template_manager,
                language=self.language,
            )

            task = workflow.process_module(
                quiz_id=quiz_id,
                module_id=module_id,
                module_name=module_info["name"],
                module_content=module_info["content"],
                question_count=module_info["question_count"],
            )

            tasks.append((module_id, task))

        # Execute all tasks in parallel
        results = {}
        for module_id, task in tasks:
            try:
                questions = await task
                results[module_id] = questions
                logger.info(
                    "parallel_module_completed",
                    module_id=module_id,
                    questions_generated=len(questions),
                )
            except Exception as e:
                logger.error(
                    "parallel_module_failed",
                    module_id=module_id,
                    error=str(e),
                    exc_info=True,
                )
                results[module_id] = []

        total_questions = sum(len(questions) for questions in results.values())
        logger.info(
            "parallel_module_processing_completed",
            quiz_id=str(quiz_id),
            total_questions=total_questions,
            modules_processed=len(results),
        )

        return results
