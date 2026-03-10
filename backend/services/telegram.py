import logging
import httpx
from database import db

TELEGRAM_API = "https://api.telegram.org/bot"


async def send_telegram_message(bot_token: str, chat_id: str, text: str, reply_markup: dict = None):
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{TELEGRAM_API}{bot_token}/sendMessage", json=payload)
            return resp.status_code == 200
    except Exception as e:
        logging.error(f"Telegram send error: {e}")
        return False


async def edit_telegram_message(bot_token: str, chat_id: str, message_id: int, text: str, reply_markup: dict = None):
    try:
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{TELEGRAM_API}{bot_token}/editMessageText", json=payload)
            return resp.status_code == 200
    except Exception as e:
        logging.error(f"Telegram edit error: {e}")
        return False


async def answer_callback_query(bot_token: str, callback_query_id: str, text: str = ""):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{TELEGRAM_API}{bot_token}/answerCallbackQuery", json={
                "callback_query_id": callback_query_id, "text": text
            })
    except Exception as e:
        logging.error(f"Telegram callback answer error: {e}")


async def notify_restaurant_telegram(restaurant_id: str, message: str, reply_markup: dict = None):
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return

    bot_token = settings["telegram_bot_token"]
    subscribers = await db.telegram_subscribers.find(
        {"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}
    ).to_list(500)

    for sub in subscribers:
        await send_telegram_message(bot_token, sub["chat_id"], message, reply_markup)


def build_order_keyboard(order_id: str, status: str = "new"):
    if status == "new":
        return {"inline_keyboard": [
            [
                {"text": "✅ Принять", "callback_data": f"o_accept_{order_id}"},
                {"text": "🍽 Готово", "callback_data": f"o_done_{order_id}"},
            ],
            [{"text": "❌ Отклонить", "callback_data": f"o_cancel_{order_id}"}]
        ]}
    elif status == "in_progress":
        return {"inline_keyboard": [
            [{"text": "🍽 Готово", "callback_data": f"o_done_{order_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"o_cancel_{order_id}"}]
        ]}
    return None


def build_call_keyboard(call_id: str):
    return {"inline_keyboard": [
        [{"text": "✅ Принял", "callback_data": f"c_done_{call_id}"}]
    ]}


STATUS_LABELS = {
    "new": "🆕 Новый",
    "in_progress": "👨‍🍳 Готовится",
    "completed": "✅ Выполнен",
    "cancelled": "❌ Отменён",
}
