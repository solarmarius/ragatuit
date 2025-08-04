"""Test data factories for creating realistic test objects."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import factory
from factory import Factory, Faker, LazyAttribute, Sequence, SubFactory
from factory.alchemy import SQLAlchemyModelFactory

from src.auth.models import User
from src.question.models import Question, QuestionDifficulty, QuestionType
from src.quiz.models import Quiz
from tests.database import get_test_session
from tests.test_data import (
    DEFAULT_CANVAS_COURSE,
    DEFAULT_CANVAS_MODULES,
    DEFAULT_EXTRACTED_CONTENT,
    DEFAULT_FILE_INFO,
    DEFAULT_FILL_IN_BLANK_DATA,
    DEFAULT_MCQ_DATA,
    DEFAULT_OPENAI_RESPONSE,
    DEFAULT_QUIZ_CONFIG,
    DEFAULT_USER_DATA,
    SAMPLE_QUESTIONS_BATCH,
)


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
        lambda: {
            "module_1": {
                "name": "Introduction",
                "question_batches": [{"question_type": "multiple_choice", "count": 10}],
            },
            "module_2": {
                "name": "Advanced Topics",
                "question_batches": [{"question_type": "multiple_choice", "count": 15}],
            },
        }
    )
    title = Faker("sentence", nb_words=4)
    llm_model = "o3"
    llm_temperature = 1.0
    status = "created"
    failure_reason = None

    class Params:
        with_extracted_content = factory.Trait(
            status="extracting_content",
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
        with_generated_questions = factory.Trait(status="ready_for_review")
        exported_to_canvas = factory.Trait(
            status="published",
            canvas_quiz_id=Faker("uuid4"),
            exported_at=LazyAttribute(lambda obj: datetime.now(timezone.utc)),
        )
        failed_extraction = factory.Trait(
            status="failed", failure_reason="content_extraction_error"
        )
        failed_generation = factory.Trait(
            status="failed", failure_reason="llm_generation_error"
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
        fill_in_blank = factory.Trait(
            question_type=QuestionType.FILL_IN_BLANK,
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


# Additional factories for API responses and external service data


class OpenAIResponseFactory(Factory):
    """Factory for OpenAI API response data."""

    class Meta:
        model = dict

    content = DEFAULT_OPENAI_RESPONSE["content"]
    usage = factory.LazyFunction(lambda: DEFAULT_OPENAI_RESPONSE["usage"].copy())

    class Params:
        norwegian = factory.Trait(
            content='{"questions": [{"question_text": "Hva er hovedstaden i Norge?", "options": [{"text": "Oslo", "is_correct": true}, {"text": "Bergen", "is_correct": false}], "explanation": "Oslo er hovedstaden i Norge."}]}'
        )
        generation_error = factory.Trait(
            content='{"error": "Failed to generate questions"}'
        )


class CanvasQuizResponseFactory(Factory):
    """Factory for Canvas quiz creation response data."""

    class Meta:
        model = dict

    id = Sequence(lambda n: f"quiz_{n}")
    title = Faker("sentence", nb_words=3)
    quiz_type = "assignment"
    points_possible = 100
    assignment_id = factory.LazyAttribute(lambda obj: f"assignment_{obj.id}")


class CanvasQuizItemsResponseFactory(Factory):
    """Factory for Canvas quiz items creation response data."""

    class Meta:
        model = dict

    @classmethod
    def create_batch(cls, size: int = 3, **kwargs) -> List[Dict[str, Any]]:
        """Create a batch of quiz item responses."""
        return [
            {
                "success": True,
                "canvas_id": 8000 + i,
                "question_id": f"q{i + 1}",
                **kwargs,
            }
            for i in range(size)
        ]

    @classmethod
    def create_with_failures(
        cls, success_count: int = 2, failure_count: int = 1
    ) -> List[Dict[str, Any]]:
        """Create quiz item responses with some failures."""
        successful = cls.create_batch(success_count)
        failed = [
            {
                "success": False,
                "canvas_id": None,
                "question_id": f"failed_q{i + 1}",
                "error": "Export failed",
            }
            for i in range(failure_count)
        ]
        return successful + failed


class ManualModuleDataFactory(Factory):
    """Factory for manual module data."""

    class Meta:
        model = dict

    module_id = factory.LazyFunction(lambda: f"manual_{uuid.uuid4().hex[:8]}")
    name = Faker("sentence", nb_words=3)
    content = Faker("text", max_nb_chars=200)
    word_count = factory.LazyAttribute(lambda obj: len(obj.content.split()))
    source_type = "manual"
    content_type = "text"
    processing_metadata = factory.LazyFunction(lambda: {"source": "manual_text"})

    class Params:
        pdf_upload = factory.Trait(
            content_type="pdf",
            processing_metadata=factory.LazyFunction(
                lambda: {"source": "manual_pdf", "pages": 3}
            ),
        )
        text_input = factory.Trait(
            content_type="text",
            processing_metadata=factory.LazyFunction(lambda: {"source": "manual_text"}),
        )


class ContentExtractionResultFactory(Factory):
    """Factory for content extraction results."""

    class Meta:
        model = dict

    @classmethod
    def create_for_modules(
        cls, module_ids: List[str], **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create extraction results for specific module IDs."""
        result = {}
        for i, module_id in enumerate(module_ids):
            result[module_id] = [
                {
                    "content": f"Test content for module {module_id}",
                    "word_count": 100 + (i * 50),
                    "source_type": "canvas",
                }
            ]
        return result

    @classmethod
    def create_mixed_canvas_manual(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Create extraction results with both Canvas and manual content."""
        return {
            "101": [
                {
                    "content": "Canvas module content about programming",
                    "word_count": 200,
                    "source_type": "canvas",
                }
            ],
            "manual_abc123": [
                {
                    "content": "Manual content for testing",
                    "word_count": 50,
                    "source_type": "manual",
                }
            ],
        }


class QuestionGenerationResultFactory(Factory):
    """Factory for question generation results."""

    class Meta:
        model = dict

    @classmethod
    def create_for_modules(
        cls, module_ids: List[str], questions_per_module: int = 2
    ) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Create generation results for specific module IDs."""
        questions = {}
        successful_batches = []

        for module_id in module_ids:
            questions[module_id] = [
                f"Generated question {i + 1} for module {module_id}"
                for i in range(questions_per_module)
            ]
            successful_batches.append(f"{module_id}_multiple_choice")

        batch_status = {
            "successful_batches": successful_batches,
            "failed_batches": [],
        }

        return questions, batch_status

    @classmethod
    def create_with_failures(
        cls, successful_modules: List[str], failed_modules: List[str]
    ) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """Create generation results with some failures."""
        questions = {}
        successful_batches = []
        failed_batches = []

        for module_id in successful_modules:
            questions[module_id] = [f"Generated question for {module_id}"]
            successful_batches.append(f"{module_id}_multiple_choice")

        for module_id in failed_modules:
            failed_batches.append(f"{module_id}_multiple_choice")

        batch_status = {
            "successful_batches": successful_batches,
            "failed_batches": failed_batches,
        }

        return questions, batch_status


class WorkflowStateFactory(Factory):
    """Factory for creating complete workflow state scenarios."""

    class Meta:
        model = dict

    @classmethod
    def create_complete_success_scenario(cls) -> Dict[str, Any]:
        """Create a complete successful workflow scenario."""
        return {
            "user_data": DEFAULT_USER_DATA.copy(),
            "course_data": DEFAULT_CANVAS_COURSE.copy(),
            "modules_data": DEFAULT_CANVAS_MODULES.copy(),
            "quiz_config": DEFAULT_QUIZ_CONFIG.copy(),
            "extraction_result": DEFAULT_EXTRACTED_CONTENT.copy(),
            "generation_result": QuestionGenerationResultFactory.create_for_modules(
                ["456", "457"]
            ),
            "questions_data": SAMPLE_QUESTIONS_BATCH.copy(),
            "canvas_response": CanvasQuizResponseFactory(),
        }

    @classmethod
    def create_extraction_failure_scenario(cls) -> Dict[str, Any]:
        """Create a workflow scenario where content extraction fails."""
        return {
            "user_data": DEFAULT_USER_DATA.copy(),
            "course_data": DEFAULT_CANVAS_COURSE.copy(),
            "modules_data": DEFAULT_CANVAS_MODULES.copy(),
            "quiz_config": DEFAULT_QUIZ_CONFIG.copy(),
            "extraction_error": "Canvas API connection failed",
        }

    @classmethod
    def create_manual_content_scenario(cls) -> Dict[str, Any]:
        """Create a workflow scenario with manual content."""
        manual_module = ManualModuleDataFactory()
        return {
            "user_data": DEFAULT_USER_DATA.copy(),
            "course_data": DEFAULT_CANVAS_COURSE.copy(),
            "quiz_config": {
                **DEFAULT_QUIZ_CONFIG,
                "selected_modules": {
                    manual_module["module_id"]: {
                        **manual_module,
                        "question_batches": [
                            {
                                "question_type": "multiple_choice",
                                "count": 5,
                                "difficulty": "medium",
                            }
                        ],
                    }
                },
            },
            "extraction_result": {
                manual_module["module_id"]: [
                    {
                        "content": manual_module["content"],
                        "word_count": manual_module["word_count"],
                        "source_type": "manual",
                    }
                ]
            },
        }


# Enhanced utility functions with centralized data


def create_standardized_user_data(**overrides) -> Dict[str, Any]:
    """Create user data with standard defaults and optional overrides."""
    return {**DEFAULT_USER_DATA, **overrides}


def create_standardized_quiz_config(**overrides) -> Dict[str, Any]:
    """Create quiz config with standard defaults and optional overrides."""
    return {**DEFAULT_QUIZ_CONFIG, **overrides}


def create_complete_test_scenario(
    user_overrides: Dict[str, Any] = None,
    quiz_overrides: Dict[str, Any] = None,
    with_questions: bool = True,
    with_extraction: bool = True,
) -> Dict[str, Any]:
    """Create a complete test scenario with all necessary data."""
    scenario = {
        "user": create_standardized_user_data(**(user_overrides or {})),
        "quiz_config": create_standardized_quiz_config(**(quiz_overrides or {})),
        "course": DEFAULT_CANVAS_COURSE.copy(),
        "modules": DEFAULT_CANVAS_MODULES.copy(),
    }

    if with_extraction:
        scenario["extracted_content"] = DEFAULT_EXTRACTED_CONTENT.copy()

    if with_questions:
        scenario["questions"] = SAMPLE_QUESTIONS_BATCH.copy()
        scenario["generation_result"] = (
            QuestionGenerationResultFactory.create_for_modules(["456", "457"])
        )

    return scenario
