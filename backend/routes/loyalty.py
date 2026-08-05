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
from models_loyalty import DEFAULT_TEMPLATE_ACCRUAL, DEFAULT_TEMPLATE_DEBIT, LoyaltyConfig
from routes.telegram import _resolve_public_base_url  # переиспользуем — тот же паттерн
from services.loyalty_bot import (
    delete_webhook,
    get_bot_username,
    handle_update,
    set_webhook,
)
from services.loyalty_crypto import decrypt, encrypt, mask
from services.loyalty_sync import sync_restaurant

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
    is_enabled: Optional[bool] = None


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
        "is_enabled": bool(doc.get("is_enabled")),
        "last_synced_at": doc.get("last_synced_at"),
        "last_error": doc.get("last_error") or "",
        "last_error_at": doc.get("last_error_at"),
        "last_clients_ts": int(doc.get("last_clients_ts") or 0),
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
    if payload.is_enabled is not None:
        updates["is_enabled"] = bool(payload.is_enabled)

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
    err = await sync_restaurant(restaurant_id)
    return {"ok": err is None, "error": err or ""}


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
