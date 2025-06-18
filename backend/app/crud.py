from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.security import token_encryption
from app.models import User, UserCreate


def create_user(session: Session, user_create: UserCreate) -> User:
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
    user.refresh_token = None
    user.expires_at = None

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_user_by_canvas_id(session: Session, canvas_id: str) -> User | None:
    statement = select(User).where(User.canvas_id == canvas_id)
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_decrypted_access_token(user: User) -> str:
    """Get decrypted access token"""
    return token_encryption.decrypt_token(user.access_token)


def get_decrypted_refresh_token(user: User) -> str | None:
    """Get decrypted refresh token"""
    if user.refresh_token:
        return token_encryption.decrypt_token(user.refresh_token)
    return None
