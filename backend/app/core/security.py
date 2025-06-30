import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from fastapi import HTTPException
from jose import jwt
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import User
from app.services.canvas_auth import refresh_canvas_token

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    """
    Create a JWT access token for user authentication.

    Generates a signed JWT token containing the user identifier and expiration time.
    This token is used for authenticating API requests and maintaining user sessions.

    **Parameters:**
        subject (str | Any): User identifier (typically UUID) to embed in token
        expires_delta (timedelta): How long the token should remain valid

    **Returns:**
        str: Encoded JWT token string that can be used in Authorization headers

    **Security:**
        - Tokens are signed with HMAC-SHA256 using the application SECRET_KEY
        - Includes expiration timestamp to prevent indefinite token validity
        - Subject is always converted to string for consistent token format

    **Example:**
        >>> token = create_access_token("user123", timedelta(hours=24))
        >>> # Returns: "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

    **Note:**
        This function does not validate the subject or check user existence.
        Token validation and user lookup happens in the authentication middleware.
    """
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class TokenEncryption:
    """Handles encryption/decryption of sensitive tokens for storage"""

    def __init__(self) -> None:
        """
        Initialize TokenEncryption with Fernet cipher for secure token storage.

        Derives a 32-byte encryption key from the application SECRET_KEY to ensure
        consistent encryption across application restarts while maintaining security.

        **Security Considerations:**
        - Uses first 32 bytes of SECRET_KEY for deterministic key derivation
        - Pads with zeros if SECRET_KEY is shorter than 32 bytes
        - All tokens encrypted with this instance use the same key
        - Key derivation ensures encrypted tokens remain decryptable after restarts

        **Cryptography:**
        - Uses Fernet symmetric encryption (AES 128 in CBC mode)
        - Includes authentication to prevent tampering
        - Base64url encoding for database-safe storage

        **Raises:**
        - May raise cryptography exceptions if SECRET_KEY format is invalid
        """
        # Derive encryption key from SECRET_KEY to keep it centralized
        key_material = settings.SECRET_KEY.encode()[:32]  # Take first 32 bytes
        key = base64.urlsafe_b64encode(key_material.ljust(32, b"0"))  # Pad to 32 bytes
        self.cipher = Fernet(key)

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a sensitive token for secure database storage.

        Encrypts Canvas OAuth tokens and other sensitive strings to protect them
        in the database. Uses Fernet encryption with base64url encoding for safe
        storage in text database fields.

        **Parameters:**
            token (str): The plaintext token to encrypt (Canvas access/refresh token)

        **Returns:**
            str: Base64url-encoded encrypted token safe for database storage

        **Behavior:**
        - Empty or None tokens are returned unchanged (no encryption)
        - Non-empty tokens are encrypted and base64url encoded
        - Output is always a valid UTF-8 string safe for database text fields

        **Security:**
        - Uses authenticated encryption (prevents tampering)
        - Each encryption produces different output (includes random IV)
        - Encrypted tokens cannot be decrypted without the same SECRET_KEY

        **Example:**
            >>> encryptor = TokenEncryption()
            >>> encrypted = encryptor.encrypt_token("canvas_token_123")
            >>> # Returns: "Z0FBQUFBQmh..." (base64url encoded encrypted data)

        **Database Storage:**
        Safe to store in VARCHAR/TEXT fields, URL-safe characters only.
        """
        if not token:
            return token
        encrypted = self.cipher.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token retrieved from database storage.

        Reverses the encryption process to recover the original plaintext token
        from its encrypted database representation.

        **Parameters:**
            encrypted_token (str): Base64url-encoded encrypted token from database

        **Returns:**
            str: Original plaintext token (Canvas access/refresh token)

        **Behavior:**
        - Empty or None tokens are returned unchanged
        - Validates encrypted token format and authenticity
        - Returns original plaintext if decryption succeeds

        **Error Handling:**
        - Raises ValueError for invalid encrypted tokens
        - Catches all decryption/encoding errors to prevent information leakage
        - Safe to call with potentially corrupted database data

        **Raises:**
            ValueError: If encrypted_token is malformed, corrupted, or encrypted
                       with a different key

        **Security:**
        - Authenticated decryption prevents tampered data from being accepted
        - Fails securely - no partial decryption or error details exposed
        - Only tokens encrypted with the same SECRET_KEY can be decrypted

        **Example:**
            >>> encryptor = TokenEncryption()
            >>> plaintext = encryptor.decrypt_token("Z0FBQUFBQmh...")
            >>> # Returns: "canvas_token_123" (original token)

        **Database Recovery:**
        Use this to retrieve Canvas tokens for API calls from encrypted storage.
        """
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


async def ensure_valid_canvas_token(session: Session, user: User) -> str:
    """
    Ensure Canvas token is valid, refresh if needed.
    Returns a valid Canvas access token.
    """
    # Check if token expires within 5 minutes
    if user.expires_at:
        expires_soon = datetime.now(timezone.utc) + timedelta(minutes=5)

        # Ensure both datetimes are timezone-aware for comparison
        if user.expires_at.tzinfo is None:
            # If stored datetime is naive, assume it's UTC
            user_expires_at = user.expires_at.replace(tzinfo=timezone.utc)
        else:
            user_expires_at = user.expires_at

        if user_expires_at <= expires_soon:
            try:
                await refresh_canvas_token(user, session)
            except HTTPException as e:
                if e.status_code == 401:
                    # Invalid canvas token - clear and force re-login
                    crud.clear_user_tokens(session, user)
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas session expired, Please re-login.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas temporarily unavailable. Please try again.",
                    )

    return crud.get_decrypted_access_token(user)
