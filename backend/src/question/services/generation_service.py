"""Module-based question generation service."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session

from ..providers import get_llm_provider_registry
from ..templates import get_template_manager
from ..types import QuestionType, QuizLanguage
from ..workflows.module_batch_workflow import ParallelModuleProcessor

logger = get_logger("generation_service")


class QuestionGenerationService:
    """Service for orchestrating module-based question generation."""

    def __init__(self) -> None:
        """Initialize question generation service."""
        self.provider_registry = get_llm_provider_registry()
        self.template_manager = get_template_manager()

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

                # Build modules to process with their batches
                modules_to_process = {}
                skipped_batches = []
                total_batches_to_process = 0

                for module_id, module_info in quiz.selected_modules.items():
                    module_name = module_info.get("name", "Unknown")

                    # Skip if no content extracted for this module
                    if module_id not in extracted_content:
                        logger.warning(
                            "batch_tracking_module_content_missing",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            module_name=module_name,
                        )
                        continue

                    # Process each batch in the module
                    batches_to_process = []
                    for batch in module_info.get("question_batches", []):
                        question_type = batch["question_type"]
                        count = batch["count"]

                        # Create batch key
                        batch_key = f"{module_id}_{question_type}_{count}"

                        if batch_key in successful_batch_keys:
                            # Skip this batch - already successful
                            skipped_batches.append(
                                {
                                    "module_id": module_id,
                                    "module_name": module_name,
                                    "batch_key": batch_key,
                                    "question_type": question_type,
                                    "count": count,
                                    "reason": "already_successful",
                                }
                            )
                            logger.debug(
                                "batch_tracking_skipping_successful_batch",
                                quiz_id=str(quiz_id),
                                batch_key=batch_key,
                            )
                        else:
                            # Add to processing list
                            batches_to_process.append(
                                {
                                    "question_type": QuestionType(question_type),
                                    "count": count,
                                    "batch_key": batch_key,
                                }
                            )
                            total_batches_to_process += 1

                    # Only add module if it has batches to process
                    if batches_to_process:
                        modules_to_process[module_id] = {
                            "name": module_name,
                            "content": extracted_content[module_id],
                            "batches": batches_to_process,
                        }

                logger.info(
                    "batch_tracking_modules_filtered",
                    quiz_id=str(quiz_id),
                    modules_to_process=len(modules_to_process),
                    total_batches_to_process=total_batches_to_process,
                    batches_skipped=len(skipped_batches),
                    skipped_details=skipped_batches,
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

                # Process modules with their batches
                processor = ParallelModuleProcessor(
                    llm_provider=provider,
                    template_manager=self.template_manager,
                    language=language,
                )

                results = await processor.process_all_modules_with_batches(
                    quiz_id, modules_to_process
                )

                # Logging moved to the logger.info call below

                logger.info(
                    "batch_tracking_generation_completed",
                    quiz_id=str(quiz_id),
                    modules_processed=len(results),
                    total_questions_generated=sum(
                        len(questions) for questions in results.values()
                    ),
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
