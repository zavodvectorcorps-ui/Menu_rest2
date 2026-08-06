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

DEFAULT_START_MESSAGE = (
    "Привет! 👋 Я — бот программы лояльности этого ресторана.\n\n"
    "Нажмите кнопку ниже, чтобы поделиться номером телефона — и я привяжу "
    "к нему ваш Telegram, чтобы присылать сюда все начисления и списания бонусов."
)
DEFAULT_ONBOARDING_BIRTHDAY_TEXT = (
    "Шаг 1 из 3 — <b>дата рождения</b>\n"
    "Пришлите в формате <b>ДД.ММ.ГГГГ</b> (например, 15.03.1990) "
    "или нажмите «Пропустить»."
)
DEFAULT_ONBOARDING_GENDER_TEXT = (
    "Шаг 2 из 3 — <b>пол</b>\n"
    "Выберите: М (мужской) или Ж (женский), либо «Пропустить»."
)
DEFAULT_WELCOME_MESSAGE = (
    "✅ Готово, {name}! Карта закреплена сверху — там всегда актуальный баланс. "
    "Мы будем уведомлять об изменениях.\n\n"
    "Хотите получать поздравления с днём рождения? Отправьте /birthday."
)
DEFAULT_INVITE_MESSAGE = (
    "Расскажите друзьям о нашем ресторане! 🎁\n\n"
    "Перешлите им это сообщение или дайте ссылку на бота:\n{bot_link}\n\n"
    "Спасибо, что делитесь с нами вкусом!"
)


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
    start_message_text: str = DEFAULT_START_MESSAGE
    onboarding_birthday_text: str = DEFAULT_ONBOARDING_BIRTHDAY_TEXT
    onboarding_gender_text: str = DEFAULT_ONBOARDING_GENDER_TEXT
    welcome_message_text: str = DEFAULT_WELCOME_MESSAGE
    invite_message_text: str = DEFAULT_INVITE_MESSAGE
    is_enabled: bool = False
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = ""
    last_error_at: Optional[datetime] = None
    last_clients_ts: int = 0  # unix timestamp последнего обработанного clients
    # Авторегистрация клиента в Caffesta при подписке на бота
    caffesta_loyalty_product_id: Optional[str] = None
    caffesta_auto_register: bool = False
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
    # UUID заказа "Карта лояльности" в Caffesta — созданного при авторегистрации.
    # Хранится для отладки: по нему кассир может найти конкретный wait_cashier заказ.
    caffesta_receipt_uuid: Optional[str] = None
    # Персональные данные, которые клиент присылает боту через /birthday, /gender
    birthday: Optional[str] = None   # YYYY-MM-DD
    sex: Optional[str] = None        # M | F
    # Состояние диалога бота (для многошаговых команд)
    pending_prompt: Optional[str] = None  # "birthday" | "gender" | None
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
