"""
Endpoints for daily Caffesta Telegram digest:
- Preview the digest text for now
- Manually trigger send (for testing)
- Scheduler is registered globally in server.py lifespan.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException

from auth import check_restaurant_access, get_current_user
from services.digest import build_digest_text, send_daily_digest
from services.caffesta import caffesta_get_all_receipts

router = APIRouter()


@router.get("/restaurants/{restaurant_id}/digest/preview")
async def digest_preview(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    try:
        text = await build_digest_text(restaurant_id)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/restaurants/{restaurant_id}/digest/diagnose")
async def digest_diagnose(
    restaurant_id: str,
    date: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Detailed breakdown for one day: всех чеки + суммы под разными метриками,
    чтобы сверить с Caffesta админкой и найти причину расхождений."""
    await check_restaurant_access(current_user, restaurant_id)
    if not date:
        # Default = вчера (Minsk = UTC+3)
        d = (datetime.now(timezone.utc) + timedelta(hours=3)).date() - timedelta(days=1)
        date = d.strftime("%Y-%m-%d")
    res = await caffesta_get_all_receipts(restaurant_id, date, date)
    if not res.get("ok"):
        raise HTTPException(502, f"Caffesta: {res.get('message')}")
    receipts = res.get("data", [])

    gross = sum(float(r.get("total_sum", 0) or 0) for r in receipts)
    discount = sum(float(r.get("discount_sum", 0) or 0) for r in receipts)
    back = sum(float(r.get("back_pay", 0) or 0) for r in receipts)
    cash = sum(float(r.get("cash_pay", 0) or 0) for r in receipts)
    card = sum(float(r.get("card_pay", 0) or 0) for r in receipts)
    cashless = sum(float(r.get("cashless_pay", 0) or 0) for r in receipts)

    return {
        "date": date,
        "total_receipts": len(receipts),
        "metrics": {
            "gross_total_sum": round(gross, 2),
            "discount_sum": round(discount, 2),
            "back_pay_sum": round(back, 2),
            "net_after_discount": round(gross - discount, 2),
            "net_after_discount_and_returns": round(gross - discount - back, 2),
            "cash_pay_sum": round(cash, 2),
            "card_pay_sum": round(card, 2),
            "cashless_pay_sum": round(cashless, 2),
            "payments_total": round(cash + card + cashless, 2),
        },
        "sample_receipts": [
            {
                "id": r.get("id"),
                "created_at": r.get("created_at"),
                "type": r.get("type"),
                "income": r.get("income"),
                "total_sum": r.get("total_sum"),
                "discount_sum": r.get("discount_sum"),
                "back_pay": r.get("back_pay"),
                "cash_pay": r.get("cash_pay"),
                "card_pay": r.get("card_pay"),
                "cashless_pay": r.get("cashless_pay"),
                "cashlessPayment_id": r.get("cashlessPayment_id"),
            }
            for r in receipts[:5]
        ],
    }


@router.post("/restaurants/{restaurant_id}/digest/send")
async def digest_send(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    """Force-send digest now (ignores daily_digest_enabled, but still needs creds)."""
    await check_restaurant_access(current_user, restaurant_id)
    result = await send_daily_digest(restaurant_id, force=True)
    if not result.get("sent"):
        raise HTTPException(400, f"Не отправлено: {result.get('reason')}")
    return {"sent": True}
