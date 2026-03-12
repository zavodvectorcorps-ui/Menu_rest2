from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone

from database import db
from auth import get_current_user, check_restaurant_access
from services.caffesta import (
    caffesta_test_connection, caffesta_get_sales, caffesta_get_sales_totals,
    caffesta_get_products, caffesta_send_order, caffesta_get_order_status,
    get_caffesta_config, is_caffesta_enabled,
)

router = APIRouter()


class CaffestaConfigUpdate(BaseModel):
    account_name: Optional[str] = None
    api_key: Optional[str] = None
    pos_id: Optional[int] = None
    payment_id: Optional[int] = None
    enabled: Optional[bool] = None


# ============ CONFIG ============

@router.get("/restaurants/{restaurant_id}/caffesta")
async def get_caffesta_settings(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    config = await get_caffesta_config(restaurant_id)
    if not config:
        return {"restaurant_id": restaurant_id, "account_name": "", "api_key": "", "pos_id": None, "payment_id": 1, "enabled": False, "connected": False}
    config.pop("_id", None)
    return config


@router.put("/restaurants/{restaurant_id}/caffesta")
async def update_caffesta_settings(restaurant_id: str, data: CaffestaConfigUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["restaurant_id"] = restaurant_id

    existing = await db.caffesta_config.find_one({"restaurant_id": restaurant_id})
    if existing:
        await db.caffesta_config.update_one({"restaurant_id": restaurant_id}, {"$set": update_data})
    else:
        update_data.setdefault("account_name", "")
        update_data.setdefault("api_key", "")
        update_data.setdefault("pos_id", None)
        update_data.setdefault("payment_id", 1)
        update_data.setdefault("enabled", False)
        await db.caffesta_config.insert_one(update_data)

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

    # Aggregate
    total_revenue = sum(float(t.get("total_pay", 0) or 0) for t in totals_data)
    total_qty = sum(int(t.get("qnt", 0) or 0) for t in totals_data)
    total_cash = sum(float(t.get("cash", 0) or 0) for t in totals_data)
    total_card = sum(float(t.get("card", 0) or 0) for t in totals_data)
    total_discount = sum(float(t.get("discount", 0) or 0) for t in totals_data)

    # Top products
    top_products = sorted(sales_data, key=lambda x: float(x.get("total_pay", 0) or 0), reverse=True)[:20]

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
        "top_products": [
            {
                "name": p.get("name", ""),
                "qty": int(p.get("qnt", 0) or 0),
                "revenue": round(float(p.get("total_pay", 0) or 0), 2),
                "price": p.get("price", "0"),
            }
            for p in top_products
        ],
        "by_terminal": totals_data,
    }
