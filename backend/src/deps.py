"""Database session dependencies."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from src.database import engine


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields a SQLModel Session that automatically closes after the request.
    This ensures proper connection handling and prevents connection leaks.

    Usage:
        @app.get("/items")
        def get_items(session: SessionDep):
            return session.exec(select(Item)).all()
    """
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
