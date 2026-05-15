from __future__ import annotations

import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_SALT = b"gitsyntropy-token-encryption"
_ITERATIONS = 390_000
_KEY_LENGTH = 32


def _derive_key(secret: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=_SALT,
        iterations=_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))


def encrypt_token(token: Optional[str], secret: str) -> Optional[str]:
    """Encrypt a GitHub OAuth token using Fernet symmetric encryption."""
    if token is None:
        return None
    return Fernet(_derive_key(secret)).encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted: Optional[str], secret: str) -> Optional[str]:
    """Decrypt a Fernet-encrypted GitHub OAuth token.

    Falls back to returning the value as-is for tokens stored before
    encryption was introduced (plaintext migration path).
    """
    if encrypted is None:
        return None
    try:
        return Fernet(_derive_key(secret)).decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return encrypted
