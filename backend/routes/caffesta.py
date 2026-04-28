from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta, timezone

from database import db
from auth import get_current_user, check_restaurant_access
from services.caffesta import (
    caffesta_test_connection, caffesta_get_sales, caffesta_get_sales_totals,
    caffesta_get_products, caffesta_send_order, caffesta_get_order_status,
    caffesta_get_sales_shift_day, get_caffesta_config, is_caffesta_enabled,
    caffesta_get_all_receipts, split_receipt_payments,
    caffesta_get_product_shop_data,
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

    # Payment breakdown by type — from real receipts (v1.1/draft/receipts_by_shift_day)
    receipts_res = await caffesta_get_all_receipts(restaurant_id, start_date, end_date)
    receipts = receipts_res.get("data", []) if receipts_res.get("ok") else []
    payment_methods = (await get_caffesta_config(restaurant_id) or {}).get("payment_methods", [])

    payment_breakdown = {}
    for r in receipts:
        for p in split_receipt_payments(r, payment_methods):
            key = p["name"]
            if key not in payment_breakdown:
                payment_breakdown[key] = {"name": key, "amount": 0.0, "count": 0}
            payment_breakdown[key]["amount"] += p["amount"]
            payment_breakdown[key]["count"] += 1
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
    day_type: str = "all",          # all | weekday | weekend | mon_thu | fri | sat | sun
    time_from: str = "00:00",       # HH:MM
    time_to: str = "23:59",         # HH:MM (if < from, treats as wrap-around past midnight)
    current_user: dict = Depends(get_current_user),
):
    """Sales within a specific day-of-week type and time-of-day window.
    Uses v1.1/draft/receipts_by_shift_day which provides real per-receipt timestamps."""
    await check_restaurant_access(current_user, restaurant_id)

    if days < 1 or days > 120:
        raise HTTPException(400, "Период должен быть от 1 до 120 дней")

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        from_min = _hhmm_to_minutes(time_from)
        to_min = _hhmm_to_minutes(time_to)
    except Exception:
        raise HTTPException(400, "Неверный формат времени (HH:MM)")

    def in_time_window(dt: datetime) -> bool:
        m = dt.hour * 60 + dt.minute
        if from_min <= to_min:
            return from_min <= m <= to_min
        return m >= from_min or m <= to_min

    def in_day_type(dt: datetime) -> bool:
        wd = dt.weekday()  # 0=Mon..6=Sun
        if day_type == "weekday":
            return wd < 5
        if day_type == "weekend":
            return wd >= 5
        if day_type == "mon_thu":
            return wd <= 3
        if day_type == "fri":
            return wd == 4
        if day_type == "sat":
            return wd == 5
        if day_type == "sun":
            return wd == 6
        return True

    res = await caffesta_get_all_receipts(restaurant_id, start_date, end_date)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("message", "Ошибка Caffesta"))
    receipts = res.get("data", [])

    config = await get_caffesta_config(restaurant_id) or {}
    payment_methods = config.get("payment_methods", [])

    # Build product_id -> title map from Caffesta products catalog
    product_map = {}
    try:
        from services.caffesta import caffesta_get_products
        prods = await caffesta_get_products(restaurant_id)
        if prods.get("ok"):
            for p in prods.get("data", []):
                try:
                    product_map[int(p["product_id"])] = p.get("title") or ""
                except (ValueError, TypeError, KeyError):
                    continue
    except Exception:
        pass

    total_revenue = 0.0
    total_discount = 0.0
    total_receipts = 0
    products = {}
    by_day = {}
    payment_breakdown = {}
    samples = []

    for r in receipts:
        dt = r.get("created_dt")
        if not dt:
            # Skip receipts without a reliable timestamp — avoid false-positives on 00:00
            continue
        if not in_day_type(dt) or not in_time_window(dt):
            continue

        rev = float(r.get("total_sum", 0) or 0)
        disc = float(r.get("discount_sum", 0) or 0)
        total_revenue += rev
        total_discount += disc
        total_receipts += 1

        # Payment breakdown
        for p in split_receipt_payments(r, payment_methods):
            key = p["name"]
            payment_breakdown.setdefault(key, {"name": key, "amount": 0.0, "count": 0})
            payment_breakdown[key]["amount"] += p["amount"]
            payment_breakdown[key]["count"] += 1

        # Day breakdown
        day_key = dt.strftime("%Y-%m-%d")
        by_day.setdefault(day_key, {"date": day_key, "weekday": dt.weekday(), "revenue": 0.0, "receipts": 0})
        by_day[day_key]["receipts"] += 1
        by_day[day_key]["revenue"] += rev

        # Top products from order_dishes
        for od in (r.get("order_dishes") or []):
            dish = od.get("dish") or {}
            pname = (
                dish.get("title") or dish.get("name") or dish.get("product_title")
            )
            if not pname:
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
                qty = float(od.get("count") or od.get("qty") or od.get("qnt") or 1)
            except (ValueError, TypeError):
                qty = 1
            try:
                psum = float(od.get("total_sum") or od.get("sum") or od.get("total") or (od.get("price", 0) or 0) * qty)
            except (ValueError, TypeError):
                psum = 0
            products.setdefault(pname, {"name": pname, "qty": 0, "revenue": 0.0})
            products[pname]["qty"] += int(qty)
            products[pname]["revenue"] += psum

        if len(samples) < 20:
            samples.append({
                "id": str(r.get("id", ""))[:12],
                "datetime": dt.strftime("%Y-%m-%d %H:%M"),
                "weekday": ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][dt.weekday()],
                "total": round(rev, 2),
                "terminal_id": r.get("terminal_id"),
            })

    top_products = sorted(products.values(), key=lambda x: x["revenue"], reverse=True)[:20]
    for p in top_products:
        p["revenue"] = round(p["revenue"], 2)
    payments_list = [
        {"name": p["name"], "amount": round(p["amount"], 2), "count": p["count"]}
        for p in sorted(payment_breakdown.values(), key=lambda x: x["amount"], reverse=True)
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
            "receipts": total_receipts,
            "items": sum(p["qty"] for p in products.values()),
            "discount": round(total_discount, 2),
            "avg_check": round(total_revenue / max(total_receipts, 1), 2),
        },
        "payments": payments_list,
        "top_products": top_products,
        "by_day": by_day_list,
        "samples": samples,
    }


# ============ STOP LIST SYNC ============

@router.get("/restaurants/{restaurant_id}/caffesta/debug/raw-receipts")
async def debug_raw_receipts(
    restaurant_id: str,
    date: Optional[str] = None,
    full: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Return raw receipts with order_dishes from Caffesta for inspection.
    full=true → returns ALL receipts of the day (compact view); otherwise first 3 in detail."""
    from services.caffesta import (
        get_caffesta_config as _g,
        caffesta_get_terminals as _t,
        caffesta_get_receipts_for_day as _fd,
    )
    await check_restaurant_access(current_user, restaurant_id)
    cfg = await _g(restaurant_id)
    if not cfg or not cfg.get("enabled"):
        raise HTTPException(400, "Caffesta не настроена")
    if not date:
        date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    terminals = await _t(restaurant_id, date, date)
    if not terminals and cfg.get("pos_id"):
        terminals = [int(cfg["pos_id"])]

    if full:
        all_receipts = []
        for tid in terminals:
            raw = await _fd(cfg["account_name"], cfg["api_key"], tid, date)
            for r in raw:
                all_receipts.append({
                    "tid": tid,
                    "id": (r.get("id") or "")[:13],
                    "created": r.get("created_at"),
                    "updated": r.get("updated_at"),
                    "type": r.get("type"),
                    "income": r.get("income"),
                    "total": r.get("total_sum"),
                    "discount": r.get("discount_sum"),
                    "terminal_number": r.get("terminal_number"),
                })
        # Sort by created_at
        all_receipts.sort(key=lambda x: x.get("created") or "")
        return {"date": date, "terminals": terminals, "count": len(all_receipts), "receipts": all_receipts}

    samples = []
    for tid in terminals[:3]:
        raw = await _fd(cfg["account_name"], cfg["api_key"], tid, date)
        for r in raw[:3]:
            samples.append({"terminal_id": tid, "receipt": r})
            if len(samples) >= 3:
                break
        if len(samples) >= 3:
            break
    return {"date": date, "terminals": terminals, "samples": samples}


@router.post("/restaurants/{restaurant_id}/caffesta/stop-list/sync")
async def sync_stop_list(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch stop-list status from Caffesta (get_product_shop_data) and update menu items' availability."""
    await check_restaurant_access(current_user, restaurant_id)
    res = await caffesta_get_product_shop_data(restaurant_id)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("message", "Ошибка Caffesta"))
    data = res.get("data", [])
    stop_ids = {row["product_id"]: row for row in data if row.get("inStopList")}
    in_stock_ids = {row["product_id"]: row for row in data if not row.get("inStopList")}

    # Only affect items that have caffesta_product_id set
    items = await db.menu_items.find(
        {"restaurant_id": restaurant_id, "caffesta_product_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "caffesta_product_id": 1, "is_available": 1, "name": 1},
    ).to_list(10000)

    disabled = []
    enabled = []
    for item in items:
        cfid = item.get("caffesta_product_id")
        if not cfid:
            continue
        if cfid in stop_ids and item.get("is_available", True) is not False:
            await db.menu_items.update_one(
                {"id": item["id"]}, {"$set": {"is_available": False, "stop_list_source": "caffesta"}}
            )
            disabled.append(item["name"])
        elif cfid in in_stock_ids and item.get("is_available", True) is False:
            # Re-enable only if it was disabled by caffesta sync
            # (don't re-enable items manually disabled by user)
            existing = await db.menu_items.find_one({"id": item["id"]}, {"_id": 0, "stop_list_source": 1})
            if existing and existing.get("stop_list_source") == "caffesta":
                await db.menu_items.update_one(
                    {"id": item["id"]}, {"$set": {"is_available": True, "stop_list_source": None}}
                )
                enabled.append(item["name"])

    return {
        "ok": True,
        "total_in_caffesta": len(data),
        "in_stop_list": len(stop_ids),
        "disabled_count": len(disabled),
        "enabled_count": len(enabled),
        "disabled": disabled[:30],
        "enabled": enabled[:30],
        "linked_items": len(items),
    }
