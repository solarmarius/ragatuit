import uuid

from sqlmodel import Session, desc, select

from app.models import CanvasToken, Item, ItemCreate, TokenCreate, User, UserCreate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    """Create a new user from Canvas OAuth data"""
    db_obj = User.model_validate(
        user_create,
        update={
            "canvas_user_id": user_create.canvas_user_id,
            "canvas_base_url": user_create.canvas_base_url,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_user_by_canvas_id(*, session: Session, canvas_user_id: str) -> User | None:
    """Get user by Canvas user ID and base URL"""
    statement = select(User).where(User.canvas_user_id == canvas_user_id)
    return session.exec(statement).first()


def create_canvas_token(*, session: Session, canvas_create: TokenCreate) -> CanvasToken:
    """Create a new Canvas token for a user"""
    db_obj = CanvasToken.model_validate(
        canvas_create,
        update={
            "user_id": canvas_create.user_id,
            "access_token": canvas_create.access_token,
            "refresh_token": canvas_create.refresh_token,
            "token_type": canvas_create.token_type,
            "expires_at": canvas_create.expires_at,
            "scope": canvas_create.scope,
            "canvas_user_id": canvas_create.user_id,
            "canvas_base_url": canvas_create.canvas_base_url,
        },
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_canvas_token(*, session: Session, user_id: uuid.UUID) -> CanvasToken | None:
    """Get the most recent Canvas token for a user"""
    statement = (
        select(CanvasToken)
        .where(CanvasToken.user_id == user_id)
        .order_by(desc(CanvasToken.created_at))
    )
    return session.exec(statement).first()


def delete_canvas_tokens(*, session: Session, user_id: uuid.UUID) -> bool:
    """Delete all Canvas tokens for a user (for logout/disconnect)"""
    statement = select(CanvasToken).where(CanvasToken.user_id == user_id)
    tokens = session.exec(statement).all()

    for token in tokens:
        session.delete(token)

    session.commit()
    return True


def authenticate(*, session: Session, canvas_user_id) -> User | None:
    db_user = get_user_by_canvas_id(session=session, canvas_user_id=canvas_user_id)
    if not db_user:
        return None

    token = get_canvas_token(session=session, user_id=canvas_user_id)
    if not token:
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item
