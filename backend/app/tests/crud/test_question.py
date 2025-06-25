import time
import uuid
from datetime import datetime

from sqlmodel import Session

from app import crud
from app.models import QuestionCreate, QuestionUpdate, QuizCreate


def test_create_question(db: Session, user_id: uuid.UUID) -> None:
    """Test creating a question with all fields."""
    # First create a quiz
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Create a question
    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="What is the capital of France?",
        option_a="Paris",
        option_b="London",
        option_c="Berlin",
        option_d="Madrid",
        correct_answer="A",
    )

    question = crud.create_question(session=db, question_create=question_in)

    # Check basic fields
    assert question.id is not None
    assert question.quiz_id == quiz.id
    assert question.question_text == "What is the capital of France?"
    assert question.option_a == "Paris"
    assert question.option_b == "London"
    assert question.option_c == "Berlin"
    assert question.option_d == "Madrid"
    assert question.correct_answer == "A"
    assert question.is_approved is False
    assert question.approved_at is None
    assert question.created_at is not None
    assert question.updated_at is not None


def test_get_question_by_id(db: Session, user_id: uuid.UUID) -> None:
    """Test retrieving a question by ID."""
    # Create quiz and question
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="What is 2+2?",
        option_a="3",
        option_b="4",
        option_c="5",
        option_d="6",
        correct_answer="B",
    )
    created_question = crud.create_question(session=db, question_create=question_in)

    # Retrieve the question
    question = crud.get_question_by_id(session=db, question_id=created_question.id)

    assert question is not None
    assert question.id == created_question.id
    assert question.question_text == "What is 2+2?"
    assert question.correct_answer == "B"


def test_get_question_by_id_not_found(db: Session) -> None:
    """Test retrieving a non-existent question."""
    fake_id = uuid.uuid4()
    question = crud.get_question_by_id(session=db, question_id=fake_id)
    assert question is None


def test_get_questions_by_quiz_id(db: Session, user_id: uuid.UUID) -> None:
    """Test retrieving all questions for a quiz."""
    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Create multiple questions
    question1_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question 1",
        option_a="A1",
        option_b="B1",
        option_c="C1",
        option_d="D1",
        correct_answer="A",
    )
    question2_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question 2",
        option_a="A2",
        option_b="B2",
        option_c="C2",
        option_d="D2",
        correct_answer="B",
    )

    crud.create_question(session=db, question_create=question1_in)
    crud.create_question(session=db, question_create=question2_in)

    # Retrieve all questions for the quiz
    questions = crud.get_questions_by_quiz_id(session=db, quiz_id=quiz.id)

    assert len(questions) == 2
    question_texts = [q.question_text for q in questions]
    assert "Question 1" in question_texts
    assert "Question 2" in question_texts


def test_get_questions_by_quiz_id_empty(db: Session, user_id: uuid.UUID) -> None:
    """Test retrieving questions for a quiz with no questions."""
    # Create quiz without questions
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Empty Quiz",
        selected_modules={173467: "Module 1"},
        title="Empty Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    questions = crud.get_questions_by_quiz_id(session=db, quiz_id=quiz.id)
    assert len(questions) == 0


def test_update_question(db: Session, user_id: uuid.UUID) -> None:
    """Test updating a question."""
    # Create quiz and question
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Original question",
        option_a="Original A",
        option_b="Original B",
        option_c="Original C",
        option_d="Original D",
        correct_answer="A",
    )
    question = crud.create_question(session=db, question_create=question_in)

    # Add small delay to ensure different timestamp
    time.sleep(0.01)

    # Update some fields
    question_update = QuestionUpdate(
        question_text="Updated question",
        option_a="Updated A",
        correct_answer="B",
    )

    updated_question = crud.update_question(
        session=db, question_id=question.id, question_update=question_update
    )

    assert updated_question is not None
    assert updated_question.question_text == "Updated question"
    assert updated_question.option_a == "Updated A"
    assert updated_question.option_b == "Original B"  # Unchanged
    assert updated_question.correct_answer == "B"
    assert updated_question.updated_at is not None
    assert question.updated_at is not None
    # Timestamps should be different due to the update
    assert updated_question.updated_at >= question.updated_at


def test_update_question_not_found(db: Session) -> None:
    """Test updating a non-existent question."""
    fake_id = uuid.uuid4()
    question_update = QuestionUpdate(question_text="Updated question")

    updated_question = crud.update_question(
        session=db, question_id=fake_id, question_update=question_update
    )
    assert updated_question is None


def test_approve_question(db: Session, user_id: uuid.UUID) -> None:
    """Test approving a question."""
    # Create quiz and question
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question to approve",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    question = crud.create_question(session=db, question_create=question_in)

    # Verify initially not approved
    assert question.is_approved is False
    assert question.approved_at is None

    # Add small delay to ensure different timestamp
    time.sleep(0.01)

    # Approve the question
    approved_question = crud.approve_question(session=db, question_id=question.id)

    assert approved_question is not None
    assert approved_question.is_approved is True
    assert approved_question.approved_at is not None
    assert isinstance(approved_question.approved_at, datetime)
    assert approved_question.updated_at is not None
    assert question.updated_at is not None
    # Timestamps should be different due to the approval
    assert approved_question.updated_at >= question.updated_at


def test_approve_question_not_found(db: Session) -> None:
    """Test approving a non-existent question."""
    fake_id = uuid.uuid4()
    approved_question = crud.approve_question(session=db, question_id=fake_id)
    assert approved_question is None


def test_delete_question(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a question."""
    # Create quiz and question
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question to delete",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    question = crud.create_question(session=db, question_create=question_in)

    # Delete the question
    success = crud.delete_question(
        session=db, question_id=question.id, quiz_owner_id=user_id
    )
    assert success is True

    # Verify question is deleted
    deleted_question = crud.get_question_by_id(session=db, question_id=question.id)
    assert deleted_question is None


def test_delete_question_unauthorized(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a question by a non-owner."""
    # Create quiz and question
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    question_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question to delete",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
    )
    question = crud.create_question(session=db, question_create=question_in)

    # Try to delete with different user ID
    other_user_id = uuid.uuid4()
    success = crud.delete_question(
        session=db, question_id=question.id, quiz_owner_id=other_user_id
    )
    assert success is False

    # Verify question still exists
    existing_question = crud.get_question_by_id(session=db, question_id=question.id)
    assert existing_question is not None


def test_delete_question_not_found(db: Session, user_id: uuid.UUID) -> None:
    """Test deleting a non-existent question."""
    fake_id = uuid.uuid4()
    success = crud.delete_question(
        session=db, question_id=fake_id, quiz_owner_id=user_id
    )
    assert success is False


def test_get_approved_questions_by_quiz_id(db: Session, user_id: uuid.UUID) -> None:
    """Test retrieving only approved questions for a quiz."""
    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Create questions (some approved, some not)
    question1_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Approved question",
        option_a="A1",
        option_b="B1",
        option_c="C1",
        option_d="D1",
        correct_answer="A",
    )
    question2_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Unapproved question",
        option_a="A2",
        option_b="B2",
        option_c="C2",
        option_d="D2",
        correct_answer="B",
    )

    question1 = crud.create_question(session=db, question_create=question1_in)
    crud.create_question(session=db, question_create=question2_in)

    # Approve only the first question
    crud.approve_question(session=db, question_id=question1.id)

    # Get only approved questions
    approved_questions = crud.get_approved_questions_by_quiz_id(
        session=db, quiz_id=quiz.id
    )

    assert len(approved_questions) == 1
    assert approved_questions[0].question_text == "Approved question"
    assert approved_questions[0].is_approved is True


def test_get_question_counts_by_quiz_id(db: Session, user_id: uuid.UUID) -> None:
    """Test getting question counts for a quiz."""
    # Create quiz
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Test Course",
        selected_modules={173467: "Module 1"},
        title="Test Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    # Create questions
    question1_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question 1",
        option_a="A1",
        option_b="B1",
        option_c="C1",
        option_d="D1",
        correct_answer="A",
    )
    question2_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question 2",
        option_a="A2",
        option_b="B2",
        option_c="C2",
        option_d="D2",
        correct_answer="B",
    )
    question3_in = QuestionCreate(
        quiz_id=quiz.id,
        question_text="Question 3",
        option_a="A3",
        option_b="B3",
        option_c="C3",
        option_d="D3",
        correct_answer="C",
    )

    question1 = crud.create_question(session=db, question_create=question1_in)
    question2 = crud.create_question(session=db, question_create=question2_in)
    crud.create_question(session=db, question_create=question3_in)

    # Approve two questions
    crud.approve_question(session=db, question_id=question1.id)
    crud.approve_question(session=db, question_id=question2.id)

    # Get counts
    counts = crud.get_question_counts_by_quiz_id(session=db, quiz_id=quiz.id)

    assert counts["total"] == 3
    assert counts["approved"] == 2


def test_get_question_counts_empty_quiz(db: Session, user_id: uuid.UUID) -> None:
    """Test getting question counts for a quiz with no questions."""
    # Create quiz without questions
    quiz_in = QuizCreate(
        canvas_course_id=12345,
        canvas_course_name="Empty Quiz",
        selected_modules={173467: "Module 1"},
        title="Empty Quiz",
        question_count=10,
        llm_model="gpt-4o",
        llm_temperature=1,
    )
    quiz = crud.create_quiz(session=db, quiz_create=quiz_in, owner_id=user_id)

    counts = crud.get_question_counts_by_quiz_id(session=db, quiz_id=quiz.id)

    assert counts["total"] == 0
    assert counts["approved"] == 0
