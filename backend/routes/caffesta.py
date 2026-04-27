from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from database import db
from auth import get_current_user, check_restaurant_access
from services.caffesta import (
    caffesta_test_connection, caffesta_get_sales, caffesta_get_sales_totals,
    caffesta_get_products, caffesta_send_order, caffesta_get_order_status,
    caffesta_get_sales_shift_day, get_caffesta_config, is_caffesta_enabled,
)

router = APIRouter()


class PaymentMethod(BaseModel):
    name: str
    payment_id: int
    is_default: bool = False


class CaffestaConfigUpdate(BaseModel):
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    pos_id: Optional[int] = None
    payment_id: Optional[int] = None  # legacy/default payment id
    payment_methods: Optional[List[PaymentMethod]] = None
    enabled: Optional[bool] = None


# ============ CONFIG ============

@router.get("/restaurants/{restaurant_id}/caffesta")
async def get_caffesta_settings(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    config = await get_caffesta_config(restaurant_id)
    if not config:
        return {"restaurant_id": restaurant_id, "account_name": "", "api_key": "", "pos_id": None, "payment_id": 1, "payment_methods": [], "enabled": False, "connected": False}
    config.pop("_id", None)
    config.setdefault("payment_methods", [])
    return config


@router.put("/restaurants/{restaurant_id}/caffesta")
async def update_caffesta_settings(restaurant_id: str, data: CaffestaConfigUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    payload = data.model_dump(exclude_none=True)
    # Serialize payment_methods if present
    if "payment_methods" in payload:
        methods = payload["payment_methods"]
        payload["payment_methods"] = [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in methods]
        # Sync legacy payment_id with the default method
        default = next((m for m in payload["payment_methods"] if m.get("is_default")), None)
        if default:
            payload["payment_id"] = int(default["payment_id"])
        elif payload["payment_methods"]:
            payload["payment_id"] = int(payload["payment_methods"][0]["payment_id"])
    payload["restaurant_id"] = restaurant_id

    existing = await db.caffesta_config.find_one({"restaurant_id": restaurant_id})
    if existing:
        await db.caffesta_config.update_one({"restaurant_id": restaurant_id}, {"$set": payload})
    else:
        payload.setdefault("account_name", "")
        payload.setdefault("api_key", "")
        payload.setdefault("pos_id", None)
        payload.setdefault("payment_id", 1)
        payload.setdefault("payment_methods", [])
        payload.setdefault("enabled", False)
        await db.caffesta_config.insert_one(payload)

    config = await db.caffesta_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    return config


@router.post("/restaurants/{restaurant_id}/caffesta/test")
async def test_caffesta_connection(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("account_name") or not config.get("api_key"):
        raise HTTPException(status_code=400, detail="Укажите account_name и API-ключ")
    result = await caffesta_test_connection(config["account_name"], config["api_key"])
    return result


# ============ PRODUCTS (for mapping) ============

@router.get("/restaurants/{restaurant_id}/caffesta/products")
async def get_caffesta_products_list(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await caffesta_get_products(restaurant_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Ошибка"))
    return result["data"]


# ============ ORDERS → CAFFESTA ============

@router.post("/restaurants/{restaurant_id}/caffesta/send-order/{order_id}")
async def send_order_to_caffesta(restaurant_id: str, order_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    order = await db.orders.find_one({"id": order_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    result = await caffesta_send_order(restaurant_id, order)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Ошибка отправки"))
    return result


@router.get("/restaurants/{restaurant_id}/caffesta/order-status/{order_id}")
async def get_caffesta_order_status(restaurant_id: str, order_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    order = await db.orders.find_one({"id": order_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    caffesta_uuid = order.get("caffesta_uuid")
    if not caffesta_uuid:
        raise HTTPException(status_code=400, detail="Заказ не отправлен в Caffesta")
    result = await caffesta_get_order_status(restaurant_id, caffesta_uuid)
    return result


# ============ ANALYTICS ============

@router.get("/restaurants/{restaurant_id}/caffesta/analytics")
async def get_caffesta_analytics(restaurant_id: str, days: int = 30, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    # Get detailed sales (grouped by product)
    sales = await caffesta_get_sales(restaurant_id, start_date, end_date, "product_id")
    # Get totals
    totals = await caffesta_get_sales_totals(restaurant_id, start_date, end_date, "terminal_id")

    sales_data = sales.get("data", []) if sales.get("ok") else []
    totals_data = totals.get("data", []) if totals.get("ok") else []

    # Safe aggregation
    total_revenue = 0
    total_qty = 0
    total_cash = 0
    total_card = 0
    total_discount = 0
    for t in totals_data:
        try:
            total_revenue += float(t.get("total_pay", 0) or 0)
            total_qty += int(float(t.get("qnt", 0) or 0))
            total_cash += float(t.get("cash", 0) or 0)
            total_card += float(t.get("card", 0) or 0)
            total_discount += float(t.get("discount", 0) or 0)
        except (ValueError, TypeError):
            continue

    # Top products
    top_products = []
    for p in sorted(sales_data, key=lambda x: float(x.get("total_pay", 0) or 0), reverse=True)[:20]:
        try:
            top_products.append({
                "name": p.get("name", p.get("title", p.get("product_title", ""))),
                "qty": int(float(p.get("qnt", 0) or 0)),
                "revenue": round(float(p.get("total_pay", 0) or 0), 2),
                "price": str(p.get("price", "0")),
            })
        except (ValueError, TypeError):
            continue

    # Payment breakdown by type (from shift_day receipts)
    shift = await caffesta_get_sales_shift_day(restaurant_id, start_date, end_date)
    shift_data = shift.get("data", []) if shift.get("ok") else []
    payment_breakdown = {}
    seen_receipts = set()
    for r in shift_data:
        pt = (r.get("payment_type") or r.get("payment_title") or "Не указан").strip() or "Не указан"
        rcpt_key = r.get("receipt_number") or r.get("receipt_id") or r.get("id")
        # Aggregate total_pay per receipt once (shift_day returns product rows)
        key = (rcpt_key, pt)
        if rcpt_key and key in seen_receipts:
            continue
        if rcpt_key:
            seen_receipts.add(key)
        try:
            amount = float(r.get("receipt_total_pay", 0) or r.get("total_pay", 0) or 0)
        except (ValueError, TypeError):
            amount = 0
        if pt not in payment_breakdown:
            payment_breakdown[pt] = {"name": pt, "amount": 0.0, "count": 0}
        payment_breakdown[pt]["amount"] += amount
        payment_breakdown[pt]["count"] += 1
    payments = [
        {"name": p["name"], "amount": round(p["amount"], 2), "count": p["count"]}
        for p in sorted(payment_breakdown.values(), key=lambda x: x["amount"], reverse=True)
    ]

    return {
        "period": {"start": start_date, "end": end_date, "days": days},
        "totals": {
            "revenue": round(total_revenue, 2),
            "quantity": total_qty,
            "cash": round(total_cash, 2),
            "card": round(total_card, 2),
            "discount": round(total_discount, 2),
            "avg_check": round(total_revenue / max(total_qty, 1), 2),
        },
        "payments": payments,
        "top_products": top_products,
        "by_terminal": totals_data,
        "errors": [
            msg for ok, msg in [
                (sales.get("ok"), sales.get("message")),
                (totals.get("ok"), totals.get("message")),
            ] if not ok and msg
        ],
    }


@router.get("/restaurants/{restaurant_id}/caffesta/sales-report")
async def get_caffesta_sales_report(restaurant_id: str, days: int = 7, cashier: str = "", current_user: dict = Depends(get_current_user)):
    """Detailed sales report by shift day with waiter/cashier filter."""
    await check_restaurant_access(current_user, restaurant_id)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    result = await caffesta_get_sales_shift_day(restaurant_id, start_date, end_date)
    if not result.get("ok"):
        return {
            "period": {"start": start_date, "end": end_date, "days": days},
            "receipts": [],
            "by_cashier": [],
            "cashiers": [],
            "error": result.get("message", "Ошибка загрузки")
        }

    raw_data = result.get("data", [])

    # Extract unique cashiers
    cashiers = sorted(set(
        r.get("cashier_title", r.get("cashier_name", "")) for r in raw_data
        if r.get("cashier_title") or r.get("cashier_name")
    ))

    # Filter by cashier if specified
    if cashier:
        raw_data = [r for r in raw_data if (r.get("cashier_title", r.get("cashier_name", "")) == cashier)]

    # Aggregate by cashier
    by_cashier = {}
    for r in raw_data:
        c_name = r.get("cashier_title", r.get("cashier_name", "Неизвестно"))
        if c_name not in by_cashier:
            by_cashier[c_name] = {"cashier": c_name, "receipts": 0, "revenue": 0, "items": 0, "discount": 0}
        try:
            by_cashier[c_name]["revenue"] += float(r.get("total_pay", 0) or 0)
            by_cashier[c_name]["items"] += int(float(r.get("product_qty", r.get("qnt", 0)) or 0))
            by_cashier[c_name]["discount"] += float(r.get("discount_sum", r.get("discount", 0)) or 0)
        except (ValueError, TypeError):
            pass
        by_cashier[c_name]["receipts"] += 1

    # Round values
    for v in by_cashier.values():
        v["revenue"] = round(v["revenue"], 2)
        v["discount"] = round(v["discount"], 2)

    # Build receipt list (limited to 200)
    receipts = []
    for r in raw_data[:200]:
        try:
            receipts.append({
                "receipt_number": r.get("receipt_number", r.get("id", "")),
                "date": r.get("date", ""),
                "time": r.get("time", ""),
                "cashier": r.get("cashier_title", r.get("cashier_name", "")),
                "terminal": r.get("terminal_title", r.get("terminal_name", "")),
                "product": r.get("product_title", r.get("product_name", r.get("name", ""))),
                "qty": int(float(r.get("product_qty", r.get("qnt", 0)) or 0)),
                "price": round(float(r.get("product_price", r.get("price", 0)) or 0), 2),
                "sum": round(float(r.get("product_sum", r.get("total_pay", 0)) or 0), 2),
                "discount": round(float(r.get("discount_sum", r.get("discount", 0)) or 0), 2),
                "payment_type": r.get("payment_type", ""),
            })
        except (ValueError, TypeError):
            continue

    return {
        "period": {"start": start_date, "end": end_date, "days": days},
        "cashiers": cashiers,
        "by_cashier": sorted(by_cashier.values(), key=lambda x: x["revenue"], reverse=True),
        "receipts": receipts,
        "total_receipts": len(raw_data),
    }



# ============ TIME WINDOW ANALYTICS ============

def _parse_receipt_datetime(r: dict):
    """Try hard to get a datetime from a Caffesta shift_day row."""
    date_s = (r.get("date") or r.get("shift_date") or "").strip()
    time_s = (r.get("time") or r.get("receipt_time") or "").strip()
    # Sometimes datetime comes combined
    dt_s = (r.get("datetime") or r.get("receipt_datetime") or "").strip()
    if dt_s:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(dt_s[:19], fmt)
            except ValueError:
                continue
    if date_s and time_s:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(f"{date_s} {time_s}"[:19], fmt)
            except ValueError:
                continue
    return None


def _hhmm_to_minutes(s: str) -> int:
    h, m = s.split(":", 1)
    return int(h) * 60 + int(m)


@router.get("/restaurants/{restaurant_id}/caffesta/time-window")
async def caffesta_time_window(
    restaurant_id: str,
    days: int = 30,
    day_type: str = "all",          # all | weekday | weekend
    time_from: str = "00:00",       # HH:MM
    time_to: str = "23:59",         # HH:MM (if < from, treats as wrap-around past midnight)
    current_user: dict = Depends(get_current_user),
):
    """Sales within a specific day-of-week type and time-of-day window."""
    await check_restaurant_access(current_user, restaurant_id)

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    result = await caffesta_get_sales_shift_day(restaurant_id, start_date, end_date)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("message", "Ошибка Caffesta"))

    raw = result.get("data", [])
    try:
        from_min = _hhmm_to_minutes(time_from)
        to_min = _hhmm_to_minutes(time_to)
    except Exception:
        raise HTTPException(400, "Неверный формат времени (HH:MM)")

    def in_time_window(dt: datetime) -> bool:
        m = dt.hour * 60 + dt.minute
        if from_min <= to_min:
            return from_min <= m <= to_min
        # wrap-around e.g. 22:00 -> 02:00
        return m >= from_min or m <= to_min

    def in_day_type(dt: datetime) -> bool:
        wd = dt.weekday()  # 0=Mon..6=Sun
        if day_type == "weekday":
            return wd < 5
        if day_type == "weekend":
            return wd >= 5
        return True

    filtered_rows = []
    seen = set()
    total_items = 0
    total_discount = 0.0
    products = {}
    receipts = {}
    by_day = {}
    payment_breakdown = {}

    for r in raw:
        dt = _parse_receipt_datetime(r)
        if not dt:
            continue
        if not in_day_type(dt) or not in_time_window(dt):
            continue
        filtered_rows.append(r)

        rcpt_id = r.get("receipt_number") or r.get("id") or r.get("receipt_id")
        pt = (r.get("payment_type") or r.get("payment_title") or "Не указан").strip() or "Не указан"

        try:
            qty = int(float(r.get("product_qty", r.get("qnt", 0)) or 0))
            psum = float(r.get("product_sum", 0) or 0)
            disc = float(r.get("discount_sum", r.get("discount", 0)) or 0)
        except (ValueError, TypeError):
            qty, psum, disc = 0, 0, 0

        total_items += qty
        total_discount += disc

        pname = r.get("product_title") or r.get("product_name") or r.get("name") or "—"
        if pname not in products:
            products[pname] = {"name": pname, "qty": 0, "revenue": 0.0}
        products[pname]["qty"] += qty
        products[pname]["revenue"] += psum

        # Aggregate revenue per receipt (product rows summed; if receipt_total_pay is present we use the max seen)
        try:
            receipt_total = float(r.get("receipt_total_pay", 0) or 0)
        except (ValueError, TypeError):
            receipt_total = 0

        if rcpt_id and rcpt_id not in seen:
            seen.add(rcpt_id)
            receipts[rcpt_id] = {
                "id": rcpt_id,
                "datetime": dt.strftime("%Y-%m-%d %H:%M"),
                "cashier": r.get("cashier_title") or r.get("cashier_name") or "",
                "payment_type": pt,
                "revenue_from_items": 0.0,
                "receipt_total": receipt_total,
            }
            if pt not in payment_breakdown:
                payment_breakdown[pt] = {"name": pt, "count": 0}
            payment_breakdown[pt]["count"] += 1
            day_key = dt.strftime("%Y-%m-%d")
            by_day.setdefault(day_key, {"date": day_key, "weekday": dt.weekday(), "revenue": 0.0, "receipts": 0})
            by_day[day_key]["receipts"] += 1
        if rcpt_id:
            receipts[rcpt_id]["revenue_from_items"] += psum
            if receipt_total and receipts[rcpt_id]["receipt_total"] == 0:
                receipts[rcpt_id]["receipt_total"] = receipt_total

    # Finalize revenue: prefer receipt_total, fallback to summed items
    total_revenue = 0.0
    for rc in receipts.values():
        rev = rc["receipt_total"] or rc["revenue_from_items"]
        rc["revenue"] = round(rev, 2)
        total_revenue += rev
        pt = rc["payment_type"]
        payment_breakdown[pt].setdefault("amount", 0.0)
        payment_breakdown[pt]["amount"] += rev
        day_key = rc["datetime"][:10]
        if day_key in by_day:
            by_day[day_key]["revenue"] += rev

    top_products = sorted(products.values(), key=lambda x: x["revenue"], reverse=True)[:20]
    for p in top_products:
        p["revenue"] = round(p["revenue"], 2)
    payments_list = [
        {"name": p["name"], "amount": round(p.get("amount", 0), 2), "count": p["count"]}
        for p in sorted(payment_breakdown.values(), key=lambda x: x.get("amount", 0), reverse=True)
    ]
    by_day_list = sorted(
        [{**v, "revenue": round(v["revenue"], 2)} for v in by_day.values()],
        key=lambda x: x["date"],
    )

    return {
        "filter": {
            "days": days,
            "day_type": day_type,
            "time_from": time_from,
            "time_to": time_to,
            "start": start_date,
            "end": end_date,
        },
        "totals": {
            "revenue": round(total_revenue, 2),
            "receipts": len(receipts),
            "items": total_items,
            "discount": round(total_discount, 2),
            "avg_check": round(total_revenue / max(len(receipts), 1), 2),
        },
        "payments": payments_list,
        "top_products": top_products,
        "by_day": by_day_list,
    }
