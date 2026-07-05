"""Symmetric encryption for profile PII stored in SQLite."""

import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class ProfileDecryptionError(Exception):
    """Raised when stored profile data cannot be decrypted."""


# True once ensure_encryption_key() has had to generate a throwaway dev key
# (i.e. no durable PROFILE_ENCRYPTION_KEY was configured). Health reporting uses
# this so it doesn't advertise durable encryption backed by an ephemeral key.
_ephemeral_key_generated = False


def has_durable_encryption_key() -> bool:
    """True when a configured (non-ephemeral) encryption key is in effect."""
    return bool(os.getenv("PROFILE_ENCRYPTION_KEY", "").strip()) and not _ephemeral_key_generated


def _fernet_key_bytes() -> bytes:
    if not os.getenv("PROFILE_ENCRYPTION_KEY", "").strip():
        ensure_encryption_key()
    key = os.getenv("PROFILE_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "PROFILE_ENCRYPTION_KEY is not set. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return key.encode("utf-8")


def get_fernet() -> Fernet:
    return Fernet(_fernet_key_bytes())


def encrypt_payload(data: dict[str, Any]) -> str:
    """Serialize and encrypt a profile payload for storage."""
    token = get_fernet().encrypt(json.dumps(data, separators=(",", ":")).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_payload(token: str) -> dict[str, Any]:
    """Decrypt a stored profile payload."""
    try:
        raw = get_fernet().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise ProfileDecryptionError("Profile data could not be decrypted") from exc
    return json.loads(raw.decode("utf-8"))


def ensure_encryption_key() -> None:
    """Ensure PROFILE_ENCRYPTION_KEY exists; generate a dev key in DEMO_MODE."""
    if os.getenv("PROFILE_ENCRYPTION_KEY", "").strip():
        return

    demo_mode = os.getenv("DEMO_MODE", "1") == "1"
    if not demo_mode:
        raise RuntimeError(
            "PROFILE_ENCRYPTION_KEY is required when DEMO_MODE=0. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    global _ephemeral_key_generated
    key = Fernet.generate_key().decode("utf-8")
    os.environ["PROFILE_ENCRYPTION_KEY"] = key
    _ephemeral_key_generated = True
    print(
        "WARNING: PROFILE_ENCRYPTION_KEY was missing; generated an ephemeral dev key. "
        "Set PROFILE_ENCRYPTION_KEY in .env to persist profiles across restarts."
    )
