"""Test data factories for creating realistic test objects."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import factory
from factory import Factory, Faker, LazyAttribute, Sequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

from src.auth.models import User
from src.question.models import Question, QuestionDifficulty, QuestionType
from src.quiz.models import Quiz
from tests.database import get_test_session


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory with common configuration."""

    class Meta:
        sqlalchemy_session_persistence = "commit"
        abstract = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override to use test session."""
        with get_test_session() as session:
            cls._meta.sqlalchemy_session = session
            instance = super()._create(model_class, *args, **kwargs)
            session.refresh(instance)
            return instance


class UserFactory(BaseFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    canvas_id = Sequence(lambda n: 1000 + n)
    name = Faker("name")
    access_token = Faker("uuid4")
    refresh_token = Faker("uuid4")
    expires_at = LazyAttribute(
        lambda obj: datetime.now(timezone.utc) + timedelta(hours=1)
    )
    token_type = "Bearer"
    onboarding_completed = False

    class Params:
        with_onboarding_completed = factory.Trait(onboarding_completed=True)
        expired_token = factory.Trait(
            expires_at=LazyAttribute(
                lambda obj: datetime.now(timezone.utc) - timedelta(hours=1)
            )
        )


class QuizFactory(BaseFactory):
    """Factory for creating Quiz instances."""

    class Meta:
        model = Quiz

    id = factory.LazyFunction(uuid.uuid4)
    owner = SubFactory(UserFactory)
    canvas_course_id = Sequence(lambda n: 100 + n)
    canvas_course_name = Faker("catch_phrase")
    selected_modules = factory.LazyFunction(
        lambda: {"module_1": "Introduction", "module_2": "Advanced Topics"}
    )
    title = Faker("sentence", nb_words=4)
    question_count = 100
    llm_model = "o3"
    llm_temperature = 1.0
    content_extraction_status = "pending"
    llm_generation_status = "pending"
    export_status = "pending"

    class Params:
        with_extracted_content = factory.Trait(
            content_extraction_status="completed",
            extracted_content=factory.LazyFunction(
                lambda: {
                    "modules": [
                        {
                            "id": "module_1",
                            "name": "Introduction",
                            "content": "This is introduction content...",
                        }
                    ],
                    "total_content_length": 1500,
                }
            ),
            content_extracted_at=LazyAttribute(lambda obj: datetime.now(timezone.utc)),
        )
        with_generated_questions = factory.Trait(
            llm_generation_status="completed", content_extraction_status="completed"
        )
        exported_to_canvas = factory.Trait(
            export_status="completed",
            canvas_quiz_id=Faker("uuid4"),
            exported_at=LazyAttribute(lambda obj: datetime.now(timezone.utc)),
        )


class QuestionFactory(BaseFactory):
    """Factory for creating Question instances."""

    class Meta:
        model = Question

    id = factory.LazyFunction(uuid.uuid4)
    quiz = SubFactory(QuizFactory)
    question_type = QuestionType.MULTIPLE_CHOICE
    difficulty = QuestionDifficulty.MEDIUM
    is_approved = False

    # Default multiple choice question data
    question_data = factory.LazyFunction(
        lambda: {
            "question_text": "What is the capital of France?",
            "options": [
                {"text": "Paris", "is_correct": True},
                {"text": "London", "is_correct": False},
                {"text": "Berlin", "is_correct": False},
                {"text": "Madrid", "is_correct": False},
            ],
            "explanation": "Paris is the capital and largest city of France.",
        }
    )

    class Params:
        approved = factory.Trait(
            is_approved=True,
            approved_at=LazyAttribute(lambda obj: datetime.now(timezone.utc)),
        )
        true_false = factory.Trait(
            question_type=QuestionType.TRUE_FALSE,
            question_data=factory.LazyFunction(
                lambda: {
                    "question_text": "The Earth is flat.",
                    "is_true": False,
                    "explanation": "The Earth is roughly spherical in shape.",
                }
            ),
        )
        short_answer = factory.Trait(
            question_type=QuestionType.SHORT_ANSWER,
            question_data=factory.LazyFunction(
                lambda: {
                    "question_text": "What is the chemical symbol for water?",
                    "correct_answers": ["H2O", "h2o"],
                    "explanation": "Water is composed of two hydrogen atoms and one oxygen atom.",
                }
            ),
        )
        easy_difficulty = factory.Trait(difficulty=QuestionDifficulty.EASY)
        hard_difficulty = factory.Trait(difficulty=QuestionDifficulty.HARD)


# Non-model factories for testing schemas and data structures


class CanvasCourseDataFactory(Factory):
    """Factory for Canvas course data."""

    class Meta:
        model = dict

    id = Sequence(lambda n: 100 + n)
    name = Faker("catch_phrase")
    course_code = Sequence(lambda n: f"CS{n}")
    enrollment_term_id = 1
    workflow_state = "available"


class CanvasModuleDataFactory(Factory):
    """Factory for Canvas module data."""

    class Meta:
        model = dict

    id = Sequence(lambda n: 200 + n)
    name = Faker("sentence", nb_words=3)
    position = Sequence(lambda n: n)
    workflow_state = "active"
    items_count = Faker("random_int", min=1, max=10)


class ExtractedContentFactory(Factory):
    """Factory for extracted content data."""

    class Meta:
        model = dict

    modules = factory.LazyFunction(
        lambda: [
            {
                "id": "module_1",
                "name": "Introduction to Programming",
                "content": "Programming is the process of creating instructions for computers...",
                "content_length": 500,
            },
            {
                "id": "module_2",
                "name": "Data Structures",
                "content": "Data structures are ways of organizing and storing data...",
                "content_length": 750,
            },
        ]
    )
    total_content_length = 1250
    extraction_metadata = factory.LazyFunction(
        lambda: {
            "extraction_method": "canvas_api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modules_processed": 2,
        }
    )


# Utility functions for creating test data


def create_user_with_quiz(session_override=None, **quiz_kwargs) -> tuple[User, Quiz]:
    """Create a user with an associated quiz."""
    if session_override:
        UserFactory._meta.sqlalchemy_session = session_override
        QuizFactory._meta.sqlalchemy_session = session_override

    user = UserFactory()
    quiz = QuizFactory(owner=user, **quiz_kwargs)
    return user, quiz


def create_quiz_with_questions(
    question_count: int = 5, session_override=None, **question_kwargs
) -> tuple[Quiz, list[Question]]:
    """Create a quiz with multiple questions."""
    if session_override:
        QuizFactory._meta.sqlalchemy_session = session_override
        QuestionFactory._meta.sqlalchemy_session = session_override

    quiz = QuizFactory()
    questions = [
        QuestionFactory(quiz=quiz, **question_kwargs) for _ in range(question_count)
    ]
    return quiz, questions


def create_canvas_integration_data() -> Dict[str, Any]:
    """Create realistic Canvas integration test data."""
    return {
        "course": CanvasCourseDataFactory(),
        "modules": [CanvasModuleDataFactory() for _ in range(3)],
        "extracted_content": ExtractedContentFactory(),
    }
