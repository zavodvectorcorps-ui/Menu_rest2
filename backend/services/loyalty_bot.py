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
from services.loyalty_sync import caffesta_register_client, normalize_phone

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


def _skip_keyboard() -> dict:
    """Клавиатура с одной кнопкой «Пропустить» (для необязательных полей)."""
    return {
        "keyboard": [[{"text": "Пропустить"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _gender_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "М"}, {"text": "Ж"}, {"text": "Пропустить"}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _main_menu_keyboard() -> dict:
    """Постоянная reply-клавиатура после регистрации."""
    return {
        "keyboard": [
            [{"text": "💰 Баланс"}, {"text": "🎫 Моя карта"}],
            [{"text": "👥 Пригласить друга"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _remove_keyboard() -> dict:
    return {"remove_keyboard": True}


# ─── Onboarding-стейт (сбор birthday/sex ДО phone) ────────────────────────
# Храним в отдельной коллекции, чтобы не мешать loyalty_clients.
# Ключ: (restaurant_id, chat_id).

async def _get_onboarding(restaurant_id: str, chat_id: int) -> Optional[dict]:
    return await db.loyalty_bot_state.find_one(
        {"restaurant_id": restaurant_id, "chat_id": int(chat_id)}, {"_id": 0}
    )


async def _set_onboarding(restaurant_id: str, chat_id: int, patch: dict) -> None:
    patch["updated_at"] = datetime.now(timezone.utc)
    await db.loyalty_bot_state.update_one(
        {"restaurant_id": restaurant_id, "chat_id": int(chat_id)},
        {"$set": patch, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def _clear_onboarding(restaurant_id: str, chat_id: int) -> None:
    await db.loyalty_bot_state.delete_one(
        {"restaurant_id": restaurant_id, "chat_id": int(chat_id)}
    )


def _parse_birthday(text: str) -> Optional[str]:
    """DD.MM.YYYY или YYYY-MM-DD → YYYY-MM-DD, иначе None."""
    s = text.strip()
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return None


def _parse_sex(text: str) -> Optional[str]:
    s = text.strip().lower()
    if s in ("м", "m", "муж", "мужской"):
        return "M"
    if s in ("ж", "f", "жен", "женский"):
        return "F"
    return None


async def _try_caffesta_auto_register(cfg: dict, client_doc: dict) -> None:
    """
    Если в конфиге включено — создаём клиента в Caffesta через фиктивный заказ.
    Успех/ошибку логируем в общий журнал раздела «Лояльность». Не блокируем регистрацию.
    """
    if not cfg.get("caffesta_auto_register"):
        return
    if client_doc.get("caffesta_receipt_uuid"):
        return  # уже регистрировали
    account = cfg.get("caffesta_account_name") or ""
    api_key = decrypt(cfg.get("caffesta_api_key_enc") or "")
    pos_id = cfg.get("pos_id") or ""
    product_id = cfg.get("caffesta_loyalty_product_id") or ""
    if not (account and api_key and pos_id and product_id):
        return
    phone = client_doc.get("phone_norm") or ""
    name = client_doc.get("name") or "Клиент"

    # Гарантируем card_number ДО обращения в Caffesta — передаём ей явный номер,
    # чтобы обойти их баг с автогенерацией "code".
    from services.loyalty_card import next_card_number
    card_no = client_doc.get("card_number")
    if not card_no:
        card_no = await next_card_number(cfg["restaurant_id"])
        await db.loyalty_clients.update_one(
            {"restaurant_id": cfg["restaurant_id"], "id": client_doc["id"]},
            {"$set": {"card_number": card_no}},
        )
        client_doc["card_number"] = card_no

    receipt_uuid, err = await caffesta_register_client(
        account, api_key, pos_id, product_id, name, phone, card_number=card_no,
        birthday=client_doc.get("birthday"), sex=client_doc.get("sex"),
    )
    now = datetime.now(timezone.utc)
    if receipt_uuid:
        # Если клиент уже был в Caffesta — не сохраняем как receipt, только логируем.
        already = (receipt_uuid == "already_exists")
        if not already:
            await db.loyalty_clients.update_one(
                {"restaurant_id": cfg["restaurant_id"], "id": client_doc["id"]},
                {"$set": {"caffesta_receipt_uuid": receipt_uuid}},
            )
        await db.loyalty_notifications_log.insert_one({
            "id": __import__("uuid").uuid4().hex,
            "restaurant_id": cfg["restaurant_id"],
            "client_id": client_doc["id"],
            "phone_norm": phone,
            "kind": "caffesta_register",
            "amount": 0.0,
            "balance_after": 0.0,
            "message": (
                "Клиент уже был в Caffesta — заказ не создавался"
                if already else f"Caffesta receipt: {receipt_uuid}"
            ),
            "sent_at": now,
            "status": "success",
            "error_text": "",
            "http_code": 200,
        })
    else:
        await db.loyalty_notifications_log.insert_one({
            "id": __import__("uuid").uuid4().hex,
            "restaurant_id": cfg["restaurant_id"],
            "client_id": client_doc["id"],
            "phone_norm": phone,
            "kind": "caffesta_register",
            "amount": 0.0,
            "balance_after": 0.0,
            "message": f"Не удалось создать клиента в Caffesta: {err}",
            "sent_at": now,
            "status": "error",
            "error_text": err,
            "http_code": 0,
        })
        logger.warning("caffesta auto-register failed for %s: %s", phone, err)


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

    from models_loyalty import DEFAULT_WELCOME_MESSAGE
    name = client_doc.get("name") or "друг"
    tpl = (cfg.get("welcome_message_text") or DEFAULT_WELCOME_MESSAGE)
    try:
        text = tpl.format(name=name)
    except Exception:
        text = tpl
    await _send(bot_token, chat_id, text, _main_menu_keyboard())


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
        # Подтягиваем данные онбординга (birthday/sex, собранные до share_contact)
        onboarding = await _get_onboarding(restaurant_id, chat_id) or {}
        existing = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "phone_norm": phone_norm}, {"_id": 0}
        )
        now = datetime.now(timezone.utc)
        if existing:
            # Привязываем к этому Telegram-аккаунту
            update_fields = {
                "telegram_chat_id": int(chat_id),
                "telegram_username": username,
                "linked_at": now,
            }
            # Мержим birthday/sex, только если у клиента их ещё нет.
            if onboarding.get("birthday") and not existing.get("birthday"):
                update_fields["birthday"] = onboarding["birthday"]
            if onboarding.get("sex") and not existing.get("sex"):
                update_fields["sex"] = onboarding["sex"]
            await db.loyalty_clients.update_one(
                {"restaurant_id": restaurant_id, "phone_norm": phone_norm},
                {"$set": update_fields},
            )
            merged = {**existing, **update_fields}
            # Авторегистрация в Caffesta (если включена) — с полным пакетом полей.
            await _try_caffesta_auto_register(cfg, merged)
            await _welcome_after_link(bot_token, chat_id, merged, cfg)
        else:
            # Новый клиент — записываем сразу со ВСЕМИ полями из онбординга.
            import uuid as _uuid
            new_id = _uuid.uuid4().hex
            new_client = {
                "id": new_id,
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
                "birthday": onboarding.get("birthday"),
                "sex": onboarding.get("sex"),
            }
            await db.loyalty_clients.insert_one(new_client)
            # Один запрос в Caffesta со всеми полями — избегаем дубликата клиента.
            await _try_caffesta_auto_register(cfg, new_client)
            refreshed = await db.loyalty_clients.find_one(
                {"restaurant_id": restaurant_id, "id": new_id}, {"_id": 0}
            ) or new_client
            await _welcome_after_link(bot_token, chat_id, refreshed, cfg)
        # Онбординг завершён — чистим временное состояние.
        await _clear_onboarding(restaurant_id, chat_id)
        return

    # 2. Команды
    text = (message.get("text") or "").strip()

    if text.startswith("/start"):
        # Если пользователь уже привязан — показываем меню.
        existing = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
        )
        if existing:
            from models_loyalty import DEFAULT_WELCOME_MESSAGE
            name = existing.get("name") or "друг"
            tpl = cfg.get("welcome_message_text") or DEFAULT_WELCOME_MESSAGE
            try:
                text_msg = tpl.format(name=name)
            except Exception:
                text_msg = tpl
            await _send(bot_token, chat_id, text_msg, _main_menu_keyboard())
            return
        # Онбординг с нуля: приветствие + вопрос о дате рождения.
        from models_loyalty import DEFAULT_START_MESSAGE
        start_text = cfg.get("start_message_text") or DEFAULT_START_MESSAGE
        await _set_onboarding(restaurant_id, chat_id, {"step": "birthday"})
        await _send(bot_token, chat_id, start_text)
        await _send(
            bot_token, chat_id,
            "Шаг 1 из 3 — <b>дата рождения</b>\nПришлите в формате <b>ДД.ММ.ГГГГ</b> (например, 15.03.1990) "
            "или нажмите «Пропустить».",
            _skip_keyboard(),
        )
        return

    # 2.5 Онбординг-стейт — приоритетный обработчик
    onboarding = await _get_onboarding(restaurant_id, chat_id)
    if onboarding:
        step = onboarding.get("step")
        is_skip = text.strip().lower() == "пропустить"
        if step == "birthday":
            if is_skip:
                await _set_onboarding(restaurant_id, chat_id, {"step": "gender"})
                await _send(
                    bot_token, chat_id,
                    "Шаг 2 из 3 — <b>пол</b>\nВыберите: М (мужской) или Ж (женский), либо «Пропустить».",
                    _gender_keyboard(),
                )
                return
            bd = _parse_birthday(text)
            if not bd:
                await _send(bot_token, chat_id, "Неверный формат. Пример: <b>15.03.1990</b>. Попробуйте ещё раз или нажмите «Пропустить».", _skip_keyboard())
                return
            await _set_onboarding(restaurant_id, chat_id, {"step": "gender", "birthday": bd})
            await _send(
                bot_token, chat_id,
                f"✅ Дата рождения: {bd}\n\nШаг 2 из 3 — <b>пол</b>\nВыберите: М или Ж, либо «Пропустить».",
                _gender_keyboard(),
            )
            return
        if step == "gender":
            if is_skip:
                await _set_onboarding(restaurant_id, chat_id, {"step": "phone"})
                await _send(
                    bot_token, chat_id,
                    "Шаг 3 из 3 — <b>номер телефона</b>\nНажмите кнопку ниже, чтобы поделиться номером.",
                    _share_phone_keyboard(),
                )
                return
            sx = _parse_sex(text)
            if not sx:
                await _send(bot_token, chat_id, "Напишите <b>М</b> или <b>Ж</b>, либо «Пропустить».", _gender_keyboard())
                return
            await _set_onboarding(restaurant_id, chat_id, {"step": "phone", "sex": sx})
            await _send(
                bot_token, chat_id,
                f"✅ Пол: {'Мужской' if sx == 'M' else 'Женский'}\n\n"
                "Шаг 3 из 3 — <b>номер телефона</b>\nНажмите кнопку ниже, чтобы поделиться номером.",
                _share_phone_keyboard(),
            )
            return
        if step == "phone":
            # Ждём именно контакт-кнопку. Если пришёл текст — напоминаем.
            await _send(
                bot_token, chat_id,
                "Нажмите кнопку «📱 Поделиться номером» внизу — иначе я не смогу привязать карту.",
                _share_phone_keyboard(),
            )
            return

    # Кнопки главного меню (reply-keyboard) — сравниваем без учёта регистра/эмодзи
    _norm = text.lower().replace("💰", "").replace("👥", "").replace("🎫", "").strip()

    if text.startswith("/balance") or _norm in ("баланс", "мой баланс"):
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
            _main_menu_keyboard(),
        )
        return

    # Пригласить друга — простая шеринг-ссылка на бота, без реферального учёта
    if _norm in ("пригласить друга", "пригласить", "invite"):
        client_doc = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
        )
        if not client_doc:
            await _send(bot_token, chat_id, "Сначала поделитесь номером телефона — нажмите /start.")
            return
        from models_loyalty import DEFAULT_INVITE_MESSAGE
        bot_username = cfg.get("telegram_bot_username") or ""
        bot_link = f"https://t.me/{bot_username}" if bot_username else "этому боту"
        tpl = cfg.get("invite_message_text") or DEFAULT_INVITE_MESSAGE
        try:
            invite_text = tpl.format(bot_link=bot_link, name=client_doc.get("name") or "друг")
        except Exception:
            invite_text = tpl
        await _send(bot_token, chat_id, invite_text, _main_menu_keyboard())
        return

    if text.startswith("/card") or _norm in ("моя карта", "карта"):
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

    # /birthday — начинаем диалог: ждём дату в формате YYYY-MM-DD или DD.MM.YYYY
    if text.startswith("/birthday"):
        client_doc = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
        )
        if not client_doc:
            await _send(bot_token, chat_id, "Сначала поделитесь номером телефона — нажмите /start.")
            return
        await db.loyalty_clients.update_one(
            {"restaurant_id": restaurant_id, "id": client_doc["id"]},
            {"$set": {"pending_prompt": "birthday"}},
        )
        await _send(bot_token, chat_id, "Пришлите вашу дату рождения в формате <b>ДД.ММ.ГГГГ</b>\n(например, 15.03.1990)")
        return

    # Обработка ответа на pending_prompt (birthday)
    client_doc = await db.loyalty_clients.find_one(
        {"restaurant_id": restaurant_id, "telegram_chat_id": int(chat_id)}, {"_id": 0}
    )
    if client_doc and client_doc.get("pending_prompt"):
        pending = client_doc["pending_prompt"]
        if pending == "birthday":
            import re as _re
            s = text.strip()
            m = _re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", s)
            if m:
                bd = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
            elif _re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                bd = s
            else:
                await _send(bot_token, chat_id, "Неверный формат. Пример: <b>15.03.1990</b>")
                return
            await db.loyalty_clients.update_one(
                {"restaurant_id": restaurant_id, "id": client_doc["id"]},
                {"$set": {"birthday": bd, "pending_prompt": None}},
            )
            await _send(bot_token, chat_id, f"✅ Спасибо! Дата рождения: {bd}")
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
            "Команды:\n/balance — текущий баланс\n/card — показать карту заново\n"
            "/birthday — указать дату рождения\n/unlink — отвязать Telegram",
            _main_menu_keyboard(),
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
