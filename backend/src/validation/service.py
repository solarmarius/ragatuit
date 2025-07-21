"""RAGAS validation service for question quality assessment."""

from typing import Any

from ragas.dataset_schema import SingleTurnSample  # type: ignore
from ragas.embeddings import LangchainEmbeddingsWrapper  # type: ignore
from ragas.metrics import Faithfulness, SemanticSimilarity  # type: ignore

from src.config import get_logger, settings
from src.question.providers import BaseLLMProvider
from src.question.types import Question
from src.question.types.registry import get_question_type_registry

from .adapters import RAGASLLMAdapter

logger = get_logger("validation_service")


class ValidationService:
    """Service for validating questions using RAGAS metrics."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
        self.llm_adapter = RAGASLLMAdapter(llm_provider)
        self.question_registry = get_question_type_registry()

        # Initialize RAGAS metrics with required components
        self.faithfulness_scorer = Faithfulness(llm=self.llm_adapter)
        self.semantic_similarity_scorer = SemanticSimilarity(
            embeddings=LangchainEmbeddingsWrapper(self._get_embedding_model())
        )

    async def evaluate_question_async(
        self, question: Question, context: str
    ) -> dict[str, Any]:
        """Async wrapper for RAGAS evaluation."""
        try:
            result = await self._evaluate_question_async_internal(question, context)
            return result
        except Exception as e:
            logger.error(f"RAGAS evaluation failed for question {question.id}: {e}")
            # Return low scores on error to flag for manual review
            return {
                "faithfulness_score": 0.0,
                "semantic_similarity_score": 0.0,
                "error": str(e),
            }

    async def _evaluate_question_async_internal(
        self, question: Question, context: str
    ) -> dict[str, Any]:
        """Internal async RAGAS evaluation delegating to question types."""
        try:
            # Get question type implementation from registry
            question_type_impl = self.question_registry.get_question_type(
                question.question_type
            )
            if not question_type_impl:
                logger.error(f"Unknown question type: {question.question_type}")
                return {
                    "faithfulness_score": 0.0,
                    "semantic_similarity_score": 0.0,
                    "error": f"Unknown question type: {question.question_type}",
                }

            # Parse and validate question data using question type's own validation
            question_data = question_type_impl.validate_data(question.question_data)

            # Extract question text and answer for faithfulness evaluation
            question_text = question_data.question_text
            answer_text = self._extract_correct_answer_from_data(
                question_data, question_type_impl
            )

            # Always evaluate faithfulness (applies to all question types)
            faithfulness_sample = SingleTurnSample(
                user_input=question_text,  # The question being asked
                response=answer_text,  # The correct answer
                retrieved_contexts=[context],  # Source content from Canvas modules
            )
            faithfulness_score = await self.faithfulness_scorer.single_turn_ascore(
                faithfulness_sample
            )

            # Delegate semantic similarity evaluation to question type implementation
            semantic_similarity_score = (
                await question_type_impl.evaluate_semantic_similarity_async(
                    question_data=question_data,
                    semantic_similarity_scorer=self.semantic_similarity_scorer,
                    logger=logger,
                )
            )

            return {
                "faithfulness_score": float(faithfulness_score),
                "semantic_similarity_score": float(semantic_similarity_score),
            }
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            raise

    def _extract_correct_answer_from_data(
        self, question_data: Any, question_type_impl: Any
    ) -> str:
        """Extract correct answer text from validated question data."""
        try:
            if hasattr(question_data, "correct_answer"):
                # MCQ pattern: get correct answer option text
                correct_option = question_data.correct_answer
                option_key = f"option_{correct_option.lower()}"
                if hasattr(question_data, option_key):
                    return str(getattr(question_data, option_key))
            elif hasattr(question_data, "blanks") and question_data.blanks:
                # Fill-in-blank pattern: use first blank's correct answer
                return str(question_data.blanks[0].correct_answer)

            logger.warning("Could not extract correct answer from question data")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract correct answer: {e}")
            return ""

    def passes_validation(self, scores: dict[str, Any]) -> bool:
        """Check if validation scores meet the configured thresholds."""
        if "error" in scores:
            return False

        faithfulness_ok = (
            scores.get("faithfulness_score", 0.0)
            >= settings.RAGAS_FAITHFULNESS_THRESHOLD
        )
        similarity_ok = (
            scores.get("semantic_similarity_score", 0.0)
            >= settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD
        )

        return bool(faithfulness_ok and similarity_ok)

    def _get_embedding_model(self) -> Any:
        """Get embedding model for semantic similarity evaluation."""
        # This would typically use OpenAI embeddings or similar
        # Implementation depends on available embedding models in the system
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings()
