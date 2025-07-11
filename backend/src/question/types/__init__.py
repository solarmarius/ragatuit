"""Question types module providing polymorphic question support."""

from .base import (
    BaseQuestionData,
    BaseQuestionType,
    GenerationParameters,
    GenerationResult,
    Question,
    QuestionDifficulty,
    QuestionType,
    QuizLanguage,
)
from .mcq import MultipleChoiceData, MultipleChoiceQuestionType
from .registry import QuestionTypeRegistry, get_question_type_registry

__all__ = [
    # Base types
    "BaseQuestionData",
    "BaseQuestionType",
    "Question",
    "QuestionType",
    "QuestionDifficulty",
    "QuizLanguage",
    "GenerationParameters",
    "GenerationResult",
    # MCQ implementation
    "MultipleChoiceData",
    "MultipleChoiceQuestionType",
    # Registry
    "QuestionTypeRegistry",
    "get_question_type_registry",
]
