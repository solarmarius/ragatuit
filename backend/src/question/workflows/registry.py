"""Workflow registry for managing question generation workflows."""

from typing import Any

from src.logging_config import get_logger

from ..types import QuestionType
from .base import BaseQuestionWorkflow, WorkflowConfiguration

logger = get_logger("workflow_registry")


class WorkflowRegistry:
    """
    Registry for question generation workflow implementations.

    Manages workflow classes and provides factory methods for creating
    workflow instances for different question types.
    """

    def __init__(self) -> None:
        self._workflows: dict[QuestionType, type[BaseQuestionWorkflow]] = {}
        self._default_configurations: dict[QuestionType, WorkflowConfiguration] = {}
        self._initialized = False

    def register_workflow(
        self,
        question_type: QuestionType,
        workflow_class: type[BaseQuestionWorkflow],
        default_config: WorkflowConfiguration | None = None,
    ) -> None:
        """
        Register a workflow implementation for a question type.

        Args:
            question_type: The question type this workflow handles
            workflow_class: The workflow implementation class
            default_config: Default configuration for the workflow

        Raises:
            ValueError: If question type already has a workflow or class is invalid
        """
        if question_type in self._workflows:
            raise ValueError(
                f"Workflow for question type {question_type} is already registered"
            )

        if not issubclass(workflow_class, BaseQuestionWorkflow):
            raise ValueError("Workflow class must inherit from BaseQuestionWorkflow")

        self._workflows[question_type] = workflow_class

        if default_config:
            self._default_configurations[question_type] = default_config

        logger.info(
            "workflow_registered",
            question_type=question_type.value,
            workflow_class=workflow_class.__name__,
            has_default_config=default_config is not None,
        )

    def get_workflow(
        self,
        question_type: QuestionType,
        configuration: WorkflowConfiguration | None = None,
        template_manager: Any | None = None,
    ) -> BaseQuestionWorkflow:
        """
        Create a workflow instance for a question type.

        Args:
            question_type: The question type
            configuration: Workflow configuration, uses default if None
            template_manager: Optional template manager

        Returns:
            Workflow instance

        Raises:
            ValueError: If question type has no registered workflow
        """
        if not self._initialized:
            self._initialize_default_workflows()

        if question_type not in self._workflows:
            raise ValueError(
                f"No workflow registered for question type {question_type}"
            )

        # Use provided configuration or default
        if configuration is None:
            if question_type in self._default_configurations:
                configuration = self._default_configurations[question_type]
            else:
                # Use basic default configuration
                configuration = WorkflowConfiguration()

        workflow_class = self._workflows[question_type]
        return workflow_class(question_type, configuration, template_manager)

    def get_available_question_types(self) -> list[QuestionType]:
        """
        Get list of question types that have registered workflows.

        Returns:
            List of supported question types
        """
        if not self._initialized:
            self._initialize_default_workflows()

        return list(self._workflows.keys())

    def is_supported(self, question_type: QuestionType) -> bool:
        """
        Check if a question type has a registered workflow.

        Args:
            question_type: The question type to check

        Returns:
            True if supported, False otherwise
        """
        if not self._initialized:
            self._initialize_default_workflows()

        return question_type in self._workflows

    def get_default_configuration(
        self, question_type: QuestionType
    ) -> WorkflowConfiguration | None:
        """
        Get default configuration for a question type.

        Args:
            question_type: The question type

        Returns:
            Default configuration or None if not available
        """
        return self._default_configurations.get(question_type)

    def set_default_configuration(
        self, question_type: QuestionType, configuration: WorkflowConfiguration
    ) -> None:
        """
        Set default configuration for a question type.

        Args:
            question_type: The question type
            configuration: The default configuration

        Raises:
            ValueError: If question type has no registered workflow
        """
        if question_type not in self._workflows:
            raise ValueError(
                f"No workflow registered for question type {question_type}"
            )

        self._default_configurations[question_type] = configuration

        logger.info(
            "default_workflow_configuration_updated",
            question_type=question_type.value,
            max_chunk_size=configuration.max_chunk_size,
            max_questions_per_chunk=configuration.max_questions_per_chunk,
        )

    def get_workflow_info(self, question_type: QuestionType) -> dict[str, Any]:
        """
        Get information about a registered workflow.

        Args:
            question_type: The question type

        Returns:
            Workflow information dictionary

        Raises:
            ValueError: If question type has no registered workflow
        """
        if not self.is_supported(question_type):
            raise ValueError(
                f"No workflow registered for question type {question_type}"
            )

        workflow_class = self._workflows[question_type]
        default_config = self._default_configurations.get(question_type)

        return {
            "question_type": question_type.value,
            "workflow_class": workflow_class.__name__,
            "workflow_module": workflow_class.__module__,
            "has_default_config": default_config is not None,
            "default_config": default_config.dict() if default_config else None,
        }

    def list_all_workflows(self) -> list[dict[str, Any]]:
        """
        Get information about all registered workflows.

        Returns:
            List of workflow information dictionaries
        """
        if not self._initialized:
            self._initialize_default_workflows()

        return [
            self.get_workflow_info(question_type)
            for question_type in self._workflows.keys()
        ]

    def unregister_workflow(self, question_type: QuestionType) -> None:
        """
        Unregister a workflow for a question type.

        Args:
            question_type: The question type

        Raises:
            ValueError: If question type has no registered workflow
        """
        if question_type not in self._workflows:
            raise ValueError(
                f"No workflow registered for question type {question_type}"
            )

        del self._workflows[question_type]

        if question_type in self._default_configurations:
            del self._default_configurations[question_type]

        logger.info("workflow_unregistered", question_type=question_type.value)

    def _initialize_default_workflows(self) -> None:
        """Initialize the registry with default workflow implementations."""
        if self._initialized:
            return

        try:
            # Import and register default workflows
            from .mcq_workflow import MCQWorkflow

            # Register MCQ workflow with default configuration
            mcq_config = WorkflowConfiguration(
                max_chunk_size=3000,
                min_chunk_size=100,
                max_questions_per_chunk=1,  # MCQ generates one question per chunk
                allow_duplicate_detection=True,
                quality_threshold=0.8,
                max_generation_retries=3,
                type_specific_settings={
                    "enforce_unique_correct_answers": True,
                    "require_plausible_distractors": True,
                    "min_option_length": 10,
                    "max_option_length": 200,
                },
            )

            self.register_workflow(
                QuestionType.MULTIPLE_CHOICE, MCQWorkflow, mcq_config
            )

            logger.info(
                "workflow_registry_initialized",
                registered_workflows=len(self._workflows),
            )

        except ImportError as e:
            logger.error(
                "failed_to_initialize_default_workflows", error=str(e), exc_info=True
            )
            # Continue with empty registry rather than failing

        self._initialized = True


# Global registry instance
workflow_registry = WorkflowRegistry()


def get_workflow_registry() -> WorkflowRegistry:
    """Get the global workflow registry instance."""
    return workflow_registry
