from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, asc, col, desc, func, select

from app.models import (
    Question,
    QuestionCreate,
    QuestionUpdate,
)
from app.quiz.models import Quiz
from app.quiz.schemas import QuizCreate


async def get_quiz_for_update(session: AsyncSession, quiz_id: UUID) -> Quiz | None:
    """
    Retrieve a quiz with a lock for updating.

    **Parameters:**
        session (AsyncSession): Async database session for the query
        quiz_id (UUID): Quiz UUID to look up

    **Returns:**
        Quiz | None: Quiz object if found, None if not found
    """
    result = await session.execute(
        select(Quiz).where(Quiz.id == quiz_id).with_for_update()
    )
    return result.scalar_one_or_none()


# User CRUD operations moved to app.auth.service.AuthService


def create_quiz(session: Session, quiz_create: QuizCreate, owner_id: UUID) -> Quiz:
    """
    Create a new quiz with the specified settings.

    **Parameters:**
        session (Session): Database session for the transaction
        quiz_create (QuizCreate): Quiz creation data including course info and LLM settings
        owner_id (UUID): ID of the user creating the quiz

    **Returns:**
        Quiz: The newly created quiz object with generated UUID and timestamps
    """

    quiz = Quiz(
        **quiz_create.model_dump(),
        owner_id=owner_id,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    return quiz


def get_quiz_by_id(session: Session, quiz_id: UUID) -> Quiz | None:
    """
    Retrieve a quiz by its UUID.

    **Parameters:**
        session (Session): Database session for the query
        quiz_id (UUID): Quiz UUID to look up

    **Returns:**
        Quiz | None: Quiz object if found, None if not found
    """
    return session.get(Quiz, quiz_id)


def get_user_quizzes(session: Session, user_id: UUID) -> list[Quiz]:
    """
    Retrieve all quizzes created by a specific user.

    **Parameters:**
        session (Session): Database session for the query
        user_id (UUID): User UUID to get quizzes for

    **Returns:**
        list[Quiz]: List of quiz objects owned by the user
    """
    statement = (
        select(Quiz).where(Quiz.owner_id == user_id).order_by(desc(Quiz.created_at))
    )
    return list(session.exec(statement).all())


def delete_quiz(session: Session, quiz_id: UUID, user_id: UUID) -> bool:
    """
    Delete a quiz by its UUID, with ownership verification.

    **Parameters:**
        session (Session): Database session for the transaction
        quiz_id (UUID): Quiz UUID to delete
        user_id (UUID): User UUID to verify ownership

    **Returns:**
        bool: True if quiz was deleted, False if quiz not found or not owned by user

    **Security:**
        - Verifies ownership before deletion to prevent unauthorized access
        - Only the quiz owner can delete their own quizzes
        - Returns False for both non-existent quizzes and unauthorized access
    """
    quiz = session.get(Quiz, quiz_id)
    if not quiz or quiz.owner_id != user_id:
        return False

    session.delete(quiz)
    session.commit()
    return True


async def get_content_from_quiz(
    session: AsyncSession, quiz_id: UUID
) -> dict[str, Any] | None:
    """
    Retrieve the extracted content from a quiz by its UUID asynchronously.

    **Parameters:**
        session (AsyncSession): Async database session for the query
        quiz_id (UUID): Quiz UUID to get extracted content from

    **Returns:**
        dict[str, Any] | None: The extracted content as a dictionary if found and available,
                              None if quiz not found or no content extracted yet
    """
    quiz = await session.get(Quiz, quiz_id)
    if not quiz:
        return None
    return quiz.extracted_content


# Question CRUD operations


def create_question(session: Session, question_create: QuestionCreate) -> Question:
    """
    Create a new question for a quiz.

    **Parameters:**
        session (Session): Database session for the transaction
        question_create (QuestionCreate): Question data including text, options, and correct answer

    **Returns:**
        Question: The newly created question object with generated UUID and timestamps
    """
    question_data = question_create.model_dump()
    current_time = datetime.now(timezone.utc)
    question_data["updated_at"] = current_time

    db_question = Question.model_validate(question_data)
    session.add(db_question)
    session.commit()
    session.refresh(db_question)
    return db_question


def get_question_by_id(session: Session, question_id: UUID) -> Question | None:
    """
    Retrieve a question by its UUID.

    **Parameters:**
        session (Session): Database session for the query
        question_id (UUID): Question UUID to look up

    **Returns:**
        Question | None: Question object if found, None if not found
    """
    return session.get(Question, question_id)


def get_questions_by_quiz_id(session: Session, quiz_id: UUID) -> list[Question]:
    """
    Retrieve all questions for a specific quiz.

    **Parameters:**
        session (Session): Database session for the query
        quiz_id (UUID): Quiz UUID to get questions for

    **Returns:**
        list[Question]: List of question objects for the quiz, ordered by creation date and ID for stability
    """
    statement = (
        select(Question)
        .where(Question.quiz_id == quiz_id)
        .order_by(asc(Question.created_at), asc(Question.id))
    )
    return list(session.exec(statement).all())


def update_question(
    session: Session, question_id: UUID, question_update: QuestionUpdate
) -> Question | None:
    """
    Update a question with new data.

    **Parameters:**
        session (Session): Database session for the transaction
        question_id (UUID): Question UUID to update
        question_update (QuestionUpdate): New question data (only provided fields will be updated)

    **Returns:**
        Question | None: Updated question object if found, None if not found
    """
    question = session.get(Question, question_id)
    if not question:
        return None

    # Update only provided fields
    update_data = question_update.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(question, field, value)

        question.updated_at = datetime.now(timezone.utc)
        session.add(question)
        session.commit()
        session.refresh(question)

    return question


def approve_question(session: Session, question_id: UUID) -> Question | None:
    """
    Approve a question by setting is_approved to True and recording approval timestamp.

    **Parameters:**
        session (Session): Database session for the transaction
        question_id (UUID): Question UUID to approve

    **Returns:**
        Question | None: Approved question object if found, None if not found
    """
    question = session.get(Question, question_id)
    if not question:
        return None

    question.is_approved = True
    question.approved_at = datetime.now(timezone.utc)
    question.updated_at = datetime.now(timezone.utc)

    session.add(question)
    session.commit()
    session.refresh(question)
    return question


def delete_question(session: Session, question_id: UUID, quiz_owner_id: UUID) -> bool:
    """
    Delete a question by its UUID, with quiz ownership verification.

    **Parameters:**
        session (Session): Database session for the transaction
        question_id (UUID): Question UUID to delete
        quiz_owner_id (UUID): User UUID to verify quiz ownership

    **Returns:**
        bool: True if question was deleted, False if question not found or not authorized

    **Security:**
        - Verifies quiz ownership before deletion to prevent unauthorized access
        - Only the quiz owner can delete questions from their quizzes
    """
    question = session.get(Question, question_id)
    if not question:
        return False

    # Get the quiz to verify ownership
    quiz = session.get(Quiz, question.quiz_id)
    if not quiz or quiz.owner_id != quiz_owner_id:
        return False

    session.delete(question)
    session.commit()
    return True


def get_approved_questions_by_quiz_id(
    session: Session, quiz_id: UUID
) -> list[Question]:
    """
    Retrieve all approved questions for a specific quiz.

    **Parameters:**
        session (Session): Database session for the query
        quiz_id (UUID): Quiz UUID to get approved questions for

    **Returns:**
        list[Question]: List of approved question objects for the quiz
    """
    statement = (
        select(Question)
        .where(Question.quiz_id == quiz_id, Question.is_approved == True)  # noqa: E712
        .order_by(asc(Question.created_at))
    )
    return list(session.exec(statement).all())


async def get_approved_questions_by_quiz_id_async(
    session: AsyncSession, quiz_id: UUID
) -> list[Question]:
    """
    Retrieve all approved questions for a specific quiz asynchronously.

    **Parameters:**
        session (AsyncSession): Async database session for the query
        quiz_id (UUID): Quiz UUID to get approved questions for

    **Returns:**
        list[Question]: List of approved question objects for the quiz
    """
    statement = (
        select(Question)
        .where(Question.quiz_id == quiz_id, Question.is_approved == True)  # noqa: E712
        .order_by(asc(Question.created_at))
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


def get_question_counts_by_quiz_id(session: Session, quiz_id: UUID) -> dict[str, int]:
    """
    Get question counts (total and approved) for a quiz.

    **Parameters:**
        session (Session): Database session for the query
        quiz_id (UUID): Quiz UUID to get counts for

    **Returns:**
        dict: Dictionary with 'total' and 'approved' question counts
    """
    statement = select(
        func.count(col(Question.id)), func.sum(cast(col(Question.is_approved), Integer))
    ).where(Question.quiz_id == quiz_id)

    result = session.exec(statement).first()

    if result:
        total, approved = result
        return {
            "total": total or 0,
            "approved": approved or 0,
        }
    else:
        return {
            "total": 0,
            "approved": 0,
        }
