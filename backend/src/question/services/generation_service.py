"""Module-based question generation service."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session
from src.quiz.models import Quiz

from ..providers import get_llm_provider_registry
from ..templates import get_template_manager
from ..types import QuizLanguage
from ..workflows.module_batch_workflow import ParallelModuleProcessor

logger = get_logger("generation_service")


class QuestionGenerationService:
    """Service for orchestrating module-based question generation."""

    def __init__(self) -> None:
        """Initialize question generation service."""
        self.provider_registry = get_llm_provider_registry()
        self.template_manager = get_template_manager()

    async def generate_questions_for_quiz(
        self,
        quiz_id: UUID,
        extracted_content: dict[str, str],
        provider_name: str = "openai",
    ) -> dict[str, list[Any]]:
        """
        Generate questions for all modules in parallel.

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
            # Get quiz to access module configuration
            async with get_async_session() as session:
                quiz = await session.get(Quiz, quiz_id)
                if not quiz:
                    raise ValueError(f"Quiz {quiz_id} not found")

                # Get provider instance
                from ..providers import LLMProvider

                provider_enum = LLMProvider(provider_name.lower())
                provider = self.provider_registry.get_provider(provider_enum)

                # Prepare module data with content and question counts
                modules_data = {}
                for module_id, module_info in quiz.selected_modules.items():
                    if module_id in extracted_content:
                        modules_data[module_id] = {
                            "name": module_info["name"],
                            "content": extracted_content[module_id],
                            "question_count": module_info["question_count"],
                        }
                    else:
                        logger.warning(
                            "module_content_missing",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            module_name=module_info.get("name", "unknown"),
                        )

                if not modules_data:
                    raise ValueError("No module content available for generation")

                # Convert language string to enum
                language = (
                    QuizLanguage.NORWEGIAN
                    if quiz.language == "no"
                    else QuizLanguage.ENGLISH
                )

                # Process all modules in parallel
                processor = ParallelModuleProcessor(
                    llm_provider=provider,
                    template_manager=self.template_manager,
                    language=language,
                )

                results = await processor.process_all_modules(quiz_id, modules_data)

                # Update quiz total question count
                total_generated = sum(len(questions) for questions in results.values())
                quiz.question_count = total_generated
                await session.commit()

                logger.info(
                    "module_generation_completed",
                    quiz_id=str(quiz_id),
                    total_questions=total_generated,
                    modules_processed=len(results),
                    successful_modules=sum(1 for q in results.values() if q),
                )

                return results

        except Exception as e:
            logger.error(
                "module_generation_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_generation_status(self, quiz_id: UUID) -> dict[str, Any]:
        """
        Get generation status for a quiz.

        Args:
            quiz_id: Quiz identifier

        Returns:
            Dictionary with generation status information
        """
        try:
            async with get_async_session() as session:
                quiz = await session.get(Quiz, quiz_id)
                if not quiz:
                    raise ValueError(f"Quiz {quiz_id} not found")

                # Get all questions for this quiz using existing service
                from .. import service

                questions = await service.get_questions_by_quiz(session, quiz_id)

                questions_by_module = {}
                for question in questions:
                    module_id = question.question_data.get("module_id", "unknown")
                    if module_id not in questions_by_module:
                        questions_by_module[module_id] = 0
                    questions_by_module[module_id] += 1

                # Calculate target vs actual
                module_targets = {
                    module_id: module_info["question_count"]
                    for module_id, module_info in quiz.selected_modules.items()
                }

                return {
                    "quiz_id": str(quiz_id),
                    "status": quiz.status.value,
                    "total_questions": len(questions),
                    "target_questions": sum(module_targets.values()),
                    "questions_by_module": questions_by_module,
                    "targets_by_module": module_targets,
                    "completion_rate": (
                        len(questions) / sum(module_targets.values())
                        if module_targets
                        else 0
                    ),
                }

        except Exception as e:
            logger.error(
                "generation_status_check_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            raise
