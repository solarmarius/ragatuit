import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class TokenEncryption:
    """Handles encryption/decryption of sensitive tokens for storage"""

    def __init__(self):
        # Derive encryption key from SECRET_KEY to keep it centralized
        key_material = settings.SECRET_KEY.encode()[:32]  # Take first 32 bytes
        key = base64.urlsafe_b64encode(key_material.ljust(32, b"0"))  # Pad to 32 bytes
        self.cipher = Fernet(key)

    def encrypt_token(self, token: str) -> str:
        """Encrypt a token for database storage"""
        if not token:
            return token
        encrypted = self.cipher.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token from database storage"""
        if not encrypted_token:
            return encrypted_token
        try:
            decoded = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            raise ValueError("Invalid encrypted token")


# Global instance
token_encryption = TokenEncryption()
