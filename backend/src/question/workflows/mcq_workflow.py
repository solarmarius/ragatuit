"""Multiple Choice Question generation workflow implementation."""

import json
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.database import get_async_session, transaction
from src.logging_config import get_logger

from ..providers import LLMMessage
from ..types import GenerationParameters
from .base import BaseQuestionWorkflow, WorkflowState

logger = get_logger("mcq_workflow")


class MCQWorkflow(BaseQuestionWorkflow):
    """Workflow implementation for Multiple Choice Question generation."""

    @property
    def workflow_name(self) -> str:
        """Return the workflow name."""
        return "mcq_generation_workflow"

    def build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow for MCQ generation.

        Returns:
            Configured StateGraph workflow
        """
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("prepare_content", self.prepare_content)
        workflow.add_node("generate_question", self.generate_question)
        workflow.add_node("validate_question", self.validate_question)
        workflow.add_node("save_questions", self.save_questions_to_database)

        # Add edges
        workflow.add_edge(START, "prepare_content")
        workflow.add_edge("prepare_content", "generate_question")
        workflow.add_edge("generate_question", "validate_question")

        # Conditional edge for continuing generation
        workflow.add_conditional_edges(
            "validate_question",
            self.should_continue_generation,
            {
                "generate_question": "generate_question",
                "save_questions": "save_questions",
            },
        )

        workflow.add_edge("save_questions", END)

        return workflow

    async def prepare_content(self, state: WorkflowState) -> WorkflowState:
        """
        Prepare content chunks for MCQ generation.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        logger.info(
            "mcq_content_preparation_started",
            quiz_id=str(state["quiz_id"]),
            target_questions=state["target_question_count"],
        )

        try:
            async with get_async_session() as session:
                # Get content from quiz
                from src.quiz.service import get_content_from_quiz

                content_dict = await get_content_from_quiz(session, state["quiz_id"])

                if not content_dict:
                    raise ValueError("No extracted content found for quiz")

                # Chunk the content using the base class method
                content_chunks = self.chunk_content(content_dict)

                if not content_chunks:
                    raise ValueError("No valid content chunks found")

                # Convert ContentChunk objects to strings for backward compatibility
                chunk_strings = [chunk.content for chunk in content_chunks]

                state["content_chunks"] = chunk_strings
                state["current_chunk_index"] = 0
                state["questions_generated"] = 0
                state["generated_questions"] = []

                # Add metadata about content processing
                state["workflow_metadata"].update(
                    {
                        "content_chunks_created": len(chunk_strings),
                        "total_content_length": sum(
                            len(chunk) for chunk in chunk_strings
                        ),
                        "avg_chunk_length": sum(len(chunk) for chunk in chunk_strings)
                        // len(chunk_strings)
                        if chunk_strings
                        else 0,
                    }
                )

                logger.info(
                    "mcq_content_preparation_completed",
                    quiz_id=str(state["quiz_id"]),
                    chunks_created=len(chunk_strings),
                )

                return state

        except Exception as e:
            logger.error(
                "mcq_content_preparation_failed",
                quiz_id=str(state["quiz_id"]),
                error=str(e),
                exc_info=True,
            )
            state["error_message"] = f"Content preparation failed: {str(e)}"
            return state

    async def generate_question(self, state: WorkflowState) -> WorkflowState:
        """
        Generate a single MCQ from current content chunk.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with generated question
        """
        quiz_id = state["quiz_id"]
        current_chunk = state["current_chunk_index"]

        logger.info(
            "mcq_generation_started",
            quiz_id=str(quiz_id),
            chunk_index=current_chunk,
            questions_generated=state["questions_generated"],
        )

        try:
            if current_chunk >= len(state["content_chunks"]):
                logger.warning(
                    "no_more_content_chunks",
                    quiz_id=str(quiz_id),
                    chunk_index=current_chunk,
                    total_chunks=len(state["content_chunks"]),
                )
                return state

            # Get current content chunk
            content_chunk = state["content_chunks"][current_chunk]

            # Create messages for LLM
            messages = await self.create_generation_messages(
                content_chunk, state["generation_parameters"]
            )

            # Generate question using LLM provider
            llm_provider = state["llm_provider"]
            response = await llm_provider.generate_with_retry(messages)

            # Parse the JSON response
            question_data = self._parse_llm_response(response.content)

            # Validate the question data structure
            self._validate_mcq_structure(question_data)

            # Add quiz_id to the question data
            question_data["quiz_id"] = quiz_id

            state["generated_questions"].append(question_data)
            state["questions_generated"] += 1
            state["current_chunk_index"] += 1

            # Update metadata
            state["workflow_metadata"].update(
                {
                    "last_generation_time": response.response_time,
                    "total_tokens_used": state["workflow_metadata"].get(
                        "total_tokens_used", 0
                    )
                    + (response.total_tokens or 0),
                    "last_model_used": response.model,
                }
            )

            logger.info(
                "mcq_generation_completed",
                quiz_id=str(quiz_id),
                chunk_index=current_chunk,
                questions_generated=state["questions_generated"],
                question_length=len(question_data["question_text"]),
                correct_answer=question_data["correct_answer"],
                response_time=response.response_time,
            )

            return state

        except Exception as e:
            logger.error(
                "mcq_generation_failed",
                quiz_id=str(quiz_id),
                chunk_index=current_chunk,
                error=str(e),
                exc_info=True,
            )

            # Check if this is a critical error that should stop the workflow
            if self._is_critical_error(e):
                state["error_message"] = (
                    f"Critical error during question generation: {str(e)}"
                )
                return state

            # Non-critical error - move to next chunk and continue
            state["current_chunk_index"] += 1
            return state

    async def validate_question(self, state: WorkflowState) -> WorkflowState:
        """
        Validate generated MCQ data.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with validation results
        """
        # For MCQ, validation is already done in generate_question
        # This step could be extended for additional quality checks

        if state["generated_questions"]:
            last_question = state["generated_questions"][-1]

            # Additional quality checks could go here
            # For example: checking option similarity, question difficulty, etc.

            logger.debug(
                "mcq_validation_completed",
                quiz_id=str(state["quiz_id"]),
                question_id=last_question.get("id", "unknown"),
                validation_passed=True,
            )

        return state

    def should_continue_generation(self, state: WorkflowState) -> str:
        """
        Determine if MCQ generation should continue.

        Args:
            state: Current workflow state

        Returns:
            Next node name
        """
        target_count = state["target_question_count"]
        generated_count = state["questions_generated"]
        current_chunk = state["current_chunk_index"]
        total_chunks = len(state["content_chunks"])

        # Stop immediately if there's a critical error
        if state["error_message"] is not None:
            logger.error(
                "mcq_generation_stopped_due_to_error",
                quiz_id=str(state["quiz_id"]),
                error=state["error_message"],
            )
            return "save_questions"

        # Stop if we have enough questions
        if generated_count >= target_count:
            logger.info(
                "mcq_generation_target_reached",
                quiz_id=str(state["quiz_id"]),
                generated=generated_count,
                target=target_count,
            )
            return "save_questions"

        # Stop if we've exhausted all content chunks
        if current_chunk >= total_chunks:
            logger.info(
                "mcq_all_chunks_processed",
                quiz_id=str(state["quiz_id"]),
                generated=generated_count,
                target=target_count,
                chunks_processed=total_chunks,
            )
            return "save_questions"

        # Continue generating
        return "generate_question"

    async def save_questions_to_database(self, state: WorkflowState) -> WorkflowState:
        """
        Save generated MCQs to the database.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        quiz_id = state["quiz_id"]
        questions = state["generated_questions"]

        logger.info(
            "mcq_saving_questions_started",
            quiz_id=str(quiz_id),
            question_count=len(questions),
        )

        try:
            async with transaction(isolation_level="SERIALIZABLE") as session:
                from ..types import Question, QuestionType

                saved_count = 0
                question_objects = []

                for question_data in questions:
                    try:
                        # Convert to new polymorphic format
                        mcq_data = {
                            "question_text": question_data["question_text"],
                            "option_a": question_data["option_a"],
                            "option_b": question_data["option_b"],
                            "option_c": question_data["option_c"],
                            "option_d": question_data["option_d"],
                            "correct_answer": question_data["correct_answer"],
                        }

                        question = Question(
                            quiz_id=quiz_id,
                            question_type=QuestionType.MULTIPLE_CHOICE,
                            question_data=mcq_data,
                            is_approved=False,
                        )
                        question_objects.append(question)

                    except Exception as validation_error:
                        logger.warning(
                            "mcq_question_validation_failed",
                            quiz_id=str(quiz_id),
                            question_fields=list(question_data.keys())
                            if isinstance(question_data, dict)
                            else "invalid_format",
                            error=str(validation_error),
                        )
                        continue

                if question_objects:
                    session.add_all(question_objects)
                    saved_count = len(question_objects)

                # Update metadata
                state["workflow_metadata"].update(
                    {
                        "questions_saved": saved_count,
                        "questions_attempted": len(questions),
                        "save_success_rate": saved_count / len(questions)
                        if questions
                        else 0,
                    }
                )

                logger.info(
                    "mcq_saving_questions_completed",
                    quiz_id=str(quiz_id),
                    questions_saved=saved_count,
                    questions_attempted=len(questions),
                )

                return state

        except Exception as e:
            logger.error(
                "mcq_saving_questions_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            state["error_message"] = f"Failed to save questions: {str(e)}"
            return state

    def _create_default_messages(
        self, content_chunk: str, generation_parameters: GenerationParameters
    ) -> list[LLMMessage]:
        """
        Create default messages for MCQ generation.

        Args:
            content_chunk: Content to generate questions from
            generation_parameters: Generation parameters

        Returns:
            List of messages for LLM
        """
        # Default MCQ generation prompt
        system_prompt = """You are an expert educator creating multiple-choice questions for a quiz.

Based on the following course content, generate ONE high-quality multiple-choice question with exactly 4 options (A, B, C, D) and one correct answer.

Requirements:
- The question should test understanding, not just memorization
- All 4 options should be plausible but only one correct
- Options should be similar in length and style
- Avoid "all of the above" or "none of the above" options
- Use clear, concise language
- Focus on key concepts from the content

Return your response as valid JSON with this exact structure:
{
    "question_text": "Your question here",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "[LETTER]"
}

The correct_answer must be exactly one of: A, B, C, or D. Try to vary the correct answer letter, do not always make it "A".

Generate exactly ONE question based on this content."""

        user_prompt = f"Course Content:\n{content_chunk}"

        # Add custom instructions if provided
        if generation_parameters.custom_instructions:
            user_prompt += f"\n\nAdditional Instructions:\n{generation_parameters.custom_instructions}"

        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

    def _parse_llm_response(self, response_content: str) -> dict[str, Any]:
        """
        Parse JSON response from LLM.

        Args:
            response_content: Raw LLM response

        Returns:
            Parsed question data

        Raises:
            ValueError: If response cannot be parsed
        """
        # Clean up JSON response (from existing logic)
        json_text = str(response_content).strip()

        # Remove markdown code block formatting
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            if len(lines) > 1:
                json_text = "\n".join(lines[1:])

        if json_text.endswith("```"):
            json_text = json_text[:-3]

        # Remove any remaining backticks and extra whitespace
        json_text = json_text.replace("`", "").strip()

        # Try to find JSON object if surrounded by other text
        start_idx = json_text.find("{")
        end_idx = json_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_text = json_text[start_idx : end_idx + 1]

        try:
            parsed_data = json.loads(json_text)
            if not isinstance(parsed_data, dict):
                raise ValueError("Response must be a JSON object")
            return parsed_data
        except json.JSONDecodeError as json_error:
            raise ValueError(f"Failed to parse LLM response as JSON: {json_error}")

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

        # Additional validation from configuration
        type_specific_settings = self.configuration.type_specific_settings

        if type_specific_settings.get("min_option_length"):
            min_length = type_specific_settings["min_option_length"]
            for option_key in ["option_a", "option_b", "option_c", "option_d"]:
                if len(question_data[option_key]) < min_length:
                    raise ValueError(
                        f"Option {option_key} is too short (minimum {min_length} characters)"
                    )

        if type_specific_settings.get("max_option_length"):
            max_length = type_specific_settings["max_option_length"]
            for option_key in ["option_a", "option_b", "option_c", "option_d"]:
                if len(question_data[option_key]) > max_length:
                    raise ValueError(
                        f"Option {option_key} is too long (maximum {max_length} characters)"
                    )

    def _is_critical_error(self, error: Exception) -> bool:
        """
        Determine if an error should stop the entire workflow.

        Args:
            error: The exception that occurred

        Returns:
            True if error is critical, False otherwise
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Critical errors that should stop the workflow immediately
        critical_patterns = [
            # Authentication/Authorization issues
            "invalid_api_key",
            "invalidapikeyerror",
            "authentication",
            "authorization",
            "insufficient_quota",
            "billing",
            "organization must be verified",
            "account_deactivated",
            # Model/Request issues
            "model_not_found",
            "invalid_model",
            "unsupported_model",
            "invalid_request_error",
            "context_length_exceeded",
            "maximum_context_length",
            "token_limit_exceeded",
        ]

        return any(
            pattern in error_str or pattern in error_type
            for pattern in critical_patterns
        )
