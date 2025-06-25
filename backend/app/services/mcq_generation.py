import json
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import UUID

from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import SecretStr
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.core.logging_config import get_logger
from app.crud import get_content_from_quiz
from app.models import Question, QuestionCreate

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
        """Get configured LLM instance."""
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=SecretStr(settings.OPENAI_SECRET_KEY),
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

    def content_preparation(self, state: MCQGenerationState) -> MCQGenerationState:
        """Prepare content chunks for question generation."""
        logger.info(
            "content_preparation_started",
            quiz_id=str(state["quiz_id"]),
            target_questions=state["target_question_count"],
        )

        try:
            with Session(engine) as session:
                # Use the CRUD function to get extracted content
                extracted_content_json = get_content_from_quiz(
                    session, state["quiz_id"]
                )

                if not extracted_content_json:
                    raise ValueError("No extracted content found for quiz")

                # Parse the JSON content
                content_dict = json.loads(extracted_content_json)

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

    def generate_question(self, state: MCQGenerationState) -> MCQGenerationState:
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

            result = chain.invoke(
                {
                    "content": content_chunk,
                }
            )

            # Parse JSON response
            result_text = result.content if hasattr(result, "content") else str(result)

            # Clean up JSON response (remove markdown formatting if present)
            json_text = str(result_text).strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            question_data = json.loads(json_text)

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
                question_text=question_data["question_text"][:100] + "...",
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
            if any(
                critical_error in error_str
                for critical_error in [
                    "invalid_request_error",
                    "authentication",
                    "authorization",
                    "model_not_found",
                    "organization must be verified",
                    "rate_limit_exceeded",
                ]
            ):
                # Critical error - stop the workflow
                state[
                    "error_message"
                ] = f"Critical error during question generation: {str(e)}"
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

    def save_questions_to_database(
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
            with Session(engine) as session:
                saved_count = 0

                for question_data in questions:
                    # Create QuestionCreate instance for validation
                    question_create = QuestionCreate(**question_data)

                    # Create Question instance
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
                    session.add(question)
                    saved_count += 1

                session.commit()

                logger.info(
                    "saving_questions_completed",
                    quiz_id=str(quiz_id),
                    questions_saved=saved_count,
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

            # Run the workflow
            final_state = app.invoke(initial_state)

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


# Global service instance
mcq_generation_service = MCQGenerationService()
