"""
Модели раздела «Лояльность».

Три коллекции в MongoDB:
- `loyalty_config` — конфигурация на ресторан (Caffesta ключи, токен бота, шаблоны).
- `loyalty_clients` — клиенты (нормализованный телефон, привязка к Telegram, баланс).
- `loyalty_notifications_log` — журнал уведомлений и ошибок синхронизации.

Секреты (X-API-KEY, bot_token) хранятся зашифрованными в полях с суффиксом `_enc`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
import uuid


DEFAULT_TEMPLATE_ACCRUAL = "Начислено {amount} бонусов. Баланс: {balance} BYN"
DEFAULT_TEMPLATE_DEBIT = "Списано {amount} бонусов. Баланс: {balance} BYN"


class LoyaltyConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    caffesta_account_name: str = ""
    caffesta_api_key_enc: str = ""  # encrypted
    pos_id: str = ""
    sync_interval_min: int = 2
    telegram_bot_token_enc: str = ""  # encrypted
    telegram_bot_username: str = ""  # cached, безопасно показывать
    template_accrual: str = DEFAULT_TEMPLATE_ACCRUAL
    template_debit: str = DEFAULT_TEMPLATE_DEBIT
    is_enabled: bool = False
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = ""
    last_error_at: Optional[datetime] = None
    last_clients_ts: int = 0  # unix timestamp последнего обработанного clients
    webhook_secret: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoyaltyClient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    phone_norm: str  # только цифры, как у Caffesta normPhone
    name: str = ""
    caffesta_uuid: str = ""
    telegram_chat_id: Optional[int] = None
    telegram_username: str = ""
    last_bonus_balance: float = 0.0
    last_point_balance: float = 0.0
    last_synced_at: Optional[datetime] = None
    linked_at: Optional[datetime] = None
    # Внутренний номер карты клиента (не связан с Caffesta cardNumber).
    # Присваивается один раз при первой привязке телефона.
    card_number: Optional[int] = None
    # ID сообщения с фото карты, закреплённого в приватном чате бота.
    # Обновляется через editMessageCaption при изменении баланса.
    pinned_message_id: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LoyaltyNotificationLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    client_id: str = ""
    phone_norm: str = ""
    kind: str  # accrual | debit | welcome | error
    amount: float = 0.0
    balance_after: float = 0.0
    message: str = ""
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "success"  # success | error
    error_text: str = ""
    http_code: int = 0
