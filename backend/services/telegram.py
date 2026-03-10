import logging
import httpx
from database import db

TELEGRAM_API = "https://api.telegram.org/bot"


async def send_telegram_message(bot_token: str, chat_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            return resp.status_code == 200
    except Exception as e:
        logging.error(f"Telegram send error: {e}")
        return False


async def notify_restaurant_telegram(restaurant_id: str, message: str):
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return

    bot_token = settings["telegram_bot_token"]
    subscribers = await db.telegram_subscribers.find(
        {"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}
    ).to_list(500)

    for sub in subscribers:
        await send_telegram_message(bot_token, sub["chat_id"], message)
