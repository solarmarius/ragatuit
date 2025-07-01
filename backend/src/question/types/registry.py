"""Question type registry for dynamic type discovery and management."""

from src.logging_config import get_logger

from .base import BaseQuestionType, QuestionType

logger = get_logger("question_type_registry")


class QuestionTypeRegistry:
    """
    Registry for question type implementations.

    Provides centralized management of question types with dynamic discovery,
    validation, and factory capabilities.
    """

    def __init__(self) -> None:
        self._question_types: dict[QuestionType, BaseQuestionType] = {}
        self._initialized = False

    def register_question_type(
        self, question_type: QuestionType, implementation: BaseQuestionType
    ) -> None:
        """
        Register a question type implementation.

        Args:
            question_type: The question type enum
            implementation: The question type implementation instance

        Raises:
            ValueError: If question type is already registered or implementation is invalid
        """
        if question_type in self._question_types:
            raise ValueError(f"Question type {question_type} is already registered")

        # Validate the implementation
        if not isinstance(implementation, BaseQuestionType):
            raise ValueError("Implementation must inherit from BaseQuestionType")

        if implementation.question_type != question_type:
            raise ValueError(
                f"Implementation question_type {implementation.question_type} "
                f"does not match registered type {question_type}"
            )

        self._question_types[question_type] = implementation

        logger.info(
            "question_type_registered",
            question_type=question_type.value,
            implementation_class=implementation.__class__.__name__,
        )

    def get_question_type(self, question_type: QuestionType) -> BaseQuestionType:
        """
        Get a question type implementation.

        Args:
            question_type: The question type to retrieve

        Returns:
            The question type implementation

        Raises:
            ValueError: If question type is not registered
        """
        if not self._initialized:
            self._initialize_default_types()

        if question_type not in self._question_types:
            raise ValueError(f"Question type {question_type} is not registered")

        return self._question_types[question_type]

    def get_available_types(self) -> list[QuestionType]:
        """
        Get list of all available question types.

        Returns:
            List of registered question types
        """
        if not self._initialized:
            self._initialize_default_types()

        return list(self._question_types.keys())

    def is_registered(self, question_type: QuestionType) -> bool:
        """
        Check if a question type is registered.

        Args:
            question_type: The question type to check

        Returns:
            True if registered, False otherwise
        """
        if not self._initialized:
            self._initialize_default_types()

        return question_type in self._question_types

    def unregister_question_type(self, question_type: QuestionType) -> None:
        """
        Unregister a question type.

        Args:
            question_type: The question type to unregister

        Raises:
            ValueError: If question type is not registered
        """
        if question_type not in self._question_types:
            raise ValueError(f"Question type {question_type} is not registered")

        del self._question_types[question_type]

        logger.info("question_type_unregistered", question_type=question_type.value)

    def _initialize_default_types(self) -> None:
        """Initialize the registry with default question type implementations."""
        if self._initialized:
            return

        try:
            # Import and register default question types
            from .mcq import MultipleChoiceQuestionType

            self.register_question_type(
                QuestionType.MULTIPLE_CHOICE, MultipleChoiceQuestionType()
            )

            logger.info(
                "question_type_registry_initialized",
                registered_types=len(self._question_types),
            )

        except ImportError as e:
            logger.error(
                "failed_to_initialize_default_question_types",
                error=str(e),
                exc_info=True,
            )
            # Continue with empty registry rather than failing

        self._initialized = True


# Global registry instance
question_type_registry = QuestionTypeRegistry()


def get_question_type_registry() -> QuestionTypeRegistry:
    """Get the global question type registry instance."""
    return question_type_registry
