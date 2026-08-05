"""
Карта лояльности внутри Telegram-бота.

- Генерация картинки-карты через Pillow.
- Отправка sendPhoto + pinChatMessage при первой привязке.
- Обновление подписи (editMessageCaption) при изменении баланса.
- Команда /card — переотправить и запинить заново.

Номер карты — внутренний, начинается с CARD_NUMBER_START (1000 по умолчанию),
атомарно инкрементируется через MongoDB findAndModify.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image, ImageDraw, ImageFont

from database import db

logger = logging.getLogger("loyalty.card")

TELEGRAM_API = "https://api.telegram.org"
CARD_NUMBER_START = int(os.environ.get("LOYALTY_CARD_START", "1000"))
CARD_WIDTH = 1013
CARD_HEIGHT = 638

# Пути к системным шрифтам DejaVu (уже в контейнере через fonts-dejavu-core).
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    idx = 0 if bold else 1
    for path in [FONT_PATHS[idx], FONT_PATHS[1 - idx]]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


async def next_card_number(restaurant_id: str) -> int:
    """
    Атомарный автоинкремент внутреннего счётчика номеров карт на ресторан.
    Хранится в отдельной коллекции `loyalty_counters`.
    """
    res = await db.loyalty_counters.find_one_and_update(
        {"_id": f"card:{restaurant_id}"},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True,
    )
    val = int(res.get("value") or 0)
    # Первое обращение даст 1 → сдвигаем на CARD_NUMBER_START-1
    return val + (CARD_NUMBER_START - 1)


def generate_card_image(
    restaurant_name: str,
    card_number: int,
    accent_hex: str = "#5DA9A4",  # mint из темы приложения
) -> bytes:
    """
    Генерация PNG-карты клиента.
    Дизайн: тёмный фон + акцентная плашка сверху с названием ресторана + крупный номер карты.
    """
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (17, 24, 24))
    draw = ImageDraw.Draw(img)

    # Мягкий градиент-имитация: несколько горизонтальных полос
    accent = tuple(int(accent_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    for y in range(CARD_HEIGHT):
        t = y / CARD_HEIGHT
        r = int(17 + (accent[0] - 17) * t * 0.35)
        g = int(24 + (accent[1] - 24) * t * 0.35)
        b = int(24 + (accent[2] - 24) * t * 0.35)
        draw.line([(0, y), (CARD_WIDTH, y)], fill=(r, g, b))

    # Верхняя плашка с названием заведения
    plate_h = 130
    draw.rectangle([(0, 0), (CARD_WIDTH, plate_h)], fill=accent)
    name_font = _load_font(52, bold=True)
    name_bbox = draw.textbbox((0, 0), restaurant_name, font=name_font)
    name_w = name_bbox[2] - name_bbox[0]
    draw.text(
        ((CARD_WIDTH - name_w) // 2, (plate_h - (name_bbox[3] - name_bbox[1])) // 2 - 6),
        restaurant_name,
        font=name_font,
        fill=(255, 255, 255),
    )

    # Слово «Карта лояльности»
    subtitle_font = _load_font(30, bold=False)
    subtitle = "КАРТА ЛОЯЛЬНОСТИ"
    st_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    draw.text(
        ((CARD_WIDTH - (st_bbox[2] - st_bbox[0])) // 2, plate_h + 60),
        subtitle,
        font=subtitle_font,
        fill=(200, 220, 218),
    )

    # Крупный номер карты
    num_font = _load_font(170, bold=True)
    num_str = f"№{card_number}"
    num_bbox = draw.textbbox((0, 0), num_str, font=num_font)
    num_w = num_bbox[2] - num_bbox[0]
    draw.text(
        ((CARD_WIDTH - num_w) // 2, plate_h + 130),
        num_str,
        font=num_font,
        fill=(255, 255, 255),
    )

    # Нижняя строка — CVC-подобный визуальный акцент (декор)
    deco_font = _load_font(22, bold=False)
    deco = "Бонусная программа · Мята"
    dc_bbox = draw.textbbox((0, 0), deco, font=deco_font)
    draw.text(
        ((CARD_WIDTH - (dc_bbox[2] - dc_bbox[0])) // 2, CARD_HEIGHT - 60),
        deco,
        font=deco_font,
        fill=(200, 220, 218),
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def format_caption(card_number: int, balance: float, currency: str = "BYN") -> str:
    b_fmt = f"{balance:.2f}".rstrip("0").rstrip(".") if balance else "0"
    return f"Карта №{card_number}\nБаланс: {b_fmt} {currency}"


async def send_card_and_pin(
    bot_token: str,
    chat_id: int,
    restaurant_name: str,
    card_number: int,
    balance: float,
    currency: str = "BYN",
) -> Optional[int]:
    """
    Отправить фото карты клиенту + запинить сообщение.
    Возвращает message_id закреплённого сообщения (или None при ошибке).
    """
    if not bot_token or not chat_id:
        return None
    image_bytes = generate_card_image(restaurant_name, card_number)
    caption = format_caption(card_number, balance, currency)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": ("card.png", image_bytes, "image/png")},
            )
            j = resp.json()
            if not j.get("ok"):
                logger.warning("sendPhoto failed: %s", j)
                return None
            message_id = int(j["result"]["message_id"])
            # Пинуем без уведомления
            pin_resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/pinChatMessage",
                json={"chat_id": chat_id, "message_id": message_id, "disable_notification": True},
            )
            pj = pin_resp.json()
            if not pj.get("ok"):
                # Не критично — карту прислали, просто не запинили
                logger.info("pinChatMessage warning: %s", pj)
            return message_id
    except Exception as exc:
        logger.warning("send_card_and_pin exception: %s", exc)
        return None


async def edit_card_caption(
    bot_token: str,
    chat_id: int,
    message_id: int,
    card_number: int,
    balance: float,
    currency: str = "BYN",
) -> tuple[bool, str]:
    """
    Обновить подпись к закреплённой карте (при изменении баланса).
    Возвращает (ok, error_description).
    Если Telegram отдал "message to edit not found" — вызывающий должен сбросить pinned_message_id.
    """
    if not bot_token or not chat_id or not message_id:
        return False, "missing params"
    caption = format_caption(card_number, balance, currency)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{TELEGRAM_API}/bot{bot_token}/editMessageCaption",
                json={"chat_id": chat_id, "message_id": message_id, "caption": caption},
            )
        j = resp.json()
        if j.get("ok"):
            return True, ""
        desc = j.get("description") or ""
        return False, desc
    except Exception as exc:
        return False, str(exc)
