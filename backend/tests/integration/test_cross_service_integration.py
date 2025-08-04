"""Cross-service integration tests for complex scenarios."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlmodel import Session

from tests.common_mocks import (
    mock_content_extraction,
    mock_database_operations,
    mock_openai_api,
)
from tests.conftest import create_user_in_session
from tests.test_data import (
    DEFAULT_EXTRACTED_CONTENT,
    DEFAULT_SELECTED_MODULES,
    SAMPLE_QUESTIONS_BATCH,
    get_unique_course_data,
    get_unique_quiz_config,
    get_unique_user_data,
)


@pytest.mark.asyncio
async def test_concurrent_quiz_operations_isolation(session: Session, caplog):
    """Test multiple concurrent quiz operations with proper isolation."""
    import asyncio

    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup Multiple Users and Quizzes ===
    user1_data = get_unique_user_data()
    user2_data = get_unique_user_data()
    user1 = create_user_in_session(
        session, canvas_id=user1_data["canvas_id"], name=user1_data["name"]
    )
    user2 = create_user_in_session(
        session, canvas_id=user2_data["canvas_id"], name=user2_data["name"]
    )

    quiz_config = get_unique_quiz_config()
    quiz_template = {
        "selected_modules": DEFAULT_SELECTED_MODULES,
        "llm_model": quiz_config["llm_model"],
        "llm_temperature": quiz_config["llm_temperature"],
        "language": QuizLanguage.ENGLISH,
    }

    course1_data = get_unique_course_data()
    course2_data = get_unique_course_data()

    quiz1 = create_quiz(
        session,
        QuizCreate(
            canvas_course_id=course1_data["id"],
            canvas_course_name=course1_data["name"],
            title=f"{user1_data['name']} Quiz",
            **quiz_template,
        ),
        user1.id,
    )

    quiz2 = create_quiz(
        session,
        QuizCreate(
            canvas_course_id=course2_data["id"],
            canvas_course_name=course2_data["name"],
            title=f"{user2_data['name']} Quiz",
            **quiz_template,
        ),
        user2.id,
    )

    session.commit()

    # === Concurrent Operations Setup ===
    module_id = list(DEFAULT_SELECTED_MODULES.keys())[0]
    mock_extractor_1 = AsyncMock()
    mock_extractor_1.return_value = {
        module_id: [{"content": f"{user1_data['name']} content", "word_count": 100}]
    }

    mock_extractor_2 = AsyncMock()
    mock_extractor_2.return_value = {
        module_id: [{"content": f"{user2_data['name']} content", "word_count": 150}]
    }

    mock_summarizer = Mock()
    mock_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 100,
    }

    selected_modules = {
        module_id: {
            "name": "Concurrent Module",
            "source_type": "canvas",
            "question_batches": [],
        }
    }

    # === Execute Concurrent Operations ===
    operations = [
        _execute_content_extraction_workflow(
            quiz1.id,
            course1_data["id"],
            "token1",
            selected_modules,
            mock_extractor_1,
            mock_summarizer,
        ),
        _execute_content_extraction_workflow(
            quiz2.id,
            course2_data["id"],
            "token2",
            selected_modules,
            mock_extractor_2,
            mock_summarizer,
        ),
    ]

    results = await asyncio.gather(*operations)

    # === Assertions ===
    # Both operations should succeed independently
    assert results[0][1] == "completed"  # final_status for quiz1
    assert results[1][1] == "completed"  # final_status for quiz2

    # Each extractor should be called with correct parameters
    mock_extractor_1.assert_called_once_with(
        "token1", course1_data["id"], [int(module_id)]
    )
    mock_extractor_2.assert_called_once_with(
        "token2", course2_data["id"], [int(module_id)]
    )

    # Content should be isolated per quiz
    assert results[0][0][module_id][0]["content"] == f"{user1_data['name']} content"
    assert results[1][0][module_id][0]["content"] == f"{user2_data['name']} content"

    # Both quiz IDs should appear in logs
    assert str(quiz1.id) in caplog.text
    assert str(quiz2.id) in caplog.text


@pytest.mark.asyncio
async def test_partial_question_generation_recovery(session: Session, caplog):
    """Test recovery from partial question generation failures."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.question_generation import _execute_generation_workflow
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "101": ModuleSelection(
                name="Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "102": ModuleSelection(
                name="Module 2",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=2,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Mock Partial Generation Success ===
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        {
            "101": [
                SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            ],  # Partial success
            "102": [],  # Failed module
        },
        {
            "successful_batches": ["101_multiple_choice"],
            "failed_batches": ["102_true_false"],  # One module failed
        },
    )

    with patch(
        "src.question.services.prepare_and_validate_content"
    ) as mock_prepare_content:
        mock_prepare_content.return_value = {
            "101": [{"content": "Module 1 content", "word_count": 150}],
            "102": [{"content": "Module 2 content", "word_count": 180}],
        }

        with patch("src.database.get_async_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_quiz = Mock()
            mock_quiz.selected_modules = {
                "101": {
                    "question_batches": [
                        {"question_type": "multiple_choice", "count": 3}
                    ]
                },
                "102": {
                    "question_batches": [{"question_type": "true_false", "count": 2}]
                },
            }
            mock_quiz.generation_metadata = {
                "successful_batches": [],
                "failed_batches": [],
            }
            mock_session.get = AsyncMock(return_value=mock_quiz)
            mock_session.refresh = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            (
                gen_status,
                gen_error,
                gen_exception,
                batch_status,
            ) = await _execute_generation_workflow(
                quiz.id, 5, "gpt-4", 0.7, QuizLanguage.ENGLISH, mock_generation_service
            )

    # === Assertions ===
    # Should result in partial success
    assert gen_status == "partial_success"
    assert gen_error is None
    assert len(batch_status["successful_batches"]) == 1
    assert len(batch_status["failed_batches"]) == 1

    # Verify partial success logging
    assert "generation_workflow_partial_success" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_canvas_api_timeout_handling(session: Session, caplog):
    """Test Canvas API timeout handling across services."""
    import asyncio

    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "201": ModuleSelection(
                name="Timeout Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=1,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Mock Canvas API Timeout ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.side_effect = asyncio.TimeoutError("Canvas API timeout")

    mock_content_summarizer = Mock()

    selected_modules = {
        "201": {
            "name": "Timeout Module",
            "source_type": "canvas",
            "question_batches": [],
        }
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        course_data["id"],
        "timeout_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Timeout should be handled as failure
    assert final_status == "failed"
    assert extracted_content is None

    # Error should be logged with timeout information
    assert "content_extraction_workflow_failed" in caplog.text
    assert "TimeoutError" in caplog.text

    # Summarizer should not be called after timeout
    mock_content_summarizer.assert_not_called()

    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_llm_provider_fallback_integration(session: Session, caplog):
    """Test LLM provider fallback and retry integration."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.question_generation import _execute_generation_workflow
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "301": ModuleSelection(
                name="Fallback Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Mock LLM Provider Failure then Success ===
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )

    # First call fails, then retry succeeds
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.side_effect = [
        RuntimeError("OpenAI API rate limit exceeded"),
        (
            {
                "301": [
                    SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                    SAMPLE_QUESTIONS_BATCH[1]["question_text"],
                ]
            },
            {"successful_batches": ["301_multiple_choice"], "failed_batches": []},
        ),
    ]

    with patch(
        "src.question.services.prepare_and_validate_content"
    ) as mock_prepare_content:
        mock_prepare_content.return_value = {
            "301": [{"content": "Fallback content", "word_count": 200}]
        }

        with patch("src.database.get_async_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_quiz = Mock()
            mock_quiz.selected_modules = {
                "301": {
                    "question_batches": [
                        {"question_type": "multiple_choice", "count": 2}
                    ]
                }
            }
            mock_quiz.generation_metadata = {
                "successful_batches": [],
                "failed_batches": [],
            }
            mock_session.get = AsyncMock(return_value=mock_quiz)
            mock_session.refresh = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            # First attempt - should fail
            (
                gen_status_1,
                gen_error_1,
                gen_exception_1,
                batch_status_1,
            ) = await _execute_generation_workflow(
                quiz.id, 2, "gpt-4", 0.7, QuizLanguage.ENGLISH, mock_generation_service
            )

    # === Assertions ===
    # First attempt should fail
    assert gen_status_1 == "failed"
    assert gen_error_1 == "OpenAI API rate limit exceeded"
    assert gen_exception_1 is not None

    # Verify error logging
    assert "generation_workflow_failed" in caplog.text
    assert "OpenAI API rate limit exceeded" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_database_transaction_rollback_integration(session: Session, caplog):
    """Test database transaction rollback integration across workflows."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.export import _execute_export_workflow
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "401": ModuleSelection(
                name="Transaction Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Mock Database Failure Scenario ===
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 88888, "title": "Transaction Test"}

    # Mock complete question export failure (requires rollback)
    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q1",
            "error": "Database constraint violation",
        },
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q2",
            "error": "Database constraint violation",
        },
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q3",
            "error": "Database constraint violation",
        },
    ]

    export_data = {
        "course_id": course_data["id"],
        "title": quiz_config["title"],
        "questions": [
            {
                "id": "q1",
                "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                "approved": True,
            },
            {
                "id": "q2",
                "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
                "approved": True,
            },
            {
                "id": "q3",
                "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                "approved": True,
            },
        ],
    }

    export_result = await _execute_export_workflow(
        quiz.id,
        "transaction_token",
        mock_quiz_creator,
        mock_question_exporter,
        export_data,
    )

    # === Assertions ===
    # Export should fail completely
    assert export_result["success"] is False
    assert export_result["should_rollback"] is True
    assert export_result["exported_questions"] == 0
    assert export_result["total_questions"] == 3

    # All failures should be logged
    assert "canvas_export_failure_rollback_needed" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_content_format_validation_integration(session: Session, caplog):
    """Test content format validation across different content types."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup Mixed Content Types ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "manual_text_module": ModuleSelection(
                name="Text Module",
                source_type="manual",
                content="Plain text content for validation testing.",
                word_count=50,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=1,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "manual_markdown_module": ModuleSelection(
                name="Markdown Module",
                source_type="manual",
                content="# Markdown Content\n\nThis is **formatted** content with _emphasis_.",
                word_count=75,
                content_type="markdown",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=1,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Process Mixed Format Content ===
    mock_content_extractor = AsyncMock()  # Won't be called for manual content
    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 125,
    }

    selected_modules = {
        "manual_text_module": {
            "name": "Text Module",
            "source_type": "manual",
            "content": "Plain text content for validation testing.",
            "word_count": 50,
            "content_type": "text",
            "question_batches": [],
        },
        "manual_markdown_module": {
            "name": "Markdown Module",
            "source_type": "manual",
            "content": "# Markdown Content\n\nThis is **formatted** content with _emphasis_.",
            "word_count": 75,
            "content_type": "markdown",
            "question_batches": [],
        },
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        course_data["id"],
        "format_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Both content types should be processed
    assert final_status == "completed"
    assert extracted_content is not None
    assert "manual_text_module" in extracted_content
    assert "manual_markdown_module" in extracted_content

    # Verify content type preservation
    text_content = extracted_content["manual_text_module"][0]
    assert text_content["content_type"] == "text"
    assert text_content["content"] == "Plain text content for validation testing."

    markdown_content = extracted_content["manual_markdown_module"][0]
    assert markdown_content["content_type"] == "markdown"
    assert "# Markdown Content" in markdown_content["content"]

    # Canvas extractor should not be called
    mock_content_extractor.assert_not_called()

    # Verify format handling logging
    assert "processing_manual_content" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_quiz_lifecycle_state_transitions(session: Session, caplog):
    """Test complete quiz lifecycle with proper state transitions."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )
    from src.quiz.orchestrator.export import _execute_export_workflow
    from src.quiz.orchestrator.question_generation import _execute_generation_workflow
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup Complete Lifecycle ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name=course_data["name"],
        selected_modules={
            "501": ModuleSelection(
                name="Lifecycle Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Phase 1: Content Extraction ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.return_value = {
        "501": [{"content": "Lifecycle content", "word_count": 200}]
    }

    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 200,
    }

    selected_modules = {
        "501": {
            "name": "Lifecycle Module",
            "source_type": "canvas",
            "question_batches": [],
        }
    }

    content_result = await _execute_content_extraction_workflow(
        quiz.id,
        course_data["id"],
        "lifecycle_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Phase 2: Question Generation ===
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        {
            "501": [
                SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                SAMPLE_QUESTIONS_BATCH[1]["question_text"],
            ]
        },
        {"successful_batches": ["501_multiple_choice"], "failed_batches": []},
    )

    with patch(
        "src.question.services.prepare_and_validate_content"
    ) as mock_prepare_content:
        mock_prepare_content.return_value = content_result[0]

        with patch("src.database.get_async_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_quiz = Mock()
            mock_quiz.selected_modules = selected_modules
            mock_quiz.generation_metadata = {
                "successful_batches": [],
                "failed_batches": [],
            }
            mock_session.get = AsyncMock(return_value=mock_quiz)
            mock_session.refresh = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)

            generation_result = await _execute_generation_workflow(
                quiz.id, 2, "gpt-4", 0.7, QuizLanguage.ENGLISH, mock_generation_service
            )

    # === Phase 3: Export ===
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 99999, "title": "Lifecycle Quiz"}

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 1001, "question_id": "q1"},
        {"success": True, "canvas_id": 1002, "question_id": "q2"},
    ]

    export_data = {
        "course_id": course_data["id"],
        "title": quiz_config["title"],
        "questions": [
            {
                "id": "q1",
                "question_text": SAMPLE_QUESTIONS_BATCH[0]["question_text"],
                "approved": True,
            },
            {
                "id": "q2",
                "question_text": SAMPLE_QUESTIONS_BATCH[1]["question_text"],
                "approved": True,
            },
        ],
    }

    export_result = await _execute_export_workflow(
        quiz.id,
        "lifecycle_token",
        mock_quiz_creator,
        mock_question_exporter,
        export_data,
    )

    # === Lifecycle Assertions ===
    # Each phase should complete successfully
    assert content_result[1] == "completed"  # Content extraction
    assert generation_result[0] == "completed"  # Question generation
    assert export_result["success"] is True  # Export

    # All phases should be logged
    assert "content_extraction_workflow_completed" in caplog.text
    assert "generation_workflow_complete_success" in caplog.text
    assert "canvas_export_complete_success" in caplog.text

    # Quiz ID should appear throughout lifecycle
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_multi_language_content_integration(session: Session, caplog):
    """Test multi-language content handling integration."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.content_extraction import (
        _execute_content_extraction_workflow,
    )
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup Multi-Language Content ===
    user_data = get_unique_user_data()
    user = create_user_in_session(
        session, canvas_id=user_data["canvas_id"], name=user_data["name"]
    )

    course_data = get_unique_course_data()
    quiz_config = get_unique_quiz_config()

    quiz_create = QuizCreate(
        canvas_course_id=course_data["id"],
        canvas_course_name="Flerspråklig Kurs",
        selected_modules={
            "manual_norsk_modul": ModuleSelection(
                name="Norsk Modul",
                source_type="manual",
                content="Dette er norsk innhold for testing av flerspråklig funksjonalitet. Innholdet dekker emner som kunstig intelligens og maskinlæring.",
                word_count=180,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "manual_engelsk_modul": ModuleSelection(
                name="English Module",
                source_type="manual",
                content="This is English content for testing multilingual functionality. The content covers topics like artificial intelligence and machine learning.",
                word_count=165,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=1,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title=quiz_config["title"],
        llm_model=quiz_config["llm_model"],
        llm_temperature=quiz_config["llm_temperature"],
        language=QuizLanguage.NORWEGIAN,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Process Multi-Language Content ===
    mock_content_extractor = AsyncMock()  # Won't be called for manual content
    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 345,
    }

    selected_modules = {
        "manual_norsk_modul": {
            "name": "Norsk Modul",
            "source_type": "manual",
            "content": "Dette er norsk innhold for testing av flerspråklig funksjonalitet. Innholdet dekker emner som kunstig intelligens og maskinlæring.",
            "word_count": 180,
            "content_type": "text",
            "question_batches": [],
        },
        "manual_engelsk_modul": {
            "name": "English Module",
            "source_type": "manual",
            "content": "This is English content for testing multilingual functionality. The content covers topics like artificial intelligence and machine learning.",
            "word_count": 165,
            "content_type": "text",
            "question_batches": [],
        },
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        course_data["id"],
        "multilang_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Multi-language content should be processed
    assert final_status == "completed"
    assert extracted_content is not None
    assert "manual_norsk_modul" in extracted_content
    assert "manual_engelsk_modul" in extracted_content

    # Verify Norwegian content
    norsk_content = extracted_content["manual_norsk_modul"][0]
    assert "Dette er norsk innhold" in norsk_content["content"]
    assert norsk_content["word_count"] == 180

    # Verify English content
    english_content = extracted_content["manual_engelsk_modul"][0]
    assert "This is English content" in english_content["content"]
    assert english_content["word_count"] == 165

    # Canvas extractor should not be called
    mock_content_extractor.assert_not_called()

    # Verify multilingual processing
    assert "processing_manual_content" in caplog.text
    assert str(quiz.id) in caplog.text
