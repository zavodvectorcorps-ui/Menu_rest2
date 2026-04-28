"""
Daily Telegram digest — summarises yesterday's Caffesta sales broken down by
user-defined time windows, and compares to the same weekday last week.
Scheduled via APScheduler at 10:00 Minsk time (UTC+3 = 07:00 UTC).
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from database import db
from helpers import get_or_create_settings
from services.caffesta import caffesta_get_all_receipts, split_receipt_payments, caffesta_get_products

logger = logging.getLogger(__name__)

MINSK_OFFSET_HOURS = 3


def _minsk_now() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=MINSK_OFFSET_HOURS)


def _hhmm(s: str) -> int:
    h, m = s.split(":", 1)
    return int(h) * 60 + int(m)


def _in_window(dt: datetime, wfrom: int, wto: int) -> bool:
    mn = dt.hour * 60 + dt.minute
    if wfrom <= wto:
        return wfrom <= mn <= wto
    return mn >= wfrom or mn <= wto


async def _collect_for_day(restaurant_id: str, day_date: str):
    """Fetch receipts for a single Minsk date; returns list normalised."""
    res = await caffesta_get_all_receipts(restaurant_id, day_date, day_date)
    return res.get("data", []) if res.get("ok") else []


def _aggregate_window(receipts, wfrom, wto, payment_methods, product_map=None):
    revenue = 0.0
    count = 0
    discount = 0.0
    products = {}
    payments = {}
    for r in receipts:
        dt = r.get("created_dt")
        if not dt:
            continue
        # dt is already in Minsk local time (naive), thanks to caffesta_get_all_receipts normalisation
        if not _in_window(dt, wfrom, wto):
            continue
        rev = float(r.get("total_sum", 0) or 0)
        revenue += rev
        count += 1
        discount += float(r.get("discount_sum", 0) or 0)
        for p in split_receipt_payments(r, payment_methods):
            payments.setdefault(p["name"], 0.0)
            payments[p["name"]] += p["amount"]
        for od in (r.get("order_dishes") or []):
            dish = od.get("dish") or {}
            # Try to resolve product name: direct fields → product_map by dish.id → ref_code → placeholder
            pname = (
                dish.get("title") or dish.get("name") or dish.get("product_title")
            )
            if not pname and product_map:
                # Caffesta returns dish.id as the product_id
                pid = (
                    dish.get("id") or dish.get("product_id") or dish.get("productId")
                    or od.get("product_id") or od.get("productId")
                )
                if pid:
                    try:
                        pname = product_map.get(int(pid))
                    except (ValueError, TypeError):
                        pass
            pname = pname or dish.get("ref_code") or od.get("ref_code") or f"ID #{dish.get('id', '?')}"
            try:
                qty = float(od.get("count") or od.get("qty") or 1)
                # total_sum is the actual charged amount (after discount); total or price*count is before
                psum = float(od.get("total_sum") or od.get("total") or (od.get("price", 0) or 0) * qty)
            except (ValueError, TypeError):
                qty, psum = 1, 0
            products.setdefault(pname, {"qty": 0, "rev": 0.0})
            products[pname]["qty"] += int(qty)
            products[pname]["rev"] += psum
    top3 = sorted(products.items(), key=lambda x: x[1]["rev"], reverse=True)[:3]
    return {
        "revenue": revenue,
        "count": count,
        "discount": discount,
        "avg_check": revenue / count if count else 0,
        "top": [{"name": n, "qty": v["qty"], "revenue": round(v["rev"], 2)} for n, v in top3],
        "payments": {k: round(v, 2) for k, v in payments.items()},
    }


def _delta_str(cur: float, prev: float) -> str:
    if not prev:
        return ""
    diff = cur - prev
    pct = (diff / prev * 100) if prev else 0
    arrow = "▲" if diff >= 0 else "▼"
    return f" {arrow} {abs(pct):.0f}%"


async def build_digest_text(restaurant_id: str) -> str:
    """Build the digest text for yesterday (Minsk TZ) vs same weekday last week."""
    settings = await get_or_create_settings(restaurant_id)
    windows = settings.get("daily_digest_windows") or []
    if not windows:
        windows = [
            {"name": "Завтрак", "time_from": "08:00", "time_to": "12:00"},
            {"name": "Обед", "time_from": "12:00", "time_to": "16:00"},
            {"name": "Вечер", "time_from": "18:00", "time_to": "23:00"},
        ]

    minsk_today = _minsk_now().date()
    y_date = (minsk_today - timedelta(days=1)).strftime("%Y-%m-%d")
    w_date = (minsk_today - timedelta(days=8)).strftime("%Y-%m-%d")

    y_receipts = await _collect_for_day(restaurant_id, y_date)
    w_receipts = await _collect_for_day(restaurant_id, w_date)

    config = await db.caffesta_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    payment_methods = (config or {}).get("payment_methods", [])

    # Fetch Caffesta product map once (product_id -> title) to resolve "—" in top-3
    product_map = {}
    try:
        prods = await caffesta_get_products(restaurant_id)
        if prods.get("ok"):
            for p in prods.get("data", []):
                try:
                    product_map[int(p["product_id"])] = p.get("title") or ""
                except (ValueError, TypeError, KeyError):
                    continue
    except Exception:
        pass

    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0, "name": 1})
    rest_name = restaurant.get("name", "Ресторан") if restaurant else "Ресторан"

    y_full = _aggregate_window(y_receipts, 0, 23 * 60 + 59, payment_methods, product_map)
    w_full = _aggregate_window(w_receipts, 0, 23 * 60 + 59, payment_methods, product_map)

    # Diagnostics: how many receipts fell on the next calendar day (shift overflow past midnight)
    overflow_count = 0
    overflow_revenue = 0.0
    for r in y_receipts:
        dt = r.get("created_dt")
        if dt and dt.strftime("%Y-%m-%d") != y_date:
            overflow_count += 1
            overflow_revenue += float(r.get("total_sum", 0) or 0)

    lines = [
        f"🗓️ <b>{rest_name}</b> — смена {y_date}",
        "",
        f"💰 Выручка: <b>{y_full['revenue']:.2f} BYN</b>"
        f"{_delta_str(y_full['revenue'], w_full['revenue'])} (неделю назад: {w_full['revenue']:.2f})",
        f"🧾 Чеков: <b>{y_full['count']}</b>"
        f"{_delta_str(y_full['count'], w_full['count'])} (вчера-7: {w_full['count']})",
        f"🎯 Средний чек: <b>{y_full['avg_check']:.2f}</b>",
    ]

    if overflow_count > 0:
        lines.append(
            f"🌙 После полуночи (хвост смены): <b>{overflow_count}</b> чеков, "
            f"<b>{overflow_revenue:.2f} BYN</b>"
        )

    if y_full["payments"]:
        pay_parts = ", ".join(f"{k}: {v:.0f}" for k, v in y_full["payments"].items())
        lines.append(f"💳 Оплата: {pay_parts}")

    # First/Last receipt of the shift
    receipts_with_dt = [r for r in y_receipts if r.get("created_dt")]
    if receipts_with_dt:
        first = min(receipts_with_dt, key=lambda r: r["created_dt"])
        last = max(receipts_with_dt, key=lambda r: r["created_dt"])
        lines.append(
            f"🟢 Первый чек: <b>{first['created_dt'].strftime('%H:%M')}</b> "
            f"({float(first.get('total_sum', 0) or 0):.0f} BYN)"
        )
        lines.append(
            f"🔴 Последний чек: <b>{last['created_dt'].strftime('%H:%M')}</b> "
            f"({float(last.get('total_sum', 0) or 0):.0f} BYN)"
        )

    # Windows breakdown
    lines.append("")
    lines.append("📊 <b>По окнам:</b>")
    for w in windows[:4]:
        try:
            wfrom = _hhmm(w["time_from"])
            wto = _hhmm(w["time_to"])
        except Exception:
            continue
        wname = w.get("name") or f"{w['time_from']}–{w['time_to']}"
        y_w = _aggregate_window(y_receipts, wfrom, wto, payment_methods, product_map)
        w_w = _aggregate_window(w_receipts, wfrom, wto, payment_methods, product_map)
        lines.append(
            f"• <b>{wname}</b> ({w['time_from']}–{w['time_to']}): "
            f"{y_w['revenue']:.0f} BYN / {y_w['count']} чек."
            f"{_delta_str(y_w['revenue'], w_w['revenue'])}"
        )

    # Top 3 products of the day
    if y_full["top"]:
        lines.append("")
        lines.append("🏆 <b>Топ-3 за день:</b>")
        for i, t in enumerate(y_full["top"], 1):
            lines.append(f"  {i}. {t['name']} — {t['qty']} шт, {t['revenue']:.0f} BYN")

    return "\n".join(lines)


async def _send_telegram(token: str, chat_id: str, text: str):
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
    except Exception as e:
        logger.warning(f"Digest Telegram send failed: {e}")


async def send_daily_digest(restaurant_id: str, force: bool = False) -> dict:
    """Build and send the digest for a restaurant. If force=True, sends even if disabled."""
    settings = await get_or_create_settings(restaurant_id)
    enabled = settings.get("daily_digest_enabled")
    token = (settings.get("daily_digest_bot_token") or settings.get("telegram_bot_token") or "").strip()
    chat_id = (settings.get("daily_digest_chat_id") or settings.get("telegram_chat_id") or "").strip()
    if not force and not enabled:
        return {"sent": False, "reason": "disabled"}
    if not token or not chat_id:
        return {"sent": False, "reason": "no-credentials"}
    text = await build_digest_text(restaurant_id)
    await _send_telegram(token, chat_id, text)
    return {"sent": True, "text": text}


async def run_daily_digest_job():
    """Iterate all restaurants with digest enabled and send."""
    cursor = db.restaurants.find({}, {"_id": 0, "id": 1, "name": 1})
    async for rest in cursor:
        try:
            settings = await db.settings.find_one({"restaurant_id": rest["id"]}, {"_id": 0})
            if not settings or not settings.get("daily_digest_enabled"):
                continue
            await send_daily_digest(rest["id"])
            logger.info(f"Daily digest sent for {rest.get('name')}")
        except Exception as e:
            logger.exception(f"Digest failed for {rest.get('name')}: {e}")
