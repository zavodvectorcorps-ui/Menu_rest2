"""
Telegram-бот для программы лояльности.

Каждый ресторан задаёт свой токен → мы регистрируем webhook на
`/api/loyalty/webhook/{restaurant_id}/{secret}`. Telegram шлёт нам update, мы
обрабатываем команды:

- `/start` — приветствие + кнопка «Поделиться номером телефона» (request_contact)
- получение контакта — привязываем phone_norm ↔ telegram_chat_id, показываем баланс
- `/balance` — показывает последний известный баланс из БД
- `/unlink` — отвязываем телефон от Telegram
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from database import db
from services.loyalty_card import (
    edit_card_caption,
    next_card_number,
    send_card_and_pin,
)
from services.loyalty_crypto import decrypt
from services.loyalty_sync import normalize_phone

logger = logging.getLogger("loyalty.bot")

TELEGRAM_API = "https://api.telegram.org"
BOT_TIMEOUT = 10


async def _send(bot_token: str, chat_id: int, text: str, reply_markup: Optional[dict] = None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=BOT_TIMEOUT) as client:
            await client.post(f"{TELEGRAM_API}/bot{bot_token}/sendMessage", json=payload)
    except Exception as exc:
        logger.warning("send failed: %s", exc)


def _share_phone_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "📱 Поделиться номером", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _remove_keyboard() -> dict:
    return {"remove_keyboard": True}


async def _ensure_card_and_send(
    bot_token: str,
    restaurant_id: str,
    restaurant_name: str,
    client_doc: dict,
) -> Optional[int]:
    """
    Гарантирует, что у клиента есть card_number, отправляет ему карту и пинует её.
    Возвращает pinned_message_id (или None при сбое).
    Обновляет БД (card_number, pinned_message_id).
    """
    card_no = client_doc.get("card_number")
    if not card_no:
        card_no = await next_card_number(restaurant_id)
        await db.loyalty_clients.update_one(
            {"restaurant_id": restaurant_id, "id": client_doc["id"]},
            {"$set": {"card_number": card_no}},
        )
    balance = float(client_doc.get("last_bonus_balance") or 0)
    msg_id = await send_card_and_pin(
        bot_token, int(client_doc["telegram_chat_id"]), restaurant_name, card_no, balance,
    )
    if msg_id:
        await db.loyalty_clients.update_one(
            {"restaurant_id": restaurant_id, "id": client_doc["id"]},
            {"$set": {"pinned_message_id": msg_id}},
        )
    return msg_id


async def _welcome_after_link(bot_token: str, chat_id: int, client_doc: dict, cfg: dict):
    """После привязки — сначала фото-карта (запинена), затем текстовое приветствие."""
    # Получаем название ресторана из БД для «шапки» карты
    rest = await db.restaurants.find_one({"id": cfg["restaurant_id"]}, {"_id": 0, "name": 1})
    restaurant_name = (rest or {}).get("name") or "Ресторан"

    await _ensure_card_and_send(bot_token, cfg["restaurant_id"], restaurant_name, client_doc)

    name = client_doc.get("name") or "друг"
    if client_doc.get("last_synced_at"):
        text = f"✅ Готово, {name}! Ваша карта закреплена сверху — там всегда виден актуальный баланс. Мы будем уведомлять об изменениях."
    else:
        text = (
            f"✅ Готово, {name}! Карта закреплена сверху. "
            "Как только в базе появятся ваши бонусы — увидите их прямо на карте."
        )
    await _send(bot_token, chat_id, text, _remove_keyboard())


async def handle_update(restaurant_id: str, update: dict) -> None:
    """Обрабатываем один update от Telegram."""
    cfg = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not cfg:
        return
    bot_token = decrypt(cfg.get("telegram_bot_token_enc") or "")
    if not bot_token:
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    username = chat.get("username") or ""

    # 1. Обработка контакта (нажатие «Поделиться номером»)
    contact = message.get("contact")
    if contact and contact.get("phone_number"):
        phone_norm = normalize_phone(contact["phone_number"])
        existing = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "phone_norm": phone_norm}, {"_id": 0}
        )
        now = datetime.now(timezone.utc)
        if existing:
            # Привязываем к этому Telegram-аккаунту
            await db.loyalty_clients.update_one(
                {"restaurant_id": restaurant_id, "phone_norm": phone_norm},
                {"$set": {
                    "telegram_chat_id": int(chat_id),
                    "telegram_username": username,
                    "linked_at": now,
                }},
            )
            merged = {**existing, "telegram_chat_id": int(chat_id)}
            await _welcome_after_link(bot_token, chat_id, merged, cfg)
        else:
            # Клиента с таким телефоном в Caffesta пока нет — создаём заготовку,
            # чтобы при следующей sync-синхронизации сразу привязать.
            import uuid as _uuid
            await db.loyalty_clients.insert_one({
                "id": _uuid.uuid4().hex,
                "restaurant_id": restaurant_id,
                "phone_norm": phone_norm,
                "name": " ".join(x for x in [contact.get("first_name") or "", contact.get("last_name") or ""] if x).strip(),
                "caffesta_uuid": "",
                "telegram_chat_id": int(chat_id),
                "telegram_username": username,
                "last_bonus_balance": 0.0,
                "last_point_balance": 0.0,
                "last_synced_at": None,
                "linked_at": now,
                "created_at": now,
            })
            await _send(
                bot_token, chat_id,
                "Мы пока не нашли карту лояльности по этому номеру. "
                "Обратитесь на кассе, чтобы её оформили — как только карта появится, "
                "вы автоматически начнёте получать уведомления.",
                _remove_keyboard(),
            )
        return

    # 2. Команды
    text = (message.get("text") or "").strip()

    if text.startswith("/start"):
        await _send(
            bot_token, chat_id,
            "Привет! 👋 Я — бот программы лояльности этого ресторана.\n\n"
            "Нажмите кнопку ниже, чтобы поделиться номером телефона — и я привяжу "
            "к нему ваш Telegram, чтобы присылать сюда все начисления и списания бонусов.",
            _share_phone_keyboard(),
        )
        return

    if text.startswith("/balance"):
        client_doc = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
        )
        if not client_doc:
            await _send(
                bot_token, chat_id,
                "Сначала поделитесь номером телефона — нажмите /start.",
            )
            return
        balance = float(client_doc.get("last_bonus_balance") or 0)
        await _send(
            bot_token, chat_id,
            f"Ваш текущий баланс: <b>{balance:.2f} BYN</b>",
        )
        return

    if text.startswith("/card"):
        client_doc = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
        )
        if not client_doc:
            await _send(bot_token, chat_id, "Сначала поделитесь номером телефона — нажмите /start.")
            return
        rest = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0, "name": 1})
        restaurant_name = (rest or {}).get("name") or "Ресторан"
        await _ensure_card_and_send(bot_token, restaurant_id, restaurant_name, client_doc)
        return

    if text.startswith("/unlink"):
        res = await db.loyalty_clients.update_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)},
            {"$set": {"telegram_chat_id": None, "telegram_username": ""}},
        )
        if res.modified_count:
            await _send(bot_token, chat_id, "Ваш Telegram отвязан от карты лояльности. Уведомлений больше не будет.")
        else:
            await _send(bot_token, chat_id, "У вас нет активной привязки.")
        return

    # 3. Прочее сообщение
    client_doc = await db.loyalty_clients.find_one(
        {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
    )
    if not client_doc:
        await _send(
            bot_token, chat_id,
            "Нажмите /start, чтобы привязать номер телефона.",
            _share_phone_keyboard(),
        )
    else:
        await _send(
            bot_token, chat_id,
            "Команды:\n/balance — текущий баланс\n/card — показать карту заново\n/unlink — отвязать Telegram",
        )


# ─── Управление webhook ───────────────────────────────────────────────────

async def set_webhook(bot_token: str, url: str) -> tuple[bool, str]:
    """Регистрируем webhook в Telegram. Возвращает (ok, description)."""
    if not bot_token:
        return False, "empty bot_token"
    try:
        async with httpx.AsyncClient(timeout=BOT_TIMEOUT) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/setWebhook",
                json={"url": url, "drop_pending_updates": True, "allowed_updates": ["message", "edited_message"]},
            )
        j = resp.json()
        return bool(j.get("ok")), j.get("description") or ""
    except Exception as exc:
        return False, str(exc)


async def delete_webhook(bot_token: str) -> None:
    if not bot_token:
        return
    try:
        async with httpx.AsyncClient(timeout=BOT_TIMEOUT) as client:
            await client.post(f"{TELEGRAM_API}/bot{bot_token}/deleteWebhook")
    except Exception:
        pass


async def get_bot_username(bot_token: str) -> str:
    if not bot_token:
        return ""
    try:
        async with httpx.AsyncClient(timeout=BOT_TIMEOUT) as client:
            resp = await client.get(f"{TELEGRAM_API}/bot{bot_token}/getMe")
        j = resp.json()
        if j.get("ok"):
            return (j.get("result") or {}).get("username") or ""
    except Exception:
        pass
    return ""
