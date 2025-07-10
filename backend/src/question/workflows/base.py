"""Abstract base classes for question generation workflows."""

from abc import ABC, abstractmethod
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from src.config import get_logger

from ..providers import BaseLLMProvider, LLMMessage
from ..types import GenerationParameters, GenerationResult, QuestionType

logger = get_logger("question_workflow")


class WorkflowState(TypedDict):
    """Base state for question generation workflows."""

    # Input parameters
    quiz_id: UUID
    question_type: QuestionType
    target_question_count: int
    content_chunks: list[str]
    generation_parameters: GenerationParameters

    # Provider configuration
    llm_provider: BaseLLMProvider

    # Workflow state
    current_chunk_index: int
    questions_generated: int
    generated_questions: list[dict[str, Any]]

    # Error handling
    error_message: str | None

    # Metadata
    workflow_metadata: dict[str, Any]


class ContentChunk(BaseModel):
    """A chunk of content for question generation."""

    content: str = Field(description="The content text")
    source: str | None = Field(default=None, description="Source identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_word_count(self) -> int:
        """Get word count of the content."""
        return len(self.content.split())

    def get_character_count(self) -> int:
        """Get character count of the content."""
        return len(self.content)


class WorkflowConfiguration(BaseModel):
    """Configuration for question generation workflows."""

    # Content processing
    max_chunk_size: int = Field(default=3000, ge=100, le=10000)
    min_chunk_size: int = Field(default=100, ge=50, le=1000)
    overlap_size: int = Field(default=200, ge=0, le=500)

    # Generation parameters
    max_questions_per_chunk: int = Field(default=3, ge=1, le=10)
    allow_duplicate_detection: bool = Field(default=True)
    quality_threshold: float = Field(default=0.8, ge=0.0, le=1.0)

    # Retry configuration
    max_generation_retries: int = Field(default=3, ge=0, le=10)
    retry_on_validation_failure: bool = Field(default=True)

    # Question type specific settings
    type_specific_settings: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class BaseQuestionWorkflow(ABC):
    """Abstract base class for question generation workflows."""

    def __init__(
        self,
        question_type: QuestionType,
        configuration: WorkflowConfiguration,
        template_manager: Any | None = None,
    ):
        self.question_type = question_type
        self.configuration = configuration
        self.template_manager = template_manager
        self._workflow: StateGraph | None = None

    @property
    @abstractmethod
    def workflow_name(self) -> str:
        """Return the workflow name."""
        pass

    @abstractmethod
    def build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow for this question type.

        Returns:
            Configured StateGraph workflow
        """
        pass

    @abstractmethod
    async def prepare_content(self, state: WorkflowState) -> WorkflowState:
        """
        Prepare content chunks for question generation.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state
        """
        pass

    @abstractmethod
    async def generate_question(self, state: WorkflowState) -> WorkflowState:
        """
        Generate a single question from current content chunk.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with generated question
        """
        pass

    @abstractmethod
    async def validate_question(self, state: WorkflowState) -> WorkflowState:
        """
        Validate generated question data.

        Args:
            state: Current workflow state

        Returns:
            Updated workflow state with validation results
        """
        pass

    @abstractmethod
    def should_continue_generation(self, state: WorkflowState) -> str:
        """
        Determine if generation should continue.

        Args:
            state: Current workflow state

        Returns:
            Next node name or END
        """
        pass

    def get_workflow(self) -> StateGraph:
        """
        Get the compiled workflow.

        Returns:
            Compiled StateGraph workflow
        """
        if self._workflow is None:
            self._workflow = self.build_workflow()
        return self._workflow

    async def execute(
        self,
        quiz_id: UUID,
        content_chunks: list[str],
        generation_parameters: GenerationParameters,
        llm_provider: BaseLLMProvider,
    ) -> GenerationResult:
        """
        Execute the question generation workflow.

        Args:
            quiz_id: Quiz identifier
            content_chunks: List of content chunks
            generation_parameters: Generation parameters
            llm_provider: LLM provider instance

        Returns:
            Generation result
        """
        logger.info(
            "workflow_execution_started",
            workflow_name=self.workflow_name,
            question_type=self.question_type.value,
            quiz_id=str(quiz_id),
            target_questions=generation_parameters.target_count,
            content_chunks=len(content_chunks),
        )

        try:
            # Build initial state
            initial_state: WorkflowState = {
                "quiz_id": quiz_id,
                "question_type": self.question_type,
                "target_question_count": generation_parameters.target_count,
                "content_chunks": content_chunks,
                "generation_parameters": generation_parameters,
                "llm_provider": llm_provider,
                "current_chunk_index": 0,
                "questions_generated": 0,
                "generated_questions": [],
                "error_message": None,
                "workflow_metadata": {
                    "workflow_name": self.workflow_name,
                    "started_at": str(quiz_id),  # Will be replaced with timestamp
                },
            }

            # Get and compile workflow
            workflow = self.get_workflow()
            app = workflow.compile()

            # Execute workflow
            final_state = await app.ainvoke(initial_state)

            # Build result
            result = GenerationResult(
                success=final_state.get("error_message") is None,
                questions_generated=final_state.get("questions_generated", 0),
                target_questions=generation_parameters.target_count,
                error_message=final_state.get("error_message"),
                metadata={
                    "workflow_name": self.workflow_name,
                    "question_type": self.question_type.value,
                    "content_chunks_processed": final_state.get(
                        "current_chunk_index", 0
                    ),
                    "total_content_chunks": len(content_chunks),
                    **final_state.get("workflow_metadata", {}),
                },
            )

            logger.info(
                "workflow_execution_completed",
                workflow_name=self.workflow_name,
                quiz_id=str(quiz_id),
                success=result.success,
                questions_generated=result.questions_generated,
                target_questions=result.target_questions,
            )

            return result

        except Exception as e:
            logger.error(
                "workflow_execution_failed",
                workflow_name=self.workflow_name,
                quiz_id=str(quiz_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

            return GenerationResult(
                success=False,
                questions_generated=0,
                target_questions=generation_parameters.target_count,
                error_message=f"Workflow execution failed: {str(e)}",
                metadata={
                    "workflow_name": self.workflow_name,
                    "question_type": self.question_type.value,
                    "error_type": type(e).__name__,
                },
            )

    def chunk_content(self, content_dict: dict[str, Any]) -> list[ContentChunk]:
        """
        Split content into manageable chunks.

        Args:
            content_dict: Content dictionary from quiz

        Returns:
            List of content chunks
        """
        chunks = []

        for module_id, pages in content_dict.items():
            if not isinstance(pages, list):
                continue

            for page in pages:
                if not isinstance(page, dict):
                    continue

                page_content = page.get("content", "")
                if (
                    not page_content
                    or len(page_content.strip()) < self.configuration.min_chunk_size
                ):
                    continue

                # Split long content into chunks
                if len(page_content) <= self.configuration.max_chunk_size:
                    chunks.append(
                        ContentChunk(
                            content=page_content,
                            source=f"{module_id}/{page.get('id', 'unknown')}",
                            metadata={
                                "module_id": module_id,
                                "page_id": page.get("id"),
                                "page_title": page.get("title", ""),
                            },
                        )
                    )
                else:
                    # Split by paragraphs first, then by sentences if needed
                    paragraphs = page_content.split("\n\n")
                    current_chunk = ""

                    for paragraph in paragraphs:
                        if (
                            len(current_chunk) + len(paragraph)
                            <= self.configuration.max_chunk_size
                        ):
                            current_chunk += paragraph + "\n\n"
                        else:
                            if (
                                current_chunk.strip()
                                and len(current_chunk.strip())
                                >= self.configuration.min_chunk_size
                            ):
                                chunks.append(
                                    ContentChunk(
                                        content=current_chunk.strip(),
                                        source=f"{module_id}/{page.get('id', 'unknown')}",
                                        metadata={
                                            "module_id": module_id,
                                            "page_id": page.get("id"),
                                            "page_title": page.get("title", ""),
                                            "chunk_type": "split",
                                        },
                                    )
                                )
                            current_chunk = paragraph + "\n\n"

                    if (
                        current_chunk.strip()
                        and len(current_chunk.strip())
                        >= self.configuration.min_chunk_size
                    ):
                        chunks.append(
                            ContentChunk(
                                content=current_chunk.strip(),
                                source=f"{module_id}/{page.get('id', 'unknown')}",
                                metadata={
                                    "module_id": module_id,
                                    "page_id": page.get("id"),
                                    "page_title": page.get("title", ""),
                                    "chunk_type": "split",
                                },
                            )
                        )

        logger.info(
            "content_chunking_completed",
            question_type=self.question_type.value,
            total_chunks=len(chunks),
            avg_chunk_size=sum(chunk.get_character_count() for chunk in chunks)
            // len(chunks)
            if chunks
            else 0,
            avg_word_count=sum(chunk.get_word_count() for chunk in chunks)
            // len(chunks)
            if chunks
            else 0,
        )

        return chunks

    async def create_generation_messages(
        self, content_chunk: str, generation_parameters: GenerationParameters
    ) -> list[LLMMessage]:
        """
        Create messages for LLM generation.

        Args:
            content_chunk: Content to generate questions from
            generation_parameters: Generation parameters

        Returns:
            List of messages for LLM
        """
        messages: list[LLMMessage]
        if self.template_manager:
            # Use template manager if available
            messages = await self.template_manager.create_messages(
                self.question_type,
                content_chunk,
                generation_parameters,
                language=generation_parameters.language,
            )
        else:
            # Fallback to default implementation
            messages = self._create_default_messages(
                content_chunk, generation_parameters
            )
        return messages

    @abstractmethod
    def _create_default_messages(
        self, content_chunk: str, generation_parameters: GenerationParameters
    ) -> list[LLMMessage]:
        """
        Create default messages for LLM generation.

        Args:
            content_chunk: Content to generate questions from
            generation_parameters: Generation parameters

        Returns:
            List of messages for LLM
        """
        pass
