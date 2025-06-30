import asyncio
import json
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import UUID

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr

from app.config import settings
from app.database import get_async_session, transaction
from app.exceptions import ValidationError
from app.logging_config import get_logger

from .models import Question
from .schemas import QuestionCreate

logger = get_logger("mcq_generation")


class MCQGenerationState(TypedDict):
    """State for the MCQ generation workflow."""

    quiz_id: UUID
    content_chunks: list[str]
    target_question_count: int
    llm_model: str
    llm_temperature: float
    generated_questions: list[dict[str, Any]]
    current_chunk_index: int
    questions_generated: int
    error_message: str | None


class MCQGenerationService:
    """Service for generating multiple-choice questions using LangGraph workflow."""

    def __init__(self) -> None:
        self.llm = None
        self.workflow: StateGraph | None = None

    def _get_llm(self, model: str, temperature: float) -> ChatOpenAI:
        """Get configured LLM instance with appropriate timeout."""
        if not settings.OPENAI_SECRET_KEY:
            raise ValueError("OPENAI_SECRET_KEY is required for LLM functionality")

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=SecretStr(settings.OPENAI_SECRET_KEY),
            timeout=settings.LLM_API_TIMEOUT,
            max_retries=0,  # We'll handle retries ourselves
        )

    def _create_mcq_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template for MCQ generation."""
        template = """You are an expert educator creating multiple-choice questions for a quiz.

Based on the following course content, generate ONE high-quality multiple-choice question with exactly 4 options (A, B, C, D) and one correct answer.

Course Content:
{content}

Requirements:
- The question should test understanding, not just memorization
- All 4 options should be plausible but only one correct
- Options should be similar in length and style
- Avoid "all of the above" or "none of the above" options
- Use clear, concise language
- Focus on key concepts from the content

Return your response as valid JSON with this exact structure:
{{
    "question_text": "Your question here",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_answer": "[LETTER]"
}}

The correct_answer must be exactly one of: A, B, C, or D. Try to vary the correct answer letter, do not always make it "A".

Generate exactly ONE question based on this content."""

        return ChatPromptTemplate.from_template(template)

    def _chunk_content(
        self, content_dict: dict[str, Any], max_chunk_size: int = 3000
    ) -> list[str]:
        """Split content into manageable chunks for question generation."""
        chunks = []

        for _module_id, pages in content_dict.items():
            if not isinstance(pages, list):
                continue

            for page in pages:
                if not isinstance(page, dict):
                    continue

                page_content = page.get("content", "")
                if not page_content or len(page_content.strip()) < 100:
                    continue

                # Split long content into chunks
                if len(page_content) <= max_chunk_size:
                    chunks.append(page_content)
                else:
                    # Split by paragraphs first, then by sentences if needed
                    paragraphs = page_content.split("\n\n")
                    current_chunk = ""

                    for paragraph in paragraphs:
                        if len(current_chunk) + len(paragraph) <= max_chunk_size:
                            current_chunk += paragraph + "\n\n"
                        else:
                            if current_chunk.strip():
                                chunks.append(current_chunk.strip())
                            current_chunk = paragraph + "\n\n"

                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())

        logger.info(
            "content_chunking_completed",
            total_chunks=len(chunks),
            avg_chunk_size=sum(len(c) for c in chunks) // len(chunks) if chunks else 0,
        )

        return chunks

    async def content_preparation(
        self, state: MCQGenerationState
    ) -> MCQGenerationState:
        """Prepare content chunks for question generation."""
        logger.info(
            "content_preparation_started",
            quiz_id=str(state["quiz_id"]),
            target_questions=state["target_question_count"],
        )

        try:
            async with get_async_session() as session:
                from app.crud import get_content_from_quiz

                content_dict = await get_content_from_quiz(session, state["quiz_id"])

                if not content_dict:
                    raise ValueError("No extracted content found for quiz")

                chunks = self._chunk_content(content_dict)
                if not chunks:
                    raise ValueError("No valid content chunks found")

                state["content_chunks"] = chunks
                state["current_chunk_index"] = 0
                state["questions_generated"] = 0
                state["generated_questions"] = []

                logger.info(
                    "content_preparation_completed",
                    quiz_id=str(state["quiz_id"]),
                    chunks_created=len(chunks),
                )

                return state

        except Exception as e:
            logger.error(
                "content_preparation_failed",
                quiz_id=str(state["quiz_id"]),
                error=str(e),
                exc_info=True,
            )
            state["error_message"] = f"Content preparation failed: {str(e)}"
            return state

    async def generate_question(self, state: MCQGenerationState) -> MCQGenerationState:
        """Generate a single MCQ question from current content chunk."""
        quiz_id = state["quiz_id"]
        current_chunk = state["current_chunk_index"]

        logger.info(
            "question_generation_started",
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

            # Get LLM and create chain
            llm = self._get_llm(state["llm_model"], state["llm_temperature"])
            prompt = self._create_mcq_prompt()

            chain = prompt | llm

            # Generate question from current chunk
            content_chunk = state["content_chunks"][current_chunk]

            # Generate question with retry logic
            result = None
            last_exception = None

            for attempt in range(settings.MAX_RETRIES + 1):
                try:
                    result = await chain.ainvoke({"content": content_chunk})
                    break  # Success, exit retry loop
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()

                    # Check if retryable (rate limits, timeouts, server errors)
                    retryable = any(
                        err in error_str
                        for err in [
                            "timeout",
                            "rate_limit",
                            "rate limit",
                            "502",
                            "503",
                            "504",
                        ]
                    )

                    if attempt == settings.MAX_RETRIES or not retryable:
                        break  # Final attempt or non-retryable error

                    # Wait with exponential backoff
                    delay = settings.INITIAL_RETRY_DELAY * (
                        settings.RETRY_BACKOFF_FACTOR**attempt
                    )
                    delay = min(delay, settings.MAX_RETRY_DELAY)
                    await asyncio.sleep(delay)

            if result is None:
                if last_exception:
                    raise last_exception
                else:
                    raise ValueError("Failed to get response from LLM after retries")

            # Parse JSON response
            result_text = result.content if hasattr(result, "content") else str(result)

            # Clean up JSON response with robust parsing
            json_text = str(result_text).strip()

            # Remove markdown code block formatting
            if json_text.startswith("```"):
                # Handle various markdown patterns: ```json, ```JSON, ```
                lines = json_text.split("\n")
                if len(lines) > 1:
                    json_text = "\n".join(lines[1:])  # Skip first line

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
                question_data = json.loads(json_text)
            except json.JSONDecodeError as json_error:
                logger.warning(
                    "json_parsing_failed",
                    quiz_id=str(quiz_id),
                    chunk_index=current_chunk,
                    response_length=len(result_text),
                    cleaned_json_length=len(json_text),
                    error=str(json_error),
                    response_starts_with=str(result_text)[:50] + "..."
                    if len(str(result_text)) > 50
                    else str(result_text),
                )
                raise ValueError(f"Failed to parse LLM response as JSON: {json_error}")

            # Validate the question data structure
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

            # Add quiz_id to the question data
            question_data["quiz_id"] = quiz_id

            state["generated_questions"].append(question_data)
            state["questions_generated"] += 1
            state["current_chunk_index"] += 1

            logger.info(
                "question_generation_completed",
                quiz_id=str(quiz_id),
                chunk_index=current_chunk,
                questions_generated=state["questions_generated"],
                question_length=len(question_data["question_text"]),
                correct_answer=question_data["correct_answer"],
            )

            return state

        except Exception as e:
            logger.error(
                "question_generation_failed",
                quiz_id=str(quiz_id),
                chunk_index=current_chunk,
                error=str(e),
                exc_info=True,
            )

            # Check if this is a critical error that should stop the entire workflow
            error_str = str(e).lower()
            error_type = type(e).__name__.lower()

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

            is_critical = any(
                pattern in error_str or pattern in error_type
                for pattern in critical_patterns
            )

            if is_critical:
                # Critical error - stop the workflow
                state["error_message"] = (
                    f"Critical error during question generation: {str(e)}"
                )
                return state

            # Non-critical error - move to next chunk and continue
            state["current_chunk_index"] += 1
            return state

    def should_continue_generation(self, state: MCQGenerationState) -> str:
        """Determine if we should continue generating questions."""
        target_count = state["target_question_count"]
        generated_count = state["questions_generated"]
        current_chunk = state["current_chunk_index"]
        total_chunks = len(state["content_chunks"])

        # Stop immediately if there's a critical error
        if state["error_message"] is not None:
            logger.error(
                "generation_stopped_due_to_error",
                quiz_id=str(state["quiz_id"]),
                error=state["error_message"],
            )
            return "save_questions"

        # Stop if we have enough questions
        if generated_count >= target_count:
            logger.info(
                "generation_target_reached",
                quiz_id=str(state["quiz_id"]),
                generated=generated_count,
                target=target_count,
            )
            return "save_questions"

        # Stop if we've exhausted all content chunks
        if current_chunk >= total_chunks:
            logger.info(
                "all_chunks_processed",
                quiz_id=str(state["quiz_id"]),
                generated=generated_count,
                target=target_count,
                chunks_processed=total_chunks,
            )
            return "save_questions"

        # Continue generating
        return "generate_question"

    async def save_questions_to_database(
        self, state: MCQGenerationState
    ) -> MCQGenerationState:
        """Save generated questions to the database."""
        quiz_id = state["quiz_id"]
        questions = state["generated_questions"]

        logger.info(
            "saving_questions_started",
            quiz_id=str(quiz_id),
            question_count=len(questions),
        )

        try:
            async with transaction(isolation_level="SERIALIZABLE") as session:
                saved_count = 0
                question_objects = []

                for question_data in questions:
                    try:
                        question_create = QuestionCreate(**question_data)

                        question = Question(
                            quiz_id=quiz_id,
                            question_text=question_create.question_text,
                            option_a=question_create.option_a,
                            option_b=question_create.option_b,
                            option_c=question_create.option_c,
                            option_d=question_create.option_d,
                            correct_answer=question_create.correct_answer,
                            is_approved=False,
                        )
                        question_objects.append(question)
                    except Exception as validation_error:
                        logger.warning(
                            "question_validation_failed",
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

                logger.info(
                    "saving_questions_completed",
                    quiz_id=str(quiz_id),
                    questions_saved=saved_count,
                    questions_attempted=len(questions),
                )

                return state

        except Exception as e:
            logger.error(
                "saving_questions_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            state["error_message"] = f"Failed to save questions: {str(e)}"
            return state

    def build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for MCQ generation."""
        workflow = StateGraph(MCQGenerationState)

        # Add nodes
        workflow.add_node("content_preparation", self.content_preparation)
        workflow.add_node("generate_question", self.generate_question)
        workflow.add_node("save_questions", self.save_questions_to_database)

        # Add edges
        workflow.add_edge(START, "content_preparation")
        workflow.add_edge("content_preparation", "generate_question")

        # Conditional edge for continuing generation
        workflow.add_conditional_edges(
            "generate_question",
            self.should_continue_generation,
            {
                "generate_question": "generate_question",
                "save_questions": "save_questions",
            },
        )

        workflow.add_edge("save_questions", END)

        return workflow

    async def generate_mcqs_for_quiz(
        self,
        quiz_id: UUID,
        target_question_count: int,
        llm_model: str,
        llm_temperature: float,
    ) -> dict[str, Any]:
        """
        Generate MCQs for a quiz using the LangGraph workflow.

        Args:
            quiz_id: UUID of the quiz
            target_question_count: Number of questions to generate
            llm_model: LLM model to use
            llm_temperature: Temperature setting for LLM

        Returns:
            Dict containing generation results and statistics
        """
        # Validate input parameters
        if target_question_count <= 0 or target_question_count > 100:
            raise ValidationError("target_question_count must be between 1 and 100")

        if not (0.0 <= llm_temperature <= 2.0):
            raise ValidationError("llm_temperature must be between 0.0 and 2.0")

        logger.info(
            "mcq_generation_workflow_started",
            quiz_id=str(quiz_id),
            target_questions=target_question_count,
            model=llm_model,
            temperature=llm_temperature,
        )

        try:
            # Build workflow if not already built
            if not self.workflow:
                self.workflow = self.build_workflow()

            app = self.workflow.compile() if self.workflow else None
            if not app:
                raise RuntimeError("Failed to compile workflow")

            # Initial state
            initial_state: MCQGenerationState = {
                "quiz_id": quiz_id,
                "content_chunks": [],
                "target_question_count": target_question_count,
                "llm_model": llm_model,
                "llm_temperature": llm_temperature,
                "generated_questions": [],
                "current_chunk_index": 0,
                "questions_generated": 0,
                "error_message": None,
            }

            # Run the workflow asynchronously
            final_state = await app.ainvoke(initial_state)

            # Prepare results
            results = {
                "quiz_id": str(quiz_id),
                "questions_generated": final_state["questions_generated"],
                "target_questions": target_question_count,
                "chunks_processed": final_state["current_chunk_index"],
                "total_chunks": len(final_state["content_chunks"]),
                "success": final_state["error_message"] is None,
                "error_message": final_state["error_message"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                "mcq_generation_workflow_completed",
                quiz_id=str(quiz_id),
                questions_generated=final_state["questions_generated"],
                success=results["success"],
            )

            return results

        except Exception as e:
            logger.error(
                "mcq_generation_workflow_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )

            return {
                "quiz_id": str(quiz_id),
                "questions_generated": 0,
                "target_questions": target_question_count,
                "chunks_processed": 0,
                "total_chunks": 0,
                "success": False,
                "error_message": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
