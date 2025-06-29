from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, asc, desc, select

from app.core.security import token_encryption
from app.models import (
    Question,
    QuestionCreate,
    QuestionUpdate,
    Quiz,
    QuizCreate,
    User,
    UserCreate,
)


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


async def update_quiz_content_extraction_status(
    session: AsyncSession,
    quiz: Quiz,
    status: str,
    content: dict[str, Any] | None = None,
) -> None:
    """
    Update the content extraction status and content of a quiz.

    **Parameters:**
        session (AsyncSession): Async database session for the transaction
        quiz (Quiz): The quiz object to update
        status (str): The new content extraction status
        content (dict | None): The extracted content, if any
    """
    quiz.content_extraction_status = status
    if content is not None:
        quiz.extracted_content = content
        quiz.content_extracted_at = datetime.now(timezone.utc)
    await session.commit()


async def update_quiz_llm_generation_status(
    session: AsyncSession, quiz: Quiz, status: str
) -> None:
    """
    Update the LLM generation status of a quiz.

    **Parameters:**
        session (AsyncSession): Async database session for the transaction
        quiz (Quiz): The quiz object to update
        status (str): The new LLM generation status
    """
    quiz.llm_generation_status = status
    await session.commit()


def create_user(session: Session, user_create: UserCreate) -> User:
    """
    Create a new user account with encrypted Canvas OAuth tokens.

    Creates a new user record in the database with Canvas OAuth credentials
    securely encrypted for storage. This is called during the OAuth callback
    when a new user authenticates with Canvas for the first time.

    **Parameters:**
        session (Session): Database session for the transaction
        user_create (UserCreate): User data containing Canvas ID, name, and OAuth tokens

    **Returns:**
        User: The newly created user object with encrypted tokens and generated UUID

    **Security:**
    - Canvas access and refresh tokens are encrypted before database storage
    - Uses secure token encryption to protect OAuth credentials at rest
    - Generated UUID serves as internal user identifier separate from Canvas ID

    **Database Operations:**
    1. Validates user data against UserCreate schema
    2. Encrypts sensitive Canvas OAuth tokens
    3. Inserts new user record with auto-generated UUID and timestamps
    4. Commits transaction and refreshes object with database-generated values

    **Fields Set:**
    - `id`: Auto-generated UUID (primary key)
    - `canvas_id`: Canvas LMS user ID (unique)
    - `name`: User's display name from Canvas
    - `access_token`: Encrypted Canvas OAuth access token
    - `refresh_token`: Encrypted Canvas OAuth refresh token
    - `created_at`: Auto-generated timestamp
    - `expires_at`: Set by default, updated during token refresh

    **Example:**
        >>> user_data = UserCreate(
        ...     canvas_id=12345,
        ...     name="John Doe",
        ...     access_token="canvas_access_123",
        ...     refresh_token="canvas_refresh_456"
        ... )
        >>> user = create_user(session, user_data)
        >>> print(user.id)  # UUID('...')
        >>> print(user.canvas_id)  # 12345

    **Note:**
    This function assumes the Canvas ID is unique and not already in use.
    Check with get_user_by_canvas_id() first to handle existing users.
    """
    db_obj = User.model_validate(
        user_create,
        update={
            "canvas_id": user_create.canvas_id,
            "name": user_create.name,
            "access_token": token_encryption.encrypt_token(user_create.access_token),
            "refresh_token": token_encryption.encrypt_token(user_create.refresh_token),
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user_tokens(
    session: Session,
    user: User,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> User:
    """Update user's Canvas tokens"""
    # Encrypt tokens
    user.access_token = token_encryption.encrypt_token(access_token)
    if refresh_token:
        user.refresh_token = token_encryption.encrypt_token(refresh_token)

    user.expires_at = expires_at
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def clear_user_tokens(session: Session, user: User) -> User:
    """Clear user's Canvas tokens"""
    user.access_token = ""
    user.refresh_token = ""
    user.expires_at = None

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_canvas_id(session: Session, canvas_id: int) -> User | None:
    """
    Retrieve a user by their Canvas LMS user ID.

    Looks up a user account using their Canvas LMS identifier. This is the primary
    method for finding existing users during OAuth authentication flow.

    **Parameters:**
        session (Session): Database session for the query
        canvas_id (int): Canvas LMS user ID (unique identifier from Canvas)

    **Returns:**
        User | None: User object if found, None if no user exists with this Canvas ID

    **Usage:**
    - OAuth callback: Check if user already exists before creating new account
    - Authentication: Link Canvas identity to internal user account
    - User lookup: Find user based on Canvas identity

    **Database Query:**
    Performs indexed lookup on canvas_id field (unique constraint ensures at most one result).

    **Example:**
        >>> user = get_user_by_canvas_id(session, 12345)
        >>> if user:
        ...     print(f"Found user: {user.name}")
        ... else:
        ...     print("User not found, create new account")

    **Security:**
    Canvas ID is not considered sensitive but should only come from trusted Canvas OAuth responses.
    """
    statement = select(User).where(User.canvas_id == canvas_id)
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    """
    Retrieve a user by their internal UUID.

    Looks up a user account using the internal UUID primary key. This is used
    for authentication middleware and API operations where the user ID comes
    from a validated JWT token.

    **Parameters:**
        session (Session): Database session for the query
        user_id (UUID): Internal user UUID (from JWT token subject)

    **Returns:**
        User | None: User object if found, None if UUID doesn't exist

    **Usage:**
    - JWT authentication: Validate token subject and load user data
    - API operations: Load user for authenticated requests
    - User validation: Ensure user still exists after token was issued

    **Performance:**
    Uses primary key lookup - fastest possible user query.

    **Example:**
        >>> from uuid import UUID
        >>> user_uuid = UUID('12345678-1234-5678-9abc-123456789abc')
        >>> user = get_user_by_id(session, user_uuid)
        >>> if user:
        ...     print(f"Authenticated user: {user.name}")
        ... else:
        ...     raise HTTPException(404, "User not found")

    **Security:**
    UUID should only come from validated JWT tokens. Random UUID guessing is
    cryptographically infeasible.
    """
    return session.get(User, user_id)


def get_decrypted_access_token(user: User) -> str:
    """Get decrypted access token"""
    return token_encryption.decrypt_token(user.access_token)


def get_decrypted_refresh_token(user: User) -> str:
    """Get decrypted refresh token"""
    return token_encryption.decrypt_token(user.refresh_token)


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
    statement = select(Question).where(Question.quiz_id == quiz_id)
    questions = list(session.exec(statement).all())

    total_count = len(questions)
    approved_count = sum(1 for q in questions if q.is_approved)

    return {
        "total": total_count,
        "approved": approved_count,
    }
