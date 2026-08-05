"""
Роуты раздела «Лояльность».

Все `/config`, `/clients`, `/logs` — только для админов (модуль включён);
webhook `/webhook/{restaurant_id}/{secret}` — публичный (валидируется по secret).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import ensure_module_access, get_current_user
from database import db
from models_loyalty import (
    DEFAULT_INVITE_MESSAGE,
    DEFAULT_START_MESSAGE,
    DEFAULT_TEMPLATE_ACCRUAL,
    DEFAULT_TEMPLATE_DEBIT,
    DEFAULT_WELCOME_MESSAGE,
    LoyaltyConfig,
)
from routes.telegram import _resolve_public_base_url  # переиспользуем — тот же паттерн
from services.loyalty_bot import (
    delete_webhook,
    get_bot_username,
    handle_update,
    set_webhook,
)
from services.loyalty_crypto import decrypt, encrypt, mask
from services.loyalty_sync import send_telegram_message, sync_restaurant

router = APIRouter()
logger = logging.getLogger("loyalty")


# ─── Config ────────────────────────────────────────────────────────────────

class LoyaltyConfigUpdate(BaseModel):
    caffesta_account_name: Optional[str] = None
    caffesta_api_key: Optional[str] = None   # plain — при сохранении шифруем
    pos_id: Optional[str] = None
    sync_interval_min: Optional[int] = None
    telegram_bot_token: Optional[str] = None  # plain
    template_accrual: Optional[str] = None
    template_debit: Optional[str] = None
    start_message_text: Optional[str] = None
    welcome_message_text: Optional[str] = None
    invite_message_text: Optional[str] = None
    is_enabled: Optional[bool] = None
    caffesta_loyalty_product_id: Optional[str] = None
    caffesta_auto_register: Optional[bool] = None


def _public_config_view(doc: dict) -> dict:
    """Для UI: секреты маскируем, храним только последние 4 символа."""
    return {
        "id": doc.get("id"),
        "restaurant_id": doc.get("restaurant_id"),
        "caffesta_account_name": doc.get("caffesta_account_name") or "",
        "caffesta_api_key_mask": mask(decrypt(doc.get("caffesta_api_key_enc") or "")),
        "caffesta_api_key_set": bool(doc.get("caffesta_api_key_enc")),
        "pos_id": doc.get("pos_id") or "",
        "sync_interval_min": doc.get("sync_interval_min") or 2,
        "telegram_bot_token_mask": mask(decrypt(doc.get("telegram_bot_token_enc") or "")),
        "telegram_bot_token_set": bool(doc.get("telegram_bot_token_enc")),
        "telegram_bot_username": doc.get("telegram_bot_username") or "",
        "template_accrual": doc.get("template_accrual") or DEFAULT_TEMPLATE_ACCRUAL,
        "template_debit": doc.get("template_debit") or DEFAULT_TEMPLATE_DEBIT,
        "start_message_text": doc.get("start_message_text") or DEFAULT_START_MESSAGE,
        "welcome_message_text": doc.get("welcome_message_text") or DEFAULT_WELCOME_MESSAGE,
        "invite_message_text": doc.get("invite_message_text") or DEFAULT_INVITE_MESSAGE,
        "is_enabled": bool(doc.get("is_enabled")),
        "last_synced_at": doc.get("last_synced_at"),
        "last_polled_at": doc.get("last_polled_at"),
        "last_error": doc.get("last_error") or "",
        "last_error_at": doc.get("last_error_at"),
        "last_clients_ts": int(doc.get("last_clients_ts") or 0),
        "caffesta_loyalty_product_id": doc.get("caffesta_loyalty_product_id") or "",
        "caffesta_auto_register": bool(doc.get("caffesta_auto_register")),
        "webhook_secret": doc.get("webhook_secret") or "",
    }


async def _get_or_create_config(restaurant_id: str) -> dict:
    doc = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if doc:
        return doc
    cfg = LoyaltyConfig(restaurant_id=restaurant_id).model_dump()
    await db.loyalty_config.insert_one(cfg)
    return cfg


@router.get("/restaurants/{restaurant_id}/loyalty/config")
async def get_config(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await ensure_module_access(restaurant_id, "loyalty", current_user)
    cfg = await _get_or_create_config(restaurant_id)
    return _public_config_view(cfg)


@router.put("/restaurants/{restaurant_id}/loyalty/config")
async def update_config(
    restaurant_id: str,
    payload: LoyaltyConfigUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    await _get_or_create_config(restaurant_id)

    updates: dict[str, Any] = {}
    if payload.caffesta_account_name is not None:
        updates["caffesta_account_name"] = payload.caffesta_account_name.strip()
    if payload.caffesta_api_key is not None and payload.caffesta_api_key.strip():
        updates["caffesta_api_key_enc"] = encrypt(payload.caffesta_api_key.strip())
    if payload.pos_id is not None:
        updates["pos_id"] = payload.pos_id.strip()
    if payload.sync_interval_min is not None:
        updates["sync_interval_min"] = max(1, min(60, int(payload.sync_interval_min)))
    if payload.template_accrual is not None:
        updates["template_accrual"] = payload.template_accrual
    if payload.template_debit is not None:
        updates["template_debit"] = payload.template_debit
    if payload.start_message_text is not None:
        updates["start_message_text"] = payload.start_message_text
    if payload.welcome_message_text is not None:
        updates["welcome_message_text"] = payload.welcome_message_text
    if payload.invite_message_text is not None:
        updates["invite_message_text"] = payload.invite_message_text
    if payload.is_enabled is not None:
        updates["is_enabled"] = bool(payload.is_enabled)
    if payload.caffesta_loyalty_product_id is not None:
        updates["caffesta_loyalty_product_id"] = payload.caffesta_loyalty_product_id.strip()
    if payload.caffesta_auto_register is not None:
        updates["caffesta_auto_register"] = bool(payload.caffesta_auto_register)

    # Обработка bot token — при смене нужно обновить webhook в Telegram.
    if payload.telegram_bot_token is not None and payload.telegram_bot_token.strip():
        token = payload.telegram_bot_token.strip()
        updates["telegram_bot_token_enc"] = encrypt(token)
        # Достаём username бота (для UI) — best-effort
        updates["telegram_bot_username"] = await get_bot_username(token) or ""
        # Регистрируем webhook
        base = _resolve_public_base_url(request)
        secret = (await db.loyalty_config.find_one(
            {"restaurant_id": restaurant_id}, {"_id": 0, "webhook_secret": 1}
        )).get("webhook_secret") or ""
        if base and secret:
            url = f"{base}/api/loyalty/webhook/{restaurant_id}/{secret}"
            ok, desc = await set_webhook(token, url)
            if not ok:
                logger.warning("set_webhook failed for %s: %s", restaurant_id, desc)

    if updates:
        await db.loyalty_config.update_one({"restaurant_id": restaurant_id}, {"$set": updates})

    doc = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    return _public_config_view(doc)


@router.delete("/restaurants/{restaurant_id}/loyalty/bot")
async def delete_bot_token(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    """Удаляем токен бота и снимаем webhook в Telegram."""
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    cfg = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if cfg:
        token = decrypt(cfg.get("telegram_bot_token_enc") or "")
        if token:
            await delete_webhook(token)
    await db.loyalty_config.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"telegram_bot_token_enc": "", "telegram_bot_username": ""}},
    )
    return {"ok": True}


@router.post("/restaurants/{restaurant_id}/loyalty/sync-now")
async def trigger_sync(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    err, info = await sync_restaurant(restaurant_id)
    return {"ok": err is None, "error": err or "", "info": info}


@router.delete("/restaurants/{restaurant_id}/loyalty/clients/{client_id}")
async def delete_client(
    restaurant_id: str,
    client_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Удалить клиента программы лояльности.
    При следующей синхронизации Caffesta он МОЖЕТ появиться снова (если ещё есть в POS).
    Логи уведомлений по клиенту сохраняются, только помечаются как orphan.
    """
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    doc = await db.loyalty_clients.find_one(
        {"restaurant_id": restaurant_id, "id": client_id}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Клиент не найден")
    await db.loyalty_clients.delete_one({"restaurant_id": restaurant_id, "id": client_id})
    return {"ok": True, "deleted_id": client_id, "phone": doc.get("phone_norm")}


@router.post("/restaurants/{restaurant_id}/loyalty/clients/delete-all")
async def delete_all_clients(
    restaurant_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Полная очистка списка клиентов лояльности (для повторной синхронизации с нуля).
    Также сбрасывает last_clients_ts=0 в конфиге, чтобы при следующем тике Caffesta
    отдала ВСЕХ клиентов заново.
    """
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    res = await db.loyalty_clients.delete_many({"restaurant_id": restaurant_id})
    await db.loyalty_config.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"last_clients_ts": 0}},
    )
    return {"ok": True, "deleted": res.deleted_count}


# ─── Сообщения и массовая рассылка ─────────────────────────────────────────

class SingleMessageRequest(BaseModel):
    text: str


class BroadcastRequest(BaseModel):
    text: str
    # Фильтры (все опциональны). Если ничего не задано — шлём всем привязанным.
    min_balance: Optional[float] = None
    max_balance: Optional[float] = None
    phone_prefixes: Optional[list[str]] = None  # напр. ["375"]
    dry_run: bool = False  # если true — только считаем получателей, не отправляем


async def _log_message(
    restaurant_id: str,
    client_id: str,
    phone_norm: str,
    text: str,
    ok: bool,
    http_code: int,
    err: str,
    kind: str = "manual",
):
    doc = {
        "id": __import__("uuid").uuid4().hex,
        "restaurant_id": restaurant_id,
        "client_id": client_id or "",
        "phone_norm": phone_norm or "",
        "kind": kind,
        "amount": 0.0,
        "balance_after": 0.0,
        "message": text,
        "sent_at": datetime.now(timezone.utc),
        "status": "success" if ok else "error",
        "error_text": err,
        "http_code": http_code,
    }
    await db.loyalty_notifications_log.insert_one(doc)


@router.post("/restaurants/{restaurant_id}/loyalty/clients/{client_id}/message")
async def send_single_message(
    restaurant_id: str,
    client_id: str,
    payload: SingleMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """Отправить произвольное сообщение одному клиенту."""
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(400, "Пустое сообщение")
    client_doc = await db.loyalty_clients.find_one(
        {"restaurant_id": restaurant_id, "id": client_id}, {"_id": 0}
    )
    if not client_doc:
        raise HTTPException(404, "Клиент не найден")
    if not client_doc.get("telegram_chat_id"):
        raise HTTPException(400, "У клиента не привязан Telegram")

    cfg = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    bot_token = decrypt((cfg or {}).get("telegram_bot_token_enc") or "")
    if not bot_token:
        raise HTTPException(400, "Токен бота не настроен")

    # Плейсхолдеры {name}, {balance} доступны и в ручных сообщениях.
    formatted = text.format(
        name=client_doc.get("name") or "",
        balance=f"{float(client_doc.get('last_bonus_balance') or 0):.2f}".rstrip("0").rstrip("."),
    )
    ok, code, err = await send_telegram_message(bot_token, int(client_doc["telegram_chat_id"]), formatted)
    await _log_message(
        restaurant_id, client_doc["id"], client_doc["phone_norm"],
        formatted, ok, code, err, kind="manual",
    )
    if not ok:
        raise HTTPException(502, f"Ошибка отправки: {err} (HTTP {code})")
    return {"ok": True}


@router.post("/restaurants/{restaurant_id}/loyalty/broadcast")
async def broadcast(
    restaurant_id: str,
    payload: BroadcastRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Массовая рассылка всем привязанным клиентам.
    dry_run=true — вернуть только количество получателей без отправки.
    """
    await ensure_module_access(restaurant_id, "loyalty", current_user, write=True)
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(400, "Пустое сообщение")

    cfg = await db.loyalty_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    bot_token = decrypt((cfg or {}).get("telegram_bot_token_enc") or "")
    if not payload.dry_run and not bot_token:
        raise HTTPException(400, "Токен бота не настроен")

    q: dict[str, Any] = {
        "restaurant_id": restaurant_id,
        "telegram_chat_id": {"$ne": None},
    }
    if payload.min_balance is not None:
        q["last_bonus_balance"] = {"$gte": float(payload.min_balance)}
    if payload.max_balance is not None:
        q.setdefault("last_bonus_balance", {})
        q["last_bonus_balance"]["$lte"] = float(payload.max_balance)
    if payload.phone_prefixes:
        q["$or"] = [{"phone_norm": {"$regex": f"^{p}"}} for p in payload.phone_prefixes]

    recipients = await db.loyalty_clients.find(q, {"_id": 0}).to_list(50000)
    if payload.dry_run:
        return {"recipients": len(recipients), "dry_run": True}

    # Telegram: не более 30 сообщений в секунду. Держим ~30ms между отправками.
    import asyncio as _asyncio
    sent, failed = 0, 0
    for c in recipients:
        formatted = text.format(
            name=c.get("name") or "",
            balance=f"{float(c.get('last_bonus_balance') or 0):.2f}".rstrip("0").rstrip("."),
        )
        ok, code, err = await send_telegram_message(bot_token, int(c["telegram_chat_id"]), formatted)
        await _log_message(
            restaurant_id, c["id"], c["phone_norm"], formatted, ok, code, err, kind="broadcast",
        )
        if ok:
            sent += 1
        else:
            failed += 1
        await _asyncio.sleep(0.035)
    return {"recipients": len(recipients), "sent": sent, "failed": failed}


# ─── Clients & Logs (read-only, для админки) ───────────────────────────────

@router.get("/restaurants/{restaurant_id}/loyalty/clients")
async def list_clients(
    restaurant_id: str,
    search: Optional[str] = None,
    linked_only: bool = False,
    limit: int = 500,
    current_user: dict = Depends(get_current_user),
):
    await ensure_module_access(restaurant_id, "loyalty", current_user)
    q: dict[str, Any] = {"restaurant_id": restaurant_id}
    if linked_only:
        q["telegram_chat_id"] = {"$ne": None}
    if search:
        s = search.strip()
        digits = "".join(ch for ch in s if ch.isdigit())
        or_clauses: list = []
        if digits:
            or_clauses.append({"phone_norm": {"$regex": digits}})
        or_clauses.append({"name": {"$regex": s, "$options": "i"}})
        or_clauses.append({"telegram_username": {"$regex": s, "$options": "i"}})
        q["$or"] = or_clauses
    docs = await db.loyalty_clients.find(q, {"_id": 0}).sort("last_synced_at", -1).limit(limit).to_list(limit)
    return docs


@router.get("/restaurants/{restaurant_id}/loyalty/logs")
async def list_logs(
    restaurant_id: str,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    current_user: dict = Depends(get_current_user),
):
    await ensure_module_access(restaurant_id, "loyalty", current_user)
    q: dict[str, Any] = {"restaurant_id": restaurant_id}
    if kind:
        q["kind"] = kind
    if status:
        q["status"] = status
    docs = await db.loyalty_notifications_log.find(q, {"_id": 0}).sort("sent_at", -1).limit(limit).to_list(limit)
    return docs


@router.get("/restaurants/{restaurant_id}/loyalty/stats")
async def stats(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    """Компактная сводка для дашборда."""
    await ensure_module_access(restaurant_id, "loyalty", current_user)
    total_clients = await db.loyalty_clients.count_documents({"restaurant_id": restaurant_id})
    linked = await db.loyalty_clients.count_documents(
        {"restaurant_id": restaurant_id, "telegram_chat_id": {"$ne": None}}
    )
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    notifications_today = await db.loyalty_notifications_log.count_documents(
        {"restaurant_id": restaurant_id, "sent_at": {"$gte": since}, "status": "success"}
    )
    errors_today = await db.loyalty_notifications_log.count_documents(
        {"restaurant_id": restaurant_id, "sent_at": {"$gte": since}, "status": "error"}
    )
    return {
        "total_clients": total_clients,
        "linked_clients": linked,
        "notifications_today": notifications_today,
        "errors_today": errors_today,
    }


# ─── Webhook (публичный) ───────────────────────────────────────────────────

@router.post("/loyalty/webhook/{restaurant_id}/{secret}")
async def loyalty_webhook(restaurant_id: str, secret: str, request: Request):
    """
    Telegram присылает сюда обновления от бота лояльности.
    Валидируем secret из конфига — иначе игнорируем.
    """
    cfg = await db.loyalty_config.find_one(
        {"restaurant_id": restaurant_id, "webhook_secret": secret}, {"_id": 0}
    )
    if not cfg:
        # Возвращаем 200, чтобы Telegram не переспрашивал бесконечно.
        return {"ok": True}
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}
    try:
        await handle_update(restaurant_id, update)
    except Exception as exc:
        logger.exception("loyalty bot handler error: %s", exc)
    return {"ok": True}
