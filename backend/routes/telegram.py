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
                    json={"commands": [
                        {"command": "start", "description": "Подписаться на уведомления"},
                        {"command": "orders", "description": "Активные заказы"},
                        {"command": "calls", "description": "Активные вызовы"},
                        {"command": "stats", "description": "Статистика за сегодня"},
                    ]}
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
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return {"ok": True}

    bot_token = settings["telegram_bot_token"]
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    restaurant_name = restaurant.get("name", "Ресторан") if restaurant else "Ресторан"

    # Handle callback_query (inline button presses)
    callback = request.get("callback_query")
    if callback:
        await handle_callback_query(bot_token, restaurant_id, callback)
        return {"ok": True}

    # Handle messages
    message = request.get("message", {})
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"ok": True}

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
                f"Доступные команды:\n"
                f"/orders — Активные заказы\n"
                f"/calls — Активные вызовы\n"
                f"/stats — Статистика за сегодня"
            )
        else:
            await send_telegram_message(
                bot_token, chat_id,
                f"Вы уже подписаны на уведомления <b>{restaurant_name}</b>.\n\n"
                f"Доступные команды:\n"
                f"/orders — Активные заказы\n"
                f"/calls — Активные вызовы\n"
                f"/stats — Статистика за сегодня"
            )

    elif text.startswith("/orders"):
        await handle_orders_command(bot_token, chat_id, restaurant_id)

    elif text.startswith("/calls"):
        await handle_calls_command(bot_token, chat_id, restaurant_id)

    elif text.startswith("/stats"):
        await handle_stats_command(bot_token, chat_id, restaurant_id, restaurant_name)

    return {"ok": True}


async def handle_callback_query(bot_token: str, restaurant_id: str, callback: dict):
    from services.telegram import answer_callback_query, edit_telegram_message, build_order_keyboard, STATUS_LABELS
    from services.websocket import manager

    callback_id = callback.get("id", "")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    message_id = message.get("message_id")

    if not data or not chat_id:
        return

    # Order actions: o_accept_ID, o_done_ID, o_cancel_ID
    if data.startswith("o_"):
        parts = data.split("_", 2)
        if len(parts) < 3:
            return
        action, order_id = parts[1], parts[2]

        order = await db.orders.find_one({"id": order_id, "restaurant_id": restaurant_id}, {"_id": 0})
        if not order:
            await answer_callback_query(bot_token, callback_id, "Заказ не найден")
            return

        if action == "accept":
            new_status = "in_progress"
            status_text = "👨‍🍳 Принят в работу"
        elif action == "done":
            new_status = "completed"
            status_text = "✅ Выполнен"
        elif action == "cancel":
            new_status = "cancelled"
            status_text = "❌ Отменён"
        else:
            return

        await db.orders.update_one({"id": order_id}, {"$set": {"status": new_status}})

        # Update the message text with new status
        original_text = message.get("text", "")
        # Remove old status line if present
        lines = original_text.split("\n")
        lines = [l for l in lines if not l.startswith("📊 Статус:")]
        updated_text = "\n".join(lines) + f"\n\n📊 Статус: {status_text}"

        new_keyboard = build_order_keyboard(order_id, new_status) if new_status == "in_progress" else None
        await edit_telegram_message(bot_token, chat_id, message_id, updated_text, new_keyboard)
        await answer_callback_query(bot_token, callback_id, status_text)

        # Broadcast to admin WS and notify all subscribers
        updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        if updated_order:
            from helpers import serialize_doc
            await manager.broadcast(restaurant_id, "order_status_changed", serialize_doc(updated_order))

    # Staff call actions: c_done_ID
    elif data.startswith("c_done_"):
        call_id = data[7:]  # after "c_done_"
        call = await db.staff_calls.find_one({"id": call_id, "restaurant_id": restaurant_id}, {"_id": 0})
        if not call:
            await answer_callback_query(bot_token, callback_id, "Вызов не найден")
            return

        await db.staff_calls.update_one({"id": call_id}, {"$set": {"status": "completed"}})

        original_text = message.get("text", "")
        updated_text = original_text + "\n\n✅ Выполнен"
        await edit_telegram_message(bot_token, chat_id, message_id, updated_text, None)
        await answer_callback_query(bot_token, callback_id, "✅ Вызов закрыт")

        await manager.broadcast(restaurant_id, "staff_call_completed", {"id": call_id, "status": "completed"})


async def handle_orders_command(bot_token: str, chat_id: str, restaurant_id: str):
    from services.telegram import build_order_keyboard, STATUS_LABELS

    orders = await db.orders.find(
        {"restaurant_id": restaurant_id, "status": {"$in": ["new", "in_progress"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)

    if not orders:
        await send_telegram_message(bot_token, chat_id, "📋 Активных заказов нет")
        return

    for order in orders:
        items_text = "\n".join([f"  • {i['name']} x{i['quantity']}" for i in order.get('items', [])])
        status = STATUS_LABELS.get(order['status'], order['status'])
        is_pre = order.get('is_preorder', False)

        if is_pre:
            msg = f"📋 <b>Предзаказ</b> {status}\n👤 {order.get('customer_name', '—')}\n📅 {order.get('preorder_date', '')} {order.get('preorder_time', '')}\n\n{items_text}\n💰 <b>{order['total']} BYN</b>"
        else:
            msg = f"🍽 <b>Заказ</b> — Стол #{order.get('table_number', '?')} {status}\n\n{items_text}\n💰 <b>{order['total']} BYN</b>"

        keyboard = build_order_keyboard(order['id'], order['status'])
        await send_telegram_message(bot_token, chat_id, msg, keyboard)


async def handle_calls_command(bot_token: str, chat_id: str, restaurant_id: str):
    from services.telegram import build_call_keyboard

    calls = await db.staff_calls.find(
        {"restaurant_id": restaurant_id, "status": {"$in": ["pending", "acknowledged"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)

    if not calls:
        await send_telegram_message(bot_token, chat_id, "🔔 Активных вызовов нет")
        return

    for call in calls:
        msg = f"🔔 <b>{call.get('call_type_name', 'Вызов')}</b>\nСтол #{call.get('table_number', '?')}"
        keyboard = build_call_keyboard(call['id'])
        await send_telegram_message(bot_token, chat_id, msg, keyboard)


async def handle_stats_command(bot_token: str, chat_id: str, restaurant_id: str, restaurant_name: str):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    orders = await db.orders.find(
        {"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}},
        {"_id": 0}
    ).to_list(1000)

    total_orders = len(orders)
    active_orders = len([o for o in orders if o['status'] in ('new', 'in_progress')])
    completed_orders = len([o for o in orders if o['status'] == 'completed'])
    revenue = sum(o.get('total', 0) for o in orders if o['status'] != 'cancelled')

    calls_total = await db.staff_calls.count_documents(
        {"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}}
    )
    calls_active = await db.staff_calls.count_documents(
        {"restaurant_id": restaurant_id, "status": {"$in": ["pending", "acknowledged"]}, "created_at": {"$gte": today_start.isoformat()}}
    )

    views = await db.menu_views.count_documents(
        {"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}}
    )

    msg = (
        f"📊 <b>{restaurant_name}</b> — Сегодня\n\n"
        f"🍽 Заказов: {total_orders} (активных: {active_orders}, выполнено: {completed_orders})\n"
        f"💰 Выручка: {revenue:.2f} BYN\n"
        f"🔔 Вызовов: {calls_total} (активных: {calls_active})\n"
        f"👁 Просмотров меню: {views}"
    )
    await send_telegram_message(bot_token, chat_id, msg)
