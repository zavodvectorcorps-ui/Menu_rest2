from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
import os
import logging
import httpx
from pathlib import Path

from database import db
from models import TelegramBotUpdate
from auth import get_current_user, check_restaurant_access
from services.telegram import TELEGRAM_API, send_telegram_message

router = APIRouter()


@router.get("/restaurants/{restaurant_id}/telegram-bot")
async def get_telegram_bot(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    bot_token = settings.get("telegram_bot_token", "") if settings else ""

    subscribers = await db.telegram_subscribers.find(
        {"restaurant_id": restaurant_id}, {"_id": 0}
    ).to_list(500)

    bot_info = None
    webhook_set = False
    if bot_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{TELEGRAM_API}{bot_token}/getMe")
                if resp.status_code == 200:
                    bot_info = resp.json().get("result")
                wh_resp = await client.get(f"{TELEGRAM_API}{bot_token}/getWebhookInfo")
                if wh_resp.status_code == 200:
                    wh_url = wh_resp.json().get("result", {}).get("url", "")
                    webhook_set = bool(wh_url)
        except Exception:
            pass

    return {
        "bot_token": bot_token,
        "bot_info": bot_info,
        "webhook_set": webhook_set,
        "subscribers": [{"chat_id": s["chat_id"], "username": s.get("username", ""), "first_name": s.get("first_name", ""), "subscribed_at": s.get("subscribed_at", "")} for s in subscribers]
    }


@router.put("/restaurants/{restaurant_id}/telegram-bot")
async def update_telegram_bot(restaurant_id: str, data: TelegramBotUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    bot_token = data.telegram_bot_token.strip()
    webhook_url = ""

    if bot_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{TELEGRAM_API}{bot_token}/getMe")
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail="Невалидный токен бота. Проверьте токен от @BotFather")
        except httpx.RequestError:
            raise HTTPException(status_code=400, detail="Не удалось подключиться к Telegram API")

        webhook_url = f"{os.environ.get('REACT_APP_BACKEND_URL', '')}/api/telegram/webhook/{restaurant_id}"
        frontend_env_path = Path(__file__).parent.parent.parent / "frontend" / ".env"
        if frontend_env_path.exists():
            with open(frontend_env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        external_url = line.split("=", 1)[1].strip()
                        webhook_url = f"{external_url}/api/telegram/webhook/{restaurant_id}"
                        break

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{TELEGRAM_API}{bot_token}/setWebhook",
                    json={"url": webhook_url}
                )
                await client.post(
                    f"{TELEGRAM_API}{bot_token}/setMyCommands",
                    json={"commands": [{"command": "start", "description": "Подписаться на уведомления"}]}
                )
        except Exception as e:
            logging.error(f"Webhook setup error: {e}")
    else:
        old_settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
        old_token = old_settings.get("telegram_bot_token") if old_settings else None
        if old_token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"{TELEGRAM_API}{old_token}/deleteWebhook")
            except Exception:
                pass

    await db.settings.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"telegram_bot_token": bot_token}}
    )

    return {"message": "Настройки бота обновлены", "webhook_url": webhook_url if bot_token else ""}


@router.delete("/restaurants/{restaurant_id}/telegram-bot")
async def disconnect_telegram_bot(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    old_token = settings.get("telegram_bot_token") if settings else None
    if old_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(f"{TELEGRAM_API}{old_token}/deleteWebhook")
        except Exception:
            pass

    await db.settings.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"telegram_bot_token": ""}}
    )
    await db.telegram_subscribers.delete_many({"restaurant_id": restaurant_id})

    return {"message": "Бот отключён"}


@router.delete("/restaurants/{restaurant_id}/telegram-bot/subscribers/{chat_id}")
async def remove_telegram_subscriber(restaurant_id: str, chat_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.telegram_subscribers.delete_one({"restaurant_id": restaurant_id, "chat_id": chat_id})
    return {"message": "Подписчик удалён"}


@router.post("/telegram/webhook/{restaurant_id}")
async def telegram_webhook(restaurant_id: str, request: dict):
    message = request.get("message", {})
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = message.get("text", "")

    if not chat_id:
        return {"ok": True}

    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return {"ok": True}

    bot_token = settings["telegram_bot_token"]
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    restaurant_name = restaurant.get("name", "Ресторан") if restaurant else "Ресторан"

    if text.startswith("/start"):
        existing = await db.telegram_subscribers.find_one(
            {"restaurant_id": restaurant_id, "chat_id": chat_id}
        )
        if not existing:
            await db.telegram_subscribers.insert_one({
                "restaurant_id": restaurant_id,
                "chat_id": chat_id,
                "username": chat.get("username", ""),
                "first_name": chat.get("first_name", ""),
                "is_active": True,
                "subscribed_at": datetime.now(timezone.utc).isoformat()
            })
            await send_telegram_message(
                bot_token, chat_id,
                f"✅ Вы подписаны на уведомления <b>{restaurant_name}</b>!\n\n"
                f"Вы будете получать уведомления о:\n"
                f"🔔 Вызовах персонала\n"
                f"💳 Запросах счёта\n"
                f"🍽 Новых заказах"
            )
        else:
            await send_telegram_message(
                bot_token, chat_id,
                f"Вы уже подписаны на уведомления <b>{restaurant_name}</b>."
            )

    return {"ok": True}
