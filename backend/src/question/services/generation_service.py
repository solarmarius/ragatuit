"""Module-based question generation service."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session

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
            from src.quiz.models import Quiz

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
                    question_type=quiz.question_type,  # Pass quiz's question type
                )

                results = await processor.process_all_modules(quiz_id, modules_data)

                # Calculate total generated questions for logging (but don't update quiz.question_count)
                total_generated = sum(len(questions) for questions in results.values())

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

    async def generate_questions_for_quiz_with_batch_tracking(
        self,
        quiz_id: UUID,
        extracted_content: dict[str, str],
        provider_name: str = "openai",
    ) -> dict[str, list[Any]]:
        """
        Generate questions for quiz with batch-level tracking and selective retry support.

        This method checks existing generation metadata to skip successfully completed batches
        and only process modules that need generation or retry.

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
            # Get quiz to access module configuration and metadata
            from src.quiz.models import Quiz

            async with get_async_session() as session:
                quiz = await session.get(Quiz, quiz_id)
                if not quiz:
                    raise ValueError(f"Quiz {quiz_id} not found")

                # Check generation metadata for successful batches to skip
                successful_batch_keys = set()
                if (
                    quiz.generation_metadata
                    and "successful_batches" in quiz.generation_metadata
                ):
                    successful_batch_keys = set(
                        quiz.generation_metadata["successful_batches"]
                    )

                logger.info(
                    "batch_tracking_generation_started",
                    quiz_id=str(quiz_id),
                    total_modules=len(quiz.selected_modules),
                    successful_batches_to_skip=len(successful_batch_keys),
                    provider=provider_name,
                )

                # Get provider instance
                from ..providers import LLMProvider

                provider_enum = LLMProvider(provider_name.lower())
                provider = self.provider_registry.get_provider(provider_enum)

                # Filter modules to only process those that need generation
                modules_to_process = {}
                skipped_modules = []

                for module_id, module_info in quiz.selected_modules.items():
                    # Create batch key for this module
                    batch_key = f"{module_id}_{quiz.question_type.value}_{module_info['question_count']}"

                    if batch_key in successful_batch_keys:
                        # Skip this module - it already has successful batch
                        skipped_modules.append(
                            {
                                "module_id": module_id,
                                "module_name": module_info.get("name", "Unknown"),
                                "batch_key": batch_key,
                                "reason": "already_successful",
                            }
                        )
                        logger.debug(
                            "batch_tracking_skipping_successful_module",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            batch_key=batch_key,
                        )
                        continue

                    # Check if we have content for this module
                    if module_id in extracted_content:
                        modules_to_process[module_id] = {
                            "name": module_info["name"],
                            "content": extracted_content[module_id],
                            "question_count": module_info["question_count"],
                        }
                        logger.debug(
                            "batch_tracking_module_needs_processing",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            batch_key=batch_key,
                            question_count=module_info["question_count"],
                        )
                    else:
                        logger.warning(
                            "batch_tracking_module_content_missing",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            module_name=module_info.get("name", "unknown"),
                        )

                logger.info(
                    "batch_tracking_modules_filtered",
                    quiz_id=str(quiz_id),
                    modules_to_process=len(modules_to_process),
                    modules_skipped=len(skipped_modules),
                    skipped_details=skipped_modules,
                )

                # If no modules need processing, return empty results
                if not modules_to_process:
                    logger.info(
                        "batch_tracking_no_modules_to_process",
                        quiz_id=str(quiz_id),
                        reason="all_batches_already_successful_or_no_content",
                    )
                    return {}

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

                results = await processor.process_all_modules(
                    quiz_id, modules_to_process
                )

                # Calculate total generated questions for logging
                total_generated = sum(len(questions) for questions in results.values())

                logger.info(
                    "batch_tracking_generation_completed",
                    quiz_id=str(quiz_id),
                    total_questions=total_generated,
                    modules_processed=len(results),
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

    async def get_generation_status(self, quiz_id: UUID) -> dict[str, Any]:
        """
        Get generation status for a quiz.

        Args:
            quiz_id: Quiz identifier

        Returns:
            Dictionary with generation status information
        """
        try:
            from src.quiz.models import Quiz

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
