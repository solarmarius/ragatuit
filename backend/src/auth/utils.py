"""
Utility functions for authentication module.
"""

import base64
import functools
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import jwt

from src.config import get_logger, settings

logger = get_logger("auth_utils")

ALGORITHM = "HS256"


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    **Parameters:**
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time

    **Returns:**
        str: Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_oauth_state() -> str:
    """Generate a secure random state for OAuth."""
    return secrets.token_urlsafe(32)


def verify_oauth_state(state: str | None, expected_state: str | None) -> bool:
    """
    Verify OAuth state parameter.

    **Parameters:**
        state: State from OAuth callback
        expected_state: Expected state value

    **Returns:**
        bool: True if states match, False otherwise
    """
    if not state or not expected_state:
        return False
    return secrets.compare_digest(state, expected_state)


# Token Encryption Functions
@functools.lru_cache(maxsize=1)
def _get_token_cipher() -> Fernet:
    """
    Get or create Fernet cipher for token encryption.

    Lazy initialization with caching ensures the cipher is created only once
    and reused across all encryption/decryption operations. Uses the same
    key derivation as the original TokenEncryption class.

    Returns:
        Fernet: Cipher instance for token encryption/decryption
    """
    # Derive encryption key from SECRET_KEY to keep it centralized
    key_material = settings.SECRET_KEY.encode()[:32]  # Take first 32 bytes
    key = base64.urlsafe_b64encode(key_material.ljust(32, b"0"))  # Pad to 32 bytes
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt a sensitive token for secure database storage.

    Encrypts Canvas OAuth tokens and other sensitive strings to protect them
    in the database. Uses Fernet encryption with base64url encoding for safe
    storage in text database fields.

    **Parameters:**
        token (str): The plaintext token to encrypt (Canvas access/refresh token)

    **Returns:**
        str: Base64url-encoded encrypted token safe for database storage

    **Security:**
    - Uses AES 128 encryption with authentication
    - Each encryption includes a unique timestamp and nonce
    - Encrypted tokens are tamper-proof

    **Example:**
        >>> encrypted = encrypt_token("canvas_secret_token_123")
        >>> print(encrypted)  # "gAAAAABhZ..."
    """
    if not token:
        return ""
    cipher = _get_token_cipher()
    return cipher.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token encrypted with encrypt_token.

    Decrypts Canvas OAuth tokens for use in API calls. Validates authenticity
    to ensure the token hasn't been tampered with in storage.

    **Parameters:**
        encrypted_token (str): The encrypted token from database storage

    **Returns:**
        str: The original plaintext token

    **Raises:**
        cryptography.fernet.InvalidToken: If token is corrupted or tampered with

    **Security:**
    - Verifies authenticity before decryption
    - Fails safely if token is corrupted
    - Should be called within try/except blocks

    **Example:**
        >>> decrypted = decrypt_token("gAAAAABhZ...")
        >>> print(decrypted)  # "canvas_secret_token_123"
    """
    if not encrypted_token:
        return ""
    cipher = _get_token_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()
