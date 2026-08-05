"""Encryption for loyalty secrets (Caffesta X-API-KEY, Telegram bot token).

Uses Fernet from `cryptography`. Key is read from `LOYALTY_ENCRYPTION_KEY` env
variable. All values are stored in DB as base64-encoded ciphertext strings.
"""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = os.environ.get("LOYALTY_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "LOYALTY_ENCRYPTION_KEY не задан в backend/.env. "
            "Сгенерируй: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(value: str) -> str:
    """Зашифровать секрет. Возвращает base64-строку. Пустую строку не шифрует."""
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    """Расшифровать. Возвращает пустую строку при ошибке (или пустом входе)."""
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask(value: str, keep: int = 4) -> str:
    """Маска для отображения в UI: `••••1234`."""
    if not value:
        return ""
    return "•" * max(4, len(value) - keep) + value[-keep:]
