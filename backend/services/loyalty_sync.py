"""
Синхронизация с Caffesta и обработка бонусных балансов клиентов.

Ключевые концепции:
- Caffesta не даёт вебхуков — приходится опрашивать `get_updates/{pos_id}`,
  проверять, изменился ли таймстемп `clients`.
- Если изменился — вытягиваем свежий список через `get_clients/{last_ts}`.
- Матчим клиентов по `normPhone`. Если клиент привязан к Telegram и его
  bonusBalance изменился — отправляем уведомление.

Все запросы к Caffesta и Telegram — с таймаутом. Любые ошибки → в лог,
воркер продолжает работу в следующий цикл.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from database import db
from models_loyalty import LoyaltyNotificationLog
from services.loyalty_card import edit_card_caption
from services.loyalty_crypto import decrypt

logger = logging.getLogger("loyalty.sync")

CAFFESTA_TIMEOUT = 20
TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_TIMEOUT = 10

PHONE_RE = re.compile(r"\D+")


def normalize_phone(raw: str) -> str:
    """Нормализуем в тот же формат, что даёт Caffesta.normPhone — только цифры."""
    if not raw:
        return ""
    return PHONE_RE.sub("", raw)


# ─── Caffesta API ──────────────────────────────────────────────────────────

async def caffesta_get_updates(account_name: str, api_key: str, pos_id: str) -> dict:
    url = f"https://{account_name}.caffesta.com/a/v1.0/draft/get_updates/{pos_id}"
    async with httpx.AsyncClient(timeout=CAFFESTA_TIMEOUT) as client:
        resp = await client.get(url, headers={"X-API-KEY": api_key})
        resp.raise_for_status()
        return resp.json()


async def caffesta_get_clients(account_name: str, api_key: str, since_ts: int) -> list[dict]:
    url = f"https://{account_name}.caffesta.com/a/v1.0/draft/get_clients/{since_ts}"
    async with httpx.AsyncClient(timeout=CAFFESTA_TIMEOUT * 2) as client:
        resp = await client.get(url, headers={"X-API-KEY": api_key})
        resp.raise_for_status()
        data = resp.json()
    # Ответ может быть либо массивом, либо {data: [...]}
    if isinstance(data, dict):
        return data.get("data") or data.get("clients") or []
    return data if isinstance(data, list) else []


async def caffesta_register_client(
    account_name: str,
    api_key: str,
    pos_id: str,
    product_id: str,
    client_name: str,
    client_phone: str,
    card_number: Optional[int] = None,
) -> tuple[Optional[str], str]:
    """
    Создать клиента в Caffesta через фиктивный заказ доставки на "Карта лояльности" (цена 0).
    Возвращает (receipt_uuid, error_or_empty).

    Особый случай: если Caffesta вернул INSERT INTO clients — значит клиент с таким
    phone уже есть в базе. Возвращаем ("already_exists", "") — это не ошибка.
    """
    if not account_name or not api_key or not pos_id or not product_id:
        return None, "не заданы pos_id / product_id / caffesta ключи"
    import time as _time
    # Split "Иван Иванов" → first="Иван", last="Иванов"
    parts = (client_name or "").strip().split(maxsplit=1)
    first_name = parts[0] if parts else "Клиент"
    last_name = parts[1] if len(parts) > 1 else ""
    # Caffesta ожидает phone в формате E.164 (+7…). Мы храним phone_norm — только
    # цифры, поэтому добавляем префикс + для запроса.
    phone_for_caffesta = client_phone if client_phone.startswith("+") else f"+{client_phone}"
    url = f"https://{account_name}.caffesta.com/a/v1.1/draft/receipts"
    body = {
        "bill": {
            "pos_id": int(pos_id) if str(pos_id).isdigit() else pos_id,
            "app_id": 26,
            "date": int(_time.time()),
            "receipt_type": 3,
            "service_type": 1,
            "delivery_type": 2,
            "discount_sum": 0,
            "total_sum": 0,
            "payments": [{"payment_id": 2, "value": 0}],
            "items": [{
                "title": "Карта лояльности",
                "count": 1,
                "price": 0,
                "origin_price": 0,
                "discount_sum": 0,
                "total_sum": 0,
                "product_id": int(product_id) if str(product_id).isdigit() else product_id,
            }],
            "client": {
                "name": first_name,
                "last_name": last_name,
                "phone": phone_for_caffesta,
                "address": "—",
                "email": "",
                # Явный card_number обходит их автогенерацию (баг с "code, code")
                "card_number": f"{int(card_number):012d}" if card_number else f"{int(_time.time()) % 10**12:012d}",
            },
            "delivery": {"address": "—"},
            "comment": "Автосоздание клиента при регистрации в Telegram-боте",
        }
    }
    try:
        async with httpx.AsyncClient(timeout=CAFFESTA_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json=body,
            )
    except Exception as exc:
        return None, f"network: {exc}"
    try:
        j = resp.json()
    except Exception:
        return None, f"HTTP {resp.status_code}: {resp.text[:500]}"

    # Успех — вернём receipt_uuid
    if j.get("success") and (j.get("data") or {}).get("message"):
        return (j["data"]["message"]), ""

    # Особый случай: клиент уже существует в Caffesta
    # Ловим только явные признаки unique constraint. INSERT INTO clients сам по себе
    # может упасть по многим причинам (NOT NULL и т.п.), не считаем это успехом.
    err_msg = str((j.get("data") or {}).get("status") or (j.get("data") or {}).get("message") or "")
    lower = err_msg.lower()
    if "duplicate" in lower or "unique constraint" in lower or "unique key" in lower:
        return "already_exists", ""

    # Прочая ошибка — с диагностикой
    import json as _json
    body_preview = _json.dumps(body, ensure_ascii=False)[:400]
    resp_preview = _json.dumps(j, ensure_ascii=False)[:400]
    return None, f"{err_msg[:200]} | REQ: {body_preview} | RESP: {resp_preview}"


# ─── Telegram sender ───────────────────────────────────────────────────────

async def send_telegram_message(bot_token: str, chat_id: int, text: str) -> tuple[bool, int, str]:
    """Отправка сообщения в Telegram. Возвращает (ok, http_code, error_text)."""
    if not bot_token or not chat_id:
        return False, 0, "missing token or chat_id"
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        if resp.status_code == 200 and resp.json().get("ok"):
            return True, 200, ""
        return False, resp.status_code, resp.text[:500]
    except Exception as exc:
        return False, 0, str(exc)[:500]


# ─── Логирование ───────────────────────────────────────────────────────────

async def _log(
    restaurant_id: str,
    kind: str,
    *,
    client_id: str = "",
    phone_norm: str = "",
    amount: float = 0.0,
    balance_after: float = 0.0,
    message: str = "",
    status: str = "success",
    error_text: str = "",
    http_code: int = 0,
):
    doc = LoyaltyNotificationLog(
        restaurant_id=restaurant_id,
        client_id=client_id,
        phone_norm=phone_norm,
        kind=kind,
        amount=amount,
        balance_after=balance_after,
        message=message,
        status=status,
        error_text=error_text,
        http_code=http_code,
    ).model_dump()
    doc["sent_at"] = datetime.now(timezone.utc)
    await db.loyalty_notifications_log.insert_one(doc)


# ─── Один цикл синхронизации на ресторан ───────────────────────────────────

async def _sync_one(restaurant_id: str, config: dict) -> tuple[Optional[str], dict]:
    """Возвращает (error_or_None, info_dict)."""
    account_name = config.get("caffesta_account_name") or ""
    api_key = decrypt(config.get("caffesta_api_key_enc") or "")
    pos_id = config.get("pos_id") or ""
    bot_token = decrypt(config.get("telegram_bot_token_enc") or "")
    tpl_accrual = config.get("template_accrual") or ""
    tpl_debit = config.get("template_debit") or ""
    last_clients_ts = int(config.get("last_clients_ts") or 0)

    if not account_name or not api_key or not pos_id:
        return "Не заполнены Caffesta account_name / api_key / pos_id", {}

    # 1. Есть ли изменения?
    try:
        updates = await caffesta_get_updates(account_name, api_key, pos_id)
    except Exception as exc:
        return f"get_updates failed: {exc}", {}
    data = updates.get("data") if isinstance(updates, dict) else None
    new_clients_ts = 0
    if isinstance(data, dict):
        new_clients_ts = int(data.get("clients") or 0)
    if new_clients_ts <= last_clients_ts:
        return None, {
            "changed": False,
            "caffesta_clients_ts": new_clients_ts,
            "last_processed_ts": last_clients_ts,
        }

    # 2. Тянем новых/изменившихся клиентов
    try:
        clients = await caffesta_get_clients(account_name, api_key, last_clients_ts)
    except Exception as exc:
        return f"get_clients failed: {exc}", {}

    processed = 0
    notifications_sent = 0
    for cli in clients:
        phone_norm = normalize_phone(cli.get("normPhone") or cli.get("phone") or "")
        if not phone_norm:
            continue

        new_bonus = float(cli.get("bonusBalance") or 0)
        new_points = float(cli.get("pointBalance") or 0)
        name = " ".join(x for x in [cli.get("name") or "", cli.get("lastName") or ""] if x).strip()
        caffesta_uuid = cli.get("uuid") or ""

        # Ищем нашего клиента
        existing = await db.loyalty_clients.find_one(
            {"restaurant_id": restaurant_id, "phone_norm": phone_norm}, {"_id": 0}
        )
        old_bonus = float(existing.get("last_bonus_balance") or 0) if existing else 0.0
        delta = round(new_bonus - old_bonus, 2)

        now = datetime.now(timezone.utc)
        upd = {
            "$set": {
                "name": name,
                "caffesta_uuid": caffesta_uuid,
                "last_bonus_balance": new_bonus,
                "last_point_balance": new_points,
                "last_synced_at": now,
            },
            "$setOnInsert": {
                "id": (existing or {}).get("id") or __import__("uuid").uuid4().hex,
                "restaurant_id": restaurant_id,
                "phone_norm": phone_norm,
                "telegram_chat_id": None,
                "telegram_username": "",
                "created_at": now,
            },
        }
        await db.loyalty_clients.update_one(
            {"restaurant_id": restaurant_id, "phone_norm": phone_norm}, upd, upsert=True
        )

        # Уведомление — только если клиент привязан к Telegram, баланс изменился,
        # и это НЕ первый импорт (existing != None и старый баланс уже был известен).
        if (
            existing
            and existing.get("telegram_chat_id")
            and abs(delta) >= 0.01
        ):
            kind = "accrual" if delta > 0 else "debit"
            tpl = tpl_accrual if kind == "accrual" else tpl_debit
            text = tpl.format(
                amount=f"{abs(delta):.2f}".rstrip("0").rstrip("."),
                balance=f"{new_bonus:.2f}".rstrip("0").rstrip("."),
                name=name,
            )
            ok, code, err = await send_telegram_message(
                bot_token, int(existing["telegram_chat_id"]), text
            )
            await _log(
                restaurant_id,
                kind,
                client_id=existing.get("id", ""),
                phone_norm=phone_norm,
                amount=abs(delta),
                balance_after=new_bonus,
                message=text,
                status="success" if ok else "error",
                error_text=err,
                http_code=code,
            )
            notifications_sent += 1

            # Обновляем подпись под закреплённой картой (если она есть).
            pinned_id = existing.get("pinned_message_id")
            card_no = existing.get("card_number")
            chat_id_int = int(existing["telegram_chat_id"])
            if pinned_id and card_no:
                edit_ok, edit_err = await edit_card_caption(
                    bot_token, chat_id_int, int(pinned_id), int(card_no), new_bonus,
                )
                if not edit_ok:
                    # Пользователь мог сам открепить/удалить сообщение.
                    if "message to edit not found" in (edit_err or "").lower() or "not found" in (edit_err or "").lower():
                        await db.loyalty_clients.update_one(
                            {"restaurant_id": restaurant_id, "id": existing["id"]},
                            {"$set": {"pinned_message_id": None}},
                        )
                        logger.info("pinned_message cleared for %s: %s", phone_norm, edit_err)
                    else:
                        logger.warning("edit_card_caption failed for %s: %s", phone_norm, edit_err)
        processed += 1

    # 3. Сохраняем новый ts
    await db.loyalty_config.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"last_clients_ts": new_clients_ts, "last_synced_at": datetime.now(timezone.utc), "last_error": "", "last_error_at": None}},
    )
    logger.info("loyalty sync %s: processed %d clients (ts %d → %d)",
                restaurant_id, processed, last_clients_ts, new_clients_ts)
    return None, {
        "changed": True,
        "processed": processed,
        "notifications_sent": notifications_sent,
        "caffesta_clients_ts": new_clients_ts,
    }


async def sync_restaurant(restaurant_id: str) -> tuple[Optional[str], dict]:
    """Ручной запуск синхронизации на конкретный ресторан (кнопка «Синхронизировать сейчас»).
    Возвращает (error_or_None, info_dict) с диагностикой."""
    cfg = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not cfg:
        return "loyalty_config not found", {}
    if not cfg.get("is_enabled"):
        return "sync disabled", {}
    await db.loyalty_config.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"last_polled_at": datetime.now(timezone.utc)}},
    )
    err, info = await _sync_one(restaurant_id, cfg)
    if err:
        await db.loyalty_config.update_one(
            {"restaurant_id": restaurant_id},
            {"$set": {"last_error": err, "last_error_at": datetime.now(timezone.utc)}},
        )
        await _log(restaurant_id, "error", status="error", error_text=err, message=err)
    return err, info


# ─── Планировщик: раз в минуту проходим по всем ресторанам ─────────────────

async def run_loyalty_sync_job():
    """Cron: тикает раз в минуту, обходит все включённые рестораны,
    учитывает индивидуальный `sync_interval_min` каждого."""
    logger.info("loyalty tick @ %s", datetime.now(timezone.utc).isoformat())
    try:
        now = datetime.now(timezone.utc)
        cursor = db.loyalty_config.find({"is_enabled": True}, {"_id": 0})
        cfgs = await cursor.to_list(1000)
    except Exception as exc:
        logger.exception("loyalty tick: failed to list configs: %s", exc)
        return

    for cfg in cfgs:
        rid = cfg.get("restaurant_id") or "?"
        try:
            interval = int(cfg.get("sync_interval_min") or 2)
            last = cfg.get("last_polled_at") or cfg.get("last_synced_at")
            if last and isinstance(last, datetime):
                # BSON не хранит tz — приводим naive → aware UTC перед вычитанием.
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                elapsed_min = (now - last).total_seconds() / 60
                if elapsed_min + 0.05 < interval:
                    continue
            # Пульс — независимо от того, было ли изменение
            await db.loyalty_config.update_one(
                {"restaurant_id": rid},
                {"$set": {"last_polled_at": datetime.now(timezone.utc)}},
            )
            try:
                err, _info = await asyncio.wait_for(_sync_one(rid, cfg), timeout=90)
            except asyncio.TimeoutError:
                err = "sync timeout > 90s"
            except Exception as exc:
                logger.exception("loyalty _sync_one crashed for %s: %s", rid, exc)
                err = f"unexpected: {exc}"
            if err:
                await db.loyalty_config.update_one(
                    {"restaurant_id": rid},
                    {"$set": {"last_error": err, "last_error_at": datetime.now(timezone.utc)}},
                )
                try:
                    await _log(rid, "error", status="error", error_text=err, message=err)
                except Exception:
                    pass
        except Exception as exc:
            # НИКОГДА не бросаем наверх — иначе APScheduler может отключить job
            logger.exception("loyalty tick: outer catch for %s: %s", rid, exc)
