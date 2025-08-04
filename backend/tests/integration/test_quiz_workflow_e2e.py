"""End-to-end integration tests for complete quiz workflows."""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlmodel import Session

from tests.conftest import create_user_in_session


@pytest.mark.asyncio
async def test_complete_canvas_workflow_integration(session: Session, caplog):
    """Test complete Canvas workflow integration without database transactions."""
    from src.auth.schemas import UserCreate
    from src.auth.service import create_user
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

    # === 1. User Setup ===
    with patch(
        "src.auth.service.encrypt_token", side_effect=lambda t: f"encrypted_{t}"
    ):
        user_data = UserCreate(
            canvas_id=12345,
            name="Integration Test User",
            access_token="canvas_access_token",
            refresh_token="canvas_refresh_token",
        )
        user = create_user(session, user_data)

    # === 2. Quiz Creation ===
    quiz_create = QuizCreate(
        canvas_course_id=67890,
        canvas_course_name="Integration Test Course",
        selected_modules={
            "101": ModuleSelection(
                name="Test Module 1",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=3,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "102": ModuleSelection(
                name="Test Module 2",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=2,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            ),
        },
        title="E2E Integration Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === 3. Content Extraction Integration ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.return_value = {
        "101": [
            {"content": "Module 1 content about machine learning", "word_count": 150},
            {"content": "More content about neural networks", "word_count": 200},
        ],
        "102": [{"content": "Module 2 content about algorithms", "word_count": 180}],
    }

    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 3,
        "total_word_count": 530,
    }

    # Test content extraction workflow directly
    selected_modules = {
        "101": {
            "name": "Test Module 1",
            "source_type": "canvas",
            "question_batches": [],
        },
        "102": {
            "name": "Test Module 2",
            "source_type": "canvas",
            "question_batches": [],
        },
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        67890,
        "canvas_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === 4. Question Generation Integration ===
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        {
            "101": [
                "Generated MC question 1",
                "Generated MC question 2",
                "Generated MC question 3",
            ],
            "102": ["Generated TF question 1", "Generated TF question 2"],
        },
        {
            "successful_batches": ["101_multiple_choice", "102_true_false"],
            "failed_batches": [],
        },
    )

    # Mock content preparation for generation
    with patch(
        "src.question.services.prepare_and_validate_content"
    ) as mock_prepare_content:
        mock_prepare_content.return_value = extracted_content

        # Mock quiz data access
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

            (
                gen_status,
                gen_error,
                gen_exception,
                batch_status,
            ) = await _execute_generation_workflow(
                quiz.id, 5, "gpt-4", 0.7, QuizLanguage.ENGLISH, mock_generation_service
            )

    # === 5. Export Integration ===
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 99999, "title": "E2E Test Quiz"}

    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 8001, "question_id": "q1"},
        {"success": True, "canvas_id": 8002, "question_id": "q2"},
        {"success": True, "canvas_id": 8003, "question_id": "q3"},
        {"success": True, "canvas_id": 8004, "question_id": "q4"},
        {"success": True, "canvas_id": 8005, "question_id": "q5"},
    ]

    export_data = {
        "course_id": 67890,
        "title": "E2E Test Quiz",
        "questions": [
            {"id": "q1", "question_text": "What is ML?", "approved": True},
            {"id": "q2", "question_text": "Define AI", "approved": True},
            {"id": "q3", "question_text": "Neural networks?", "approved": True},
            {
                "id": "q4",
                "question_text": "True or false: AI is complex",
                "approved": True,
            },
            {
                "id": "q5",
                "question_text": "True or false: ML uses data",
                "approved": True,
            },
        ],
    }

    export_result = await _execute_export_workflow(
        quiz.id, "canvas_token", mock_quiz_creator, mock_question_exporter, export_data
    )

    # === Integration Assertions ===
    # Content extraction should succeed
    assert final_status == "completed"
    assert extracted_content is not None
    assert "101" in extracted_content
    assert "102" in extracted_content

    # Question generation should succeed
    assert gen_status == "completed"
    assert gen_error is None
    assert len(batch_status["successful_batches"]) == 2
    assert len(batch_status["failed_batches"]) == 0

    # Export should succeed
    assert export_result["success"] is True
    assert export_result["canvas_quiz_id"] == 99999
    assert export_result["exported_questions"] == 5

    # Cross-workflow integration
    mock_content_extractor.assert_called_once_with("canvas_token", 67890, [101, 102])
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.assert_called_once()
    mock_quiz_creator.assert_called_once()
    mock_question_exporter.assert_called_once()

    # Verify logging integration
    assert "content_extraction_workflow_completed" in caplog.text
    assert "generation_workflow_complete_success" in caplog.text
    assert "canvas_export_complete_success" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_manual_content_workflow_integration(session: Session, caplog):
    """Test manual content workflow integration."""
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
    user = create_user_in_session(session)

    quiz_create = QuizCreate(
        canvas_course_id=11111,
        canvas_course_name="Manual Test Course",
        selected_modules={
            "manual_1": ModuleSelection(
                name="Manual Module",
                source_type="manual",
                content="This is manual content for testing question generation. It covers topics like artificial intelligence and machine learning.",
                word_count=150,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Manual Content Quiz",
        llm_model="gpt-4",
        llm_temperature=0.8,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Manual Content Processing ===
    mock_content_extractor = AsyncMock()  # Should not be called
    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 150,
    }

    selected_modules = {
        "manual_1": {
            "name": "Manual Module",
            "source_type": "manual",
            "content": "This is manual content for testing question generation. It covers topics like artificial intelligence and machine learning.",
            "word_count": 150,
            "content_type": "text",
            "question_batches": [],
        }
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        11111,
        "manual_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Manual content should be processed without Canvas API calls
    mock_content_extractor.assert_not_called()

    # Content should be structured properly
    assert final_status == "completed"
    assert extracted_content is not None
    assert "manual_1" in extracted_content
    assert extracted_content["manual_1"][0]["source_type"] == "manual"
    assert (
        extracted_content["manual_1"][0]["content"]
        == "This is manual content for testing question generation. It covers topics like artificial intelligence and machine learning."
    )

    # Logging should indicate manual processing
    assert "content_modules_categorized" in caplog.text
    assert "processing_manual_content" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_mixed_content_workflow_integration(session: Session, caplog):
    """Test mixed Canvas + manual content workflow integration."""
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
    user = create_user_in_session(session)

    quiz_create = QuizCreate(
        canvas_course_id=22222,
        canvas_course_name="Mixed Content Course",
        selected_modules={
            "101": ModuleSelection(
                name="Canvas Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            ),
            "manual_1": ModuleSelection(
                name="Manual Supplement",
                source_type="manual",
                content="Additional manual content to supplement Canvas materials.",
                word_count=120,
                content_type="text",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.FILL_IN_BLANK,
                        count=1,
                        difficulty=QuestionDifficulty.HARD,
                    )
                ],
            ),
        },
        title="Mixed Content Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Mixed Content Processing ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.return_value = {
        "101": [{"content": "Canvas module content", "word_count": 250}]
    }

    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 2,
        "total_pages": 2,
        "total_word_count": 370,  # 250 + 120
    }

    selected_modules = {
        "101": {
            "name": "Canvas Module",
            "source_type": "canvas",
            "question_batches": [],
        },
        "manual_1": {
            "name": "Manual Supplement",
            "source_type": "manual",
            "content": "Additional manual content to supplement Canvas materials.",
            "word_count": 120,
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
        22222,
        "mixed_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Should call Canvas extractor only for Canvas module
    mock_content_extractor.assert_called_once_with("mixed_token", 22222, [101])

    # Should process both content types
    assert final_status == "completed"
    assert extracted_content is not None
    assert "101" in extracted_content  # Canvas content
    assert "manual_1" in extracted_content  # Manual content

    # Verify content structure
    assert extracted_content["101"][0]["content"] == "Canvas module content"
    assert extracted_content["manual_1"][0]["source_type"] == "manual"
    assert (
        extracted_content["manual_1"][0]["content"]
        == "Additional manual content to supplement Canvas materials."
    )

    # Logging should show mixed processing
    assert "content_modules_categorized" in caplog.text
    assert "extracting_canvas_content" in caplog.text
    assert "processing_manual_content" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_error_propagation_integration(session: Session, caplog):
    """Test error propagation across workflow components."""
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
    user = create_user_in_session(session)

    quiz_create = QuizCreate(
        canvas_course_id=33333,
        canvas_course_name="Error Test Course",
        selected_modules={
            "201": ModuleSelection(
                name="Error Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=1,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Error Propagation Test",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Canvas API Error ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.side_effect = RuntimeError("Canvas API connection failed")

    mock_content_summarizer = Mock()

    selected_modules = {
        "201": {"name": "Error Module", "source_type": "canvas", "question_batches": []}
    }

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        33333,
        "error_token",
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Error should be handled gracefully
    assert final_status == "failed"
    assert extracted_content is None
    assert cleaned_modules == selected_modules  # Original modules returned

    # Error should be logged
    assert "content_extraction_workflow_failed" in caplog.text
    assert "Canvas API connection failed" in caplog.text

    # Summarizer should not be called after extractor failure
    mock_content_summarizer.assert_not_called()

    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_authentication_token_integration(session: Session):
    """Test Canvas token handling throughout workflow integration."""
    from src.auth.schemas import UserCreate
    from src.auth.service import create_user, get_decrypted_access_token
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

    # === OAuth Token Setup ===
    user_data = UserCreate(
        canvas_id=54321,
        name="Auth Test User",
        access_token="encrypted_canvas_token",
        refresh_token="encrypted_refresh_token",
    )

    with patch("src.auth.service.encrypt_token", side_effect=lambda t: f"enc_{t}"):
        user = create_user(session, user_data)

    # === Token Decryption Test ===
    with patch("src.auth.service.decrypt_token") as mock_decrypt:
        mock_decrypt.return_value = "decrypted_canvas_token"

        decrypted_token = get_decrypted_access_token(user)
        assert decrypted_token == "decrypted_canvas_token"
        mock_decrypt.assert_called_once_with("enc_encrypted_canvas_token")

    # === Canvas API Integration with Token ===
    quiz_create = QuizCreate(
        canvas_course_id=44444,
        canvas_course_name="Auth Test Course",
        selected_modules={
            "301": ModuleSelection(
                name="Protected Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.TRUE_FALSE,
                        count=1,
                        difficulty=QuestionDifficulty.EASY,
                    )
                ],
            )
        },
        title="Authentication Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Authenticated Canvas Call ===
    mock_content_extractor = AsyncMock()
    mock_content_extractor.return_value = {
        "301": [{"content": "Protected content", "word_count": 100}]
    }

    mock_content_summarizer = Mock()
    mock_content_summarizer.return_value = {
        "modules_processed": 1,
        "total_pages": 1,
        "total_word_count": 100,
    }

    selected_modules = {
        "301": {
            "name": "Protected Module",
            "source_type": "canvas",
            "question_batches": [],
        }
    }

    canvas_token = "authenticated_canvas_token"

    (
        extracted_content,
        final_status,
        cleaned_modules,
    ) = await _execute_content_extraction_workflow(
        quiz.id,
        44444,
        canvas_token,
        selected_modules,
        mock_content_extractor,
        mock_content_summarizer,
    )

    # === Assertions ===
    # Canvas API should be called with the provided token
    mock_content_extractor.assert_called_once_with(canvas_token, 44444, [301])

    # Workflow should complete with authenticated access
    assert final_status == "completed"
    assert extracted_content is not None
    assert "301" in extracted_content


@pytest.mark.asyncio
async def test_export_rollback_integration(session: Session, caplog):
    """Test export failure and rollback integration."""
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
    user = create_user_in_session(session)

    quiz_create = QuizCreate(
        canvas_course_id=55555,
        canvas_course_name="Rollback Test Course",
        selected_modules={
            "401": ModuleSelection(
                name="Rollback Module",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Rollback Test Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.ENGLISH,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Export with Partial Failure ===
    mock_quiz_creator = AsyncMock()
    mock_quiz_creator.return_value = {"id": 66666, "title": "Failed Export"}

    # Mock partial failure requiring rollback
    mock_question_exporter = AsyncMock()
    mock_question_exporter.return_value = [
        {"success": True, "canvas_id": 1001, "question_id": "q1"},
        {
            "success": False,
            "canvas_id": None,
            "question_id": "q2",
            "error": "Export failed",
        },
    ]

    export_data = {
        "course_id": 55555,
        "title": "Failed Export Quiz",
        "questions": [
            {"id": "q1", "question_text": "Question 1?", "approved": True},
            {"id": "q2", "question_text": "Question 2?", "approved": True},
        ],
    }

    export_result = await _execute_export_workflow(
        quiz.id,
        "rollback_token",
        mock_quiz_creator,
        mock_question_exporter,
        export_data,
    )

    # === Assertions ===
    # Export should fail due to partial success
    assert export_result["success"] is False
    assert export_result["should_rollback"] is True
    assert export_result["canvas_quiz_id"] == 66666
    assert export_result["exported_questions"] == 1  # Only one succeeded
    assert export_result["total_questions"] == 2

    # Failure should be logged
    assert "canvas_export_failure_rollback_needed" in caplog.text
    assert str(quiz.id) in caplog.text


@pytest.mark.asyncio
async def test_language_workflow_integration(session: Session, caplog):
    """Test Norwegian language workflow integration."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.orchestrator.question_generation import _execute_generation_workflow
    from src.quiz.schemas import (
        ModuleSelection,
        QuestionBatch,
        QuizCreate,
        QuizLanguage,
    )
    from src.quiz.service import create_quiz

    # === Setup Norwegian Quiz ===
    user = create_user_in_session(session)

    quiz_create = QuizCreate(
        canvas_course_id=99999,
        canvas_course_name="Norsk Kurs",
        selected_modules={
            "601": ModuleSelection(
                name="Norsk Modul",
                question_batches=[
                    QuestionBatch(
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        count=2,
                        difficulty=QuestionDifficulty.MEDIUM,
                    )
                ],
            )
        },
        title="Norsk Quiz",
        llm_model="gpt-4",
        llm_temperature=0.7,
        language=QuizLanguage.NORWEGIAN,
    )

    quiz = create_quiz(session, quiz_create, user.id)
    session.commit()

    # === Norwegian Question Generation ===
    mock_generation_service = Mock()
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking = (
        AsyncMock()
    )
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.return_value = (
        {"601": ["Norsk spørsmål 1", "Norsk spørsmål 2"]},
        {"successful_batches": ["601_multiple_choice"], "failed_batches": []},
    )

    with patch(
        "src.question.services.prepare_and_validate_content"
    ) as mock_prepare_content:
        mock_prepare_content.return_value = {
            "601": [{"content": "Norsk innhold", "word_count": 100}]
        }

        with patch("src.database.get_async_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_quiz = Mock()
            mock_quiz.selected_modules = {
                "601": {
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

            (
                gen_status,
                gen_error,
                gen_exception,
                batch_status,
            ) = await _execute_generation_workflow(
                quiz.id,
                2,
                "gpt-4",
                0.7,
                QuizLanguage.NORWEGIAN,
                mock_generation_service,
            )

    # === Assertions ===
    # Norwegian generation should succeed
    assert gen_status == "completed"
    assert gen_error is None
    assert len(batch_status["successful_batches"]) == 1

    # Generation service should be called
    mock_generation_service.generate_questions_for_quiz_with_batch_tracking.assert_called_once()

    # Workflow should complete successfully
    assert "generation_workflow_complete_success" in caplog.text
    assert str(quiz.id) in caplog.text
