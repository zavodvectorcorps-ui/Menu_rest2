"""Encryption for loyalty secrets (Caffesta X-API-KEY, Telegram bot token).

Uses Fernet from `cryptography`. Key is read from `LOYALTY_ENCRYPTION_KEY` env
variable. All values are stored in DB as base64-encoded ciphertext strings.
"""

from __future__ import annotations

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


import logging as _logging
_logger = _logging.getLogger("loyalty.crypto")


@lru_cache(maxsize=1)
def _fernet_or_none() -> Fernet | None:
    key = os.environ.get("LOYALTY_ENCRYPTION_KEY")
    if not key:
        _logger.warning(
            "LOYALTY_ENCRYPTION_KEY не задан. Секреты не будут шифроваться/расшифровываться. "
            "Сгенерируй: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        _logger.error("LOYALTY_ENCRYPTION_KEY некорректен: %s", exc)
        return None


def encrypt(value: str) -> str:
    """Зашифровать секрет. Возвращает base64-строку. Пустую строку не шифрует."""
    if not value:
        return ""
    f = _fernet_or_none()
    if f is None:
        # Без ключа — не сохраняем секрет в базе.
        return ""
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    """Расшифровать. Возвращает пустую строку при ошибке (или пустом входе/отсутствии ключа)."""
    if not value:
        return ""
    f = _fernet_or_none()
    if f is None:
        return ""
    try:
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask(value: str, keep: int = 4) -> str:
    """Маска для отображения в UI: `••••1234`."""
    if not value:
        return ""
    return "•" * max(4, len(value) - keep) + value[-keep:]
