"""Polymorphic question models for multiple question types."""

# Re-export the new polymorphic Question model and related types
from .types.base import (
    GenerationParameters,
    GenerationResult,
    Question,
    QuestionDifficulty,
    QuestionType,
)

__all__ = [
    "Question",
    "QuestionType",
    "QuestionDifficulty",
    "GenerationParameters",
    "GenerationResult",
]
