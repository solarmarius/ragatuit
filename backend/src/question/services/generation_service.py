"""Generation orchestration service for question generation workflows."""

from typing import Any
from uuid import UUID

from src.config import get_logger

from ..config import get_configuration_service
from ..providers import get_llm_provider_registry
from ..templates import get_template_manager
from ..types import GenerationParameters, GenerationResult, QuestionType
from ..workflows import get_workflow_registry
from .content_service import ContentProcessingService

logger = get_logger("generation_service")


class GenerationOrchestrationService:
    """
    Service for orchestrating question generation workflows.

    Coordinates content processing, provider selection, workflow execution,
    and result aggregation for question generation.
    """

    def __init__(self) -> None:
        """Initialize generation orchestration service."""
        self.config_service = get_configuration_service()
        self.provider_registry = get_llm_provider_registry()
        self.workflow_registry = get_workflow_registry()
        self.template_manager = get_template_manager()

    async def generate_questions(
        self,
        quiz_id: UUID,
        question_type: QuestionType,
        generation_parameters: GenerationParameters,
        provider_name: str | None = None,
        workflow_name: str | None = None,
        template_name: str | None = None,
    ) -> GenerationResult:
        """
        Generate questions for a quiz using specified parameters.

        Args:
            quiz_id: Quiz identifier
            question_type: Type of questions to generate
            generation_parameters: Generation parameters
            provider_name: LLM provider to use (uses default if None)
            workflow_name: Workflow to use (uses default if None)
            template_name: Template to use (uses default if None)

        Returns:
            Generation result
        """
        logger.info(
            "question_generation_started",
            quiz_id=str(quiz_id),
            question_type=question_type.value,
            target_count=generation_parameters.target_count,
            provider_name=provider_name,
            workflow_name=workflow_name,
            template_name=template_name,
        )

        try:
            # Validate inputs
            self._validate_generation_request(question_type, generation_parameters)

            # Get configurations
            config = self.config_service.get_config()
            provider_config = self.config_service.get_provider_config(
                self.provider_registry.get_available_providers()[0]
                if provider_name is None
                else getattr(self.provider_registry, provider_name, None)
            )
            workflow_config = self.config_service.get_workflow_config(question_type)

            # Prepare content
            content_service = ContentProcessingService(workflow_config)
            content_chunks = await content_service.prepare_content_for_generation(
                quiz_id
            )

            if not content_chunks:
                return GenerationResult(
                    success=False,
                    questions_generated=0,
                    target_questions=generation_parameters.target_count,
                    error_message="No valid content chunks found for generation",
                    metadata={
                        "quiz_id": str(quiz_id),
                        "question_type": question_type.value,
                        "content_chunks": 0,
                    },
                )

            # Apply quality filtering if enabled
            if config.enable_duplicate_detection:
                content_chunks = content_service.validate_content_quality(
                    content_chunks
                )

            # Get content statistics
            content_stats = content_service.get_content_statistics(content_chunks)

            logger.info(
                "content_preparation_completed",
                quiz_id=str(quiz_id),
                question_type=question_type.value,
                content_chunks=len(content_chunks),
                total_characters=content_stats["total_characters"],
                avg_chunk_size=content_stats["avg_chunk_size"],
            )

            # Get provider instance
            provider = self.provider_registry.get_provider(
                provider_config.provider, provider_config
            )

            # Get workflow instance
            workflow = self.workflow_registry.get_workflow(
                question_type, workflow_config, self.template_manager
            )

            # Convert chunks to strings for workflow compatibility
            chunk_strings = [chunk.content for chunk in content_chunks]

            # Execute workflow
            result = await workflow.execute(
                quiz_id=quiz_id,
                content_chunks=chunk_strings,
                generation_parameters=generation_parameters,
                llm_provider=provider,
            )

            # Enhance result with additional metadata
            result.metadata.update(
                {
                    "provider_used": provider_config.provider.value,
                    "model_used": provider_config.model,
                    "workflow_used": workflow.workflow_name,
                    "template_used": template_name,
                    "content_statistics": content_stats,
                    "generation_config": {
                        "temperature": provider_config.temperature,
                        "max_retries": provider_config.max_retries,
                        "chunk_size": workflow_config.max_chunk_size,
                        "quality_threshold": workflow_config.quality_threshold,
                    },
                }
            )

            logger.info(
                "question_generation_completed",
                quiz_id=str(quiz_id),
                question_type=question_type.value,
                success=result.success,
                questions_generated=result.questions_generated,
                target_questions=result.target_questions,
                provider=provider_config.provider.value,
                workflow=workflow.workflow_name,
            )

            return result

        except Exception as e:
            logger.error(
                "question_generation_failed",
                quiz_id=str(quiz_id),
                question_type=question_type.value,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )

            return GenerationResult(
                success=False,
                questions_generated=0,
                target_questions=generation_parameters.target_count,
                error_message=f"Generation failed: {str(e)}",
                metadata={
                    "quiz_id": str(quiz_id),
                    "question_type": question_type.value,
                    "error_type": type(e).__name__,
                    "provider_name": provider_name,
                    "workflow_name": workflow_name,
                },
            )

    async def batch_generate_questions(
        self, requests: list[dict[str, Any]]
    ) -> list[GenerationResult]:
        """
        Generate questions for multiple requests in batch.

        Args:
            requests: List of generation request dictionaries

        Returns:
            List of generation results
        """
        logger.info("batch_generation_started", request_count=len(requests))

        results = []

        for i, request in enumerate(requests):
            try:
                # Extract parameters from request
                quiz_id = UUID(request["quiz_id"])
                question_type = QuestionType(request["question_type"])
                generation_parameters = GenerationParameters(
                    **request["generation_parameters"]
                )

                # Optional parameters
                provider_name = request.get("provider_name")
                workflow_name = request.get("workflow_name")
                template_name = request.get("template_name")

                # Generate questions
                result = await self.generate_questions(
                    quiz_id=quiz_id,
                    question_type=question_type,
                    generation_parameters=generation_parameters,
                    provider_name=provider_name,
                    workflow_name=workflow_name,
                    template_name=template_name,
                )

                results.append(result)

                logger.debug(
                    "batch_request_completed",
                    request_index=i,
                    quiz_id=str(quiz_id),
                    success=result.success,
                    questions_generated=result.questions_generated,
                )

            except Exception as e:
                logger.error(
                    "batch_request_failed",
                    request_index=i,
                    request=request,
                    error=str(e),
                    exc_info=True,
                )

                # Create error result
                error_result = GenerationResult(
                    success=False,
                    questions_generated=0,
                    target_questions=request.get("generation_parameters", {}).get(
                        "target_count", 0
                    ),
                    error_message=f"Batch request failed: {str(e)}",
                    metadata={"request_index": i, "error_type": type(e).__name__},
                )
                results.append(error_result)

        successful_requests = sum(1 for r in results if r.success)
        total_questions = sum(r.questions_generated for r in results)

        logger.info(
            "batch_generation_completed",
            total_requests=len(requests),
            successful_requests=successful_requests,
            failed_requests=len(requests) - successful_requests,
            total_questions_generated=total_questions,
        )

        return results

    def get_generation_capabilities(self) -> dict[str, Any]:
        """
        Get information about generation capabilities.

        Returns:
            Dictionary with capability information
        """
        available_providers = self.provider_registry.get_available_providers()
        available_question_types = self.workflow_registry.get_available_question_types()
        available_templates = self.template_manager.list_templates()

        return {
            "providers": [
                {
                    "name": provider.value,
                    "available": self.provider_registry.is_registered(provider),
                }
                for provider in available_providers
            ],
            "question_types": [
                {"type": qt.value, "supported": self.workflow_registry.is_supported(qt)}
                for qt in available_question_types
            ],
            "templates": [
                {
                    "name": template.name,
                    "question_type": template.question_type.value,
                    "version": template.version,
                    "description": template.description,
                }
                for template in available_templates
            ],
            "configuration": self.config_service.get_configuration_summary(),
        }

    async def validate_generation_setup(
        self, question_type: QuestionType, provider_name: str | None = None
    ) -> dict[str, Any]:
        """
        Validate that generation setup is working correctly.

        Args:
            question_type: Question type to validate
            provider_name: Provider to validate (uses default if None)

        Returns:
            Validation results
        """
        logger.info(
            "generation_setup_validation_started",
            question_type=question_type.value,
            provider_name=provider_name,
        )

        validation_results: dict[str, Any] = {
            "overall_status": "unknown",
            "question_type_supported": False,
            "provider_available": False,
            "workflow_available": False,
            "template_available": False,
            "provider_health": False,
            "errors": [],
        }

        try:
            # Check question type support
            validation_results["question_type_supported"] = (
                self.workflow_registry.is_supported(question_type)
            )
            if not validation_results["question_type_supported"]:
                validation_results["errors"].append(
                    f"Question type {question_type.value} is not supported"
                )

            # Check provider availability
            config = self.config_service.get_config()
            self.config_service.get_provider_config()  # Check if provider is available

            if provider_name:
                # Check specific provider
                from ..providers import LLMProvider

                try:
                    provider_enum = LLMProvider(provider_name)
                    validation_results["provider_available"] = (
                        self.provider_registry.is_registered(provider_enum)
                    )
                    if validation_results["provider_available"]:
                        # Test provider health
                        validation_results[
                            "provider_health"
                        ] = await self.provider_registry.health_check(provider_enum)
                except ValueError:
                    validation_results["errors"].append(
                        f"Invalid provider name: {provider_name}"
                    )
            else:
                # Check default provider
                validation_results["provider_available"] = (
                    self.provider_registry.is_registered(config.default_provider)
                )
                if validation_results["provider_available"]:
                    validation_results[
                        "provider_health"
                    ] = await self.provider_registry.health_check(
                        config.default_provider
                    )

            if not validation_results["provider_available"]:
                validation_results["errors"].append(
                    "No available LLM provider configured"
                )
            elif not validation_results["provider_health"]:
                validation_results["errors"].append("LLM provider health check failed")

            # Check workflow availability
            validation_results["workflow_available"] = (
                self.workflow_registry.is_supported(question_type)
            )
            if not validation_results["workflow_available"]:
                validation_results["errors"].append(
                    f"No workflow available for question type {question_type.value}"
                )

            # Check template availability
            try:
                self.template_manager.get_template(
                    question_type
                )  # Check if template exists
                validation_results["template_available"] = True
            except ValueError:
                validation_results["errors"].append(
                    f"No template available for question type {question_type.value}"
                )
                validation_results["template_available"] = False

            # Determine overall status
            if all(
                [
                    validation_results["question_type_supported"],
                    validation_results["provider_available"],
                    validation_results["workflow_available"],
                    validation_results["template_available"],
                    validation_results["provider_health"],
                ]
            ):
                validation_results["overall_status"] = "ready"
            elif validation_results["errors"]:
                validation_results["overall_status"] = "error"
            else:
                validation_results["overall_status"] = "partial"

            logger.info(
                "generation_setup_validation_completed",
                question_type=question_type.value,
                provider_name=provider_name,
                overall_status=validation_results["overall_status"],
                errors_count=len(validation_results["errors"]),
            )

        except Exception as e:
            logger.error(
                "generation_setup_validation_failed",
                question_type=question_type.value,
                provider_name=provider_name,
                error=str(e),
                exc_info=True,
            )

            validation_results["overall_status"] = "error"
            validation_results["errors"].append(f"Validation failed: {str(e)}")

        return validation_results

    def _validate_generation_request(
        self, question_type: QuestionType, generation_parameters: GenerationParameters
    ) -> None:
        """
        Validate generation request parameters.

        Args:
            question_type: Question type to validate
            generation_parameters: Generation parameters to validate

        Raises:
            ValueError: If request is invalid
        """
        # Check if question type is supported
        if not self.workflow_registry.is_supported(question_type):
            raise ValueError(f"Question type {question_type.value} is not supported")

        # Validate generation parameters
        if generation_parameters.target_count <= 0:
            raise ValueError("Target question count must be positive")

        if generation_parameters.target_count > 100:
            raise ValueError("Target question count cannot exceed 100")

        # Check configuration limits
        config = self.config_service.get_config()

        if generation_parameters.target_count > config.max_concurrent_generations * 10:
            raise ValueError(
                f"Target question count exceeds system limits "
                f"(max: {config.max_concurrent_generations * 10})"
            )
