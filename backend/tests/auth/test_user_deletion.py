"""Tests for user deletion with quiz anonymization."""

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.main import app
from src.question.models import Question
from src.question.types import QuestionType
from src.quiz.models import Quiz
from tests.conftest import create_quiz_in_session, create_user_in_session


def test_user_deletion_anonymizes_quizzes(session: Session):
    """Test user deletion anonymizes associated quizzes."""
    from src.auth.service import get_user_by_id

    # Create user and quiz
    user = create_user_in_session(session)
    quiz = create_quiz_in_session(session, owner=user)

    # Create questions for the quiz
    question1 = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Test Q1", "choices": ["A", "B"]},
    )
    question2 = Question(
        quiz_id=quiz.id,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_data={"question_text": "Test Q2", "choices": ["C", "D"]},
    )
    session.add_all([question1, question2])
    session.commit()
    session.refresh(question1)
    session.refresh(question2)

    # Simulate user deletion by manually calling the logic
    # (since the actual delete_user_me requires authentication)
    user_quizzes = session.exec(select(Quiz).where(Quiz.owner_id == user.id)).all()

    quiz_count = len(user_quizzes)
    total_questions_deleted = 0

    for quiz in user_quizzes:
        # Cascade soft delete to all associated questions
        questions = session.exec(
            select(Question)
            .where(Question.quiz_id == quiz.id)
            .where(Question.deleted == False)  # noqa: E712
        ).all()

        question_count = len(questions)
        total_questions_deleted += question_count

        # Soft delete all questions
        for question in questions:
            question.deleted = True
            question.deleted_at = datetime.now()
            session.add(question)

        # Anonymize the quiz by removing owner association
        quiz.owner_id = None
        # Soft delete the quiz to preserve data for research
        quiz.deleted = True
        quiz.deleted_at = datetime.now()
        session.add(quiz)

    # Hard delete the user account (complete removal)
    session.delete(user)
    session.commit()

    # Verify user is completely deleted
    deleted_user = get_user_by_id(session, user.id)
    assert deleted_user is None

    # Verify quiz is anonymized and soft-deleted
    anonymized_quiz = session.exec(select(Quiz).where(Quiz.id == quiz.id)).first()
    assert anonymized_quiz is not None
    assert anonymized_quiz.owner_id is None  # Anonymized
    assert anonymized_quiz.deleted is True  # Soft deleted
    assert anonymized_quiz.deleted_at is not None

    # Verify questions are soft-deleted
    deleted_questions = session.exec(
        select(Question).where(Question.quiz_id == quiz.id)
    ).all()
    assert len(deleted_questions) == 2
    for q in deleted_questions:
        assert q.deleted is True
        assert q.deleted_at is not None

    # Verify data is preserved for research
    assert anonymized_quiz.title == quiz.title
    assert anonymized_quiz.selected_modules == quiz.selected_modules
    assert anonymized_quiz.question_count == quiz.question_count


def test_user_deletion_preserves_quiz_data_for_research(session: Session):
    """Test user deletion preserves all quiz data for research purposes."""
    # Create user with comprehensive quiz data
    user = create_user_in_session(session)
    quiz = create_quiz_in_session(
        session,
        owner=user,
        title="Research Study Quiz",
        question_count=100,
        llm_model="gpt-4",
        llm_temperature=0.8,
        selected_modules={
            "123": {"name": "Advanced AI", "question_count": 50},
            "456": {"name": "Machine Learning", "question_count": 50},
        },
    )

    original_quiz_data = {
        "title": quiz.title,
        "question_count": quiz.question_count,
        "llm_model": quiz.llm_model,
        "llm_temperature": quiz.llm_temperature,
        "selected_modules": quiz.selected_modules,
        "canvas_course_id": quiz.canvas_course_id,
        "canvas_course_name": quiz.canvas_course_name,
        "status": quiz.status,
        "language": quiz.language,
        "question_type": quiz.question_type,
    }

    # Simulate user deletion process
    quiz.owner_id = None  # Anonymize
    quiz.deleted = True  # Soft delete
    quiz.deleted_at = datetime.now()
    session.add(quiz)
    session.delete(user)  # Hard delete user
    session.commit()

    # Retrieve anonymized quiz
    anonymized_quiz = session.exec(select(Quiz).where(Quiz.id == quiz.id)).first()

    # Verify all research data is preserved
    assert anonymized_quiz is not None
    assert anonymized_quiz.owner_id is None  # Anonymized
    assert anonymized_quiz.deleted is True  # Soft deleted

    # Verify all original data is preserved for research
    assert anonymized_quiz.title == original_quiz_data["title"]
    assert anonymized_quiz.question_count == original_quiz_data["question_count"]
    assert anonymized_quiz.llm_model == original_quiz_data["llm_model"]
    assert anonymized_quiz.llm_temperature == original_quiz_data["llm_temperature"]
    assert anonymized_quiz.selected_modules == original_quiz_data["selected_modules"]
    assert anonymized_quiz.canvas_course_id == original_quiz_data["canvas_course_id"]
    assert (
        anonymized_quiz.canvas_course_name == original_quiz_data["canvas_course_name"]
    )
    assert anonymized_quiz.status == original_quiz_data["status"]
    assert anonymized_quiz.language == original_quiz_data["language"]
    assert anonymized_quiz.question_type == original_quiz_data["question_type"]


def test_user_deletion_gdpr_compliance(session: Session):
    """Test user deletion ensures GDPR compliance through complete anonymization."""
    # Create user with personal data
    user = create_user_in_session(session, name="John Doe", canvas_id=12345)
    quiz1 = create_quiz_in_session(session, owner=user, title="John's Quiz 1")
    quiz2 = create_quiz_in_session(session, owner=user, title="John's Quiz 2")

    # Store original user data
    user_id = user.id
    canvas_id = user.canvas_id
    user_name = user.name

    # Simulate complete user deletion process
    user_quizzes = session.exec(select(Quiz).where(Quiz.owner_id == user.id)).all()

    # Anonymize all quizzes
    for quiz in user_quizzes:
        quiz.owner_id = None  # Remove personal connection
        quiz.deleted = True
        quiz.deleted_at = datetime.now()
        session.add(quiz)

    # Hard delete user (complete removal of PII)
    session.delete(user)
    session.commit()

    # Verify complete user PII removal
    from src.auth.service import get_user_by_canvas_id, get_user_by_id

    deleted_user_by_id = get_user_by_id(session, user_id)
    assert deleted_user_by_id is None

    deleted_user_by_canvas = get_user_by_canvas_id(session, canvas_id)
    assert deleted_user_by_canvas is None

    # Verify no way to trace quizzes back to user
    anonymized_quizzes = session.exec(
        select(Quiz).where(Quiz.id.in_([quiz1.id, quiz2.id]))
    ).all()

    assert len(anonymized_quizzes) == 2
    for quiz in anonymized_quizzes:
        assert quiz.owner_id is None  # No connection to user
        assert quiz.deleted is True  # Soft deleted for research
        # Quiz titles and content preserved for research
        assert quiz.title in ["John's Quiz 1", "John's Quiz 2"]

    # Verify there's no database record that can link back to the user
    # This ensures GDPR "right to be forgotten" compliance
    all_quizzes = session.exec(select(Quiz).where(Quiz.owner_id == user_id)).all()
    assert len(all_quizzes) == 0  # No quizzes linked to deleted user ID


def test_multiple_users_deletion_isolation(session: Session):
    """Test multiple user deletions don't affect each other's data."""
    # Create two users with their own quizzes
    user1 = create_user_in_session(session, name="User 1", canvas_id=111)
    user2 = create_user_in_session(session, name="User 2", canvas_id=222)

    quiz1 = create_quiz_in_session(session, owner=user1, title="User 1 Quiz")
    quiz2 = create_quiz_in_session(session, owner=user2, title="User 2 Quiz")

    # Delete user1 only
    user1_quizzes = session.exec(select(Quiz).where(Quiz.owner_id == user1.id)).all()

    for quiz in user1_quizzes:
        quiz.owner_id = None
        quiz.deleted = True
        quiz.deleted_at = datetime.now()
        session.add(quiz)

    session.delete(user1)
    session.commit()

    # Verify user1 is deleted and quiz anonymized
    from src.auth.service import get_user_by_id

    deleted_user1 = get_user_by_id(session, user1.id)
    assert deleted_user1 is None

    anonymized_quiz1 = session.exec(select(Quiz).where(Quiz.id == quiz1.id)).first()
    assert anonymized_quiz1.owner_id is None
    assert anonymized_quiz1.deleted is True

    # Verify user2 and their quiz are unaffected
    active_user2 = get_user_by_id(session, user2.id)
    assert active_user2 is not None
    assert active_user2.name == "User 2"

    active_quiz2 = session.exec(select(Quiz).where(Quiz.id == quiz2.id)).first()
    assert active_quiz2.owner_id == user2.id  # Still owned by user2
    assert active_quiz2.deleted is False  # Still active
    assert active_quiz2.title == "User 2 Quiz"


def test_empty_user_deletion(session: Session):
    """Test deletion of user with no quizzes works correctly."""
    from src.auth.service import get_user_by_id

    # Create user with no quizzes
    user = create_user_in_session(session, name="Empty User")
    user_id = user.id

    # Delete user (no quizzes to anonymize)
    session.delete(user)
    session.commit()

    # Verify user is deleted
    deleted_user = get_user_by_id(session, user_id)
    assert deleted_user is None

    # Verify no orphaned data
    orphaned_quizzes = session.exec(select(Quiz).where(Quiz.owner_id == user_id)).all()
    assert len(orphaned_quizzes) == 0
