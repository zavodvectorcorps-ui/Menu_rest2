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


@router.get("/restaurants/{restaurant_id}/caffesta/probe-transfers")
async def probe_transfers(
    restaurant_id: str,
    date: str = "",
    current_user: dict = Depends(get_current_user),
):
    """Probe: пытаемся найти эндпоинт Caffesta API для «История счетов /
    Перенос блюд» (тот, что в UI на /admin/orders_history/list). Если найдём —
    можно вывести в сводку строку «🔄 Переносы блюд: N» для контроля
    официантов (частые переносы — индикатор подозрительной активности)."""
    from auth import has_role
    if not has_role(current_user, "superadmin"):
        raise HTTPException(403, "Только суперадмин")
    from services.caffesta import get_caffesta_config, _base_url, _headers, _safe_json
    import httpx
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}
    pos_id = config.get("pos_id", 1)
    candidates = [
        f"v1.0/draft/get_orders_history/{pos_id}/0",
        f"v1.0/draft/get_orders_history/{pos_id}",
        f"v1.0/draft/get_account_history/{pos_id}/0",
        f"v1.0/draft/get_transfers/{pos_id}/0",
        f"v1.0/draft/get_account_transfers/{pos_id}/0",
        f"v1.0/draft/get_dish_transfers/{pos_id}/0",
        f"v1.0/draft/orders_history/{pos_id}/0",
        f"v1.0/draft/get_order_actions/{pos_id}/0",
    ]
    findings = []
    async with httpx.AsyncClient(timeout=20) as client:
        for path in candidates:
            url = f"{_base_url(config['account_name'])}/{path}"
            try:
                resp = await client.get(url, headers=_headers(config["api_key"]))
                snippet = (resp.text or "")[:600]
                ok_json, rows = False, 0
                try:
                    j = resp.json()
                    ok_json = True
                    if isinstance(j, list):
                        rows = len(j)
                    elif isinstance(j, dict):
                        d = j.get("data")
                        if isinstance(d, list):
                            rows = len(d)
                except Exception:
                    pass
                findings.append({
                    "url": url, "status": resp.status_code,
                    "is_json": ok_json, "row_count": rows,
                    "body_sample": snippet,
                })
            except Exception as e:
                findings.append({"url": url, "error": str(e)})
    return {"ok": True, "data": findings}


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

    # Несколько формул-кандидатов: пытаемся найти ту, что совпадёт с Caffesta UI
    f_total_only = sum(float(r.get("total_sum", 0) or 0) for r in receipts)
    f_total_minus_disc = sum(
        float(r.get("total_sum", 0) or 0) - abs(float(r.get("discount_sum", 0) or 0))
        for r in receipts
    )
    # Ключевая гипотеза: для чеков с total_sum > 0 — minus discount; для total_sum = 0
    # (оплата сертификатом) — net = abs(discount_sum)
    f_split_zero = 0.0
    for r in receipts:
        ts = float(r.get("total_sum", 0) or 0)
        ds = abs(float(r.get("discount_sum", 0) or 0))
        if ts > 0:
            f_split_zero += ts - ds
        else:
            f_split_zero += ds
    # Или для total_sum=0 не считаем (т.е. они = 0 в выручке)
    f_only_paid = sum(
        float(r.get("total_sum", 0) or 0) - abs(float(r.get("discount_sum", 0) or 0))
        for r in receipts if float(r.get("total_sum", 0) or 0) > 0
    )
    # Или: total + abs(discount) для чеков с total=0 (сертификаты), плюс все остальные total
    f_certs_added = sum(
        float(r.get("total_sum", 0) or 0)
        + (abs(float(r.get("discount_sum", 0) or 0)) if float(r.get("total_sum", 0) or 0) == 0 else 0)
        for r in receipts
    )

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
        "candidate_formulas": {
            "F1_total_only": round(f_total_only, 2),
            "F2_total_minus_abs_disc": round(f_total_minus_disc, 2),
            "F3_split_zero_certificates": round(f_split_zero, 2),
            "F4_only_paid_minus_disc": round(f_only_paid, 2),
            "F5_total_plus_disc_for_zero": round(f_certs_added, 2),
        },
        "caffesta_target_hint": "Какая F-формула из candidate_formulas даёт 2186.20 — ту и зафиксируем",
        "all_receipts": [
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
            for r in receipts
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
