from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.api.models import User
from backend.db import get_session
from backend.config import Settings

# Load settings once
settings = Settings()

# Configure OAuth2 scheme
# tokenUrl can be a dummy one if you don't have a direct username/password token endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class TokenData(BaseModel):
    user_id: Optional[int] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use default expiration from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def verify_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        user_id_str: Optional[str] = payload.get("user_id") # Changed from "sub" to "user_id"
        if user_id_str is None:
            raise credentials_exception

        # Attempt to convert user_id to int
        try:
            user_id = int(user_id_str)
        except ValueError:
            raise credentials_exception # If user_id is not a valid integer

        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    return token_data

async def get_current_user(
    token_data: TokenData = Depends(verify_token),
    session: Session = Depends(get_session)
) -> User:
    if token_data.user_id is None:
        # This case should ideally be caught by verify_token if user_id is None in payload
        raise HTTPException(status_code=404, detail="User ID not in token")

    user = session.get(User, token_data.user_id) # SQLModel's way to get by primary key

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
