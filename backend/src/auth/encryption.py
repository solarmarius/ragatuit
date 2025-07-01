"""Token encryption utilities for secure storage of sensitive data."""

import base64

from cryptography.fernet import Fernet

from src.config import settings


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

        **Security:**
        - Uses AES 128 encryption with authentication
        - Each encryption includes a unique timestamp and nonce
        - Encrypted tokens are tamper-proof

        **Example:**
            >>> encryption = TokenEncryption()
            >>> encrypted = encryption.encrypt_token("canvas_secret_token_123")
            >>> print(encrypted)  # "gAAAAABhZ..."
        """
        if not token:
            return ""
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
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
            >>> encryption = TokenEncryption()
            >>> decrypted = encryption.decrypt_token("gAAAAABhZ...")
            >>> print(decrypted)  # "canvas_secret_token_123"
        """
        if not encrypted_token:
            return ""
        return self.cipher.decrypt(encrypted_token.encode()).decode()


# Global instance for use across the application
token_encryption = TokenEncryption()
