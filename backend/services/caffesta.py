import logging
import httpx
from database import db

logger = logging.getLogger(__name__)


async def get_caffesta_config(restaurant_id: str) -> dict:
    """Get Caffesta config for restaurant. Returns None if not configured."""
    config = await db.caffesta_config.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    return config


async def is_caffesta_enabled(restaurant_id: str) -> bool:
    config = await get_caffesta_config(restaurant_id)
    if not config:
        return False
    return bool(config.get("enabled") and config.get("account_name") and config.get("api_key"))


def _base_url(account_name: str) -> str:
    return f"https://{account_name}.caffesta.com/a"


def _headers(api_key: str) -> dict:
    return {"X-API-KEY": api_key, "Content-Type": "application/json"}


def _safe_json(resp) -> dict:
    """Safely parse JSON response from Caffesta. Returns error dict if not JSON."""
    if not resp.text or not resp.text.strip():
        logger.warning(f"Caffesta empty response: status={resp.status_code} url={resp.url}")
        return {"success": False, "data": {"error": f"Пустой ответ от Caffesta (HTTP {resp.status_code})"}}
    try:
        return _safe_json(resp)
    except Exception:
        logger.warning(f"Caffesta non-JSON response: status={resp.status_code} body={resp.text[:200]}")
        return {"success": False, "data": {"error": f"Некорректный ответ от Caffesta (HTTP {resp.status_code})"}}


async def caffesta_test_connection(account_name: str, api_key: str) -> dict:
    """Test connection to Caffesta API."""
    try:
        url = f"{_base_url(account_name)}/v1.0/storage/test"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if data.get("success"):
                return {"ok": True, "message": "Подключение успешно"}
            return {"ok": False, "message": data.get("error", "Неизвестная ошибка")}
    except httpx.TimeoutException:
        return {"ok": False, "message": "Таймаут подключения к Caffesta"}
    except Exception as e:
        logger.error(f"Caffesta connection test failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_send_order(restaurant_id: str, order: dict) -> dict:
    """Send order to Caffesta POS as a delivery order."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]
    pos_id = config.get("pos_id")
    payment_id = config.get("payment_id", 1)

    if not pos_id:
        return {"ok": False, "message": "Не указан POS ID"}

    # Build Caffesta order payload
    items = []
    for item in order.get("items", []):
        caf_product_id = item.get("caffesta_product_id")
        if not caf_product_id:
            continue
        price = float(item.get("price", 0))
        count = int(item.get("quantity", 1))
        items.append({
            "title": item.get("name", ""),
            "count": count,
            "price": price,
            "discount_sum": 0,
            "origin_price": price,
            "total_sum": price * count,
            "product_id": caf_product_id,
        })

    if not items:
        return {"ok": False, "message": "Нет товаров с привязкой к Caffesta"}

    total_sum = sum(i["total_sum"] for i in items)

    # Build client info for preorders
    client_data = None
    if order.get("is_preorder") and order.get("customer_name"):
        client_data = {
            "name": order.get("customer_name", ""),
            "phone": order.get("customer_phone", ""),
        }

    bill = {
        "pos_id": int(pos_id),
        "app_id": int(pos_id),
        "delivery_type": 2,
        "discount_sum": 0,
        "total_sum": total_sum,
        "payments": [{"payment_id": int(payment_id), "value": total_sum}],
        "items": items,
        "comment": f"Стол #{order.get('table_number', '?')}. {order.get('notes', '')}".strip(),
    }
    if client_data:
        bill["client"] = client_data

    try:
        url = f"{_base_url(account_name)}/v1.1/draft/receipts"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=_headers(api_key), json={"bill": bill})
            data = _safe_json(resp)
            if data.get("success"):
                caffesta_uuid = data.get("data", {}).get("message", "")
                # Save caffesta UUID to our order
                await db.orders.update_one(
                    {"id": order.get("id")},
                    {"$set": {"caffesta_uuid": caffesta_uuid, "caffesta_status": data.get("data", {}).get("status", "")}}
                )
                logger.info(f"Order {order.get('id')} sent to Caffesta: {caffesta_uuid}")
                return {"ok": True, "caffesta_uuid": caffesta_uuid, "status": data.get("data", {}).get("status", "")}
            else:
                error_msg = data.get("message", data.get("data", {}).get("error", "Неизвестная ошибка"))
                logger.warning(f"Caffesta order error: {error_msg}")
                return {"ok": False, "message": error_msg}
    except Exception as e:
        logger.error(f"Caffesta send order failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_get_order_status(restaurant_id: str, caffesta_uuid: str) -> dict:
    """Get order status from Caffesta."""
    config = await get_caffesta_config(restaurant_id)
    if not config:
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]

    try:
        url = f"{_base_url(account_name)}/v1.0/draft/receipts/{caffesta_uuid}/info"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if isinstance(data, list) and len(data) > 0:
                return {"ok": True, "status": data[0].get("status", "unknown"), "data": data[0]}
            if isinstance(data, dict) and data.get("success") is False:
                return {"ok": False, "message": data.get("data", {}).get("error", "Ошибка Caffesta")}
            return {"ok": False, "message": "Заказ не найден в Caffesta"}
    except Exception as e:
        logger.error(f"Caffesta order status failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_get_sales(restaurant_id: str, start_date: str, end_date: str, group_by: str = "") -> dict:
    """Get sales data from Caffesta for analytics."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]

    try:
        url = f"{_base_url(account_name)}/v1.0/product/export_sales?start={start_date}&end={end_date}"
        if group_by:
            url += f"&add_gr_by={group_by}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if data.get("success"):
                return {"ok": True, "data": data.get("data", [])}
            err = data.get("data", {})
            msg = err.get("error", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "message": msg}
    except Exception as e:
        logger.error(f"Caffesta sales export failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_get_sales_totals(restaurant_id: str, start_date: str, end_date: str, group_by: str = "terminal_id") -> dict:
    """Get aggregated sales totals from Caffesta."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]

    try:
        url = f"{_base_url(account_name)}/v1.0/product/export_sales_totals?start={start_date}&end={end_date}&add_gr_by={group_by}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if data.get("success"):
                return {"ok": True, "data": data.get("data", [])}
            err = data.get("data", {})
            msg = err.get("error", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "message": msg}
    except Exception as e:
        logger.error(f"Caffesta sales totals failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_get_sales_shift_day(restaurant_id: str, start_date: str, end_date: str) -> dict:
    """Get detailed sales by shift day (includes waiter/cashier info)."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]

    try:
        url = f"{_base_url(account_name)}/v1.0/product/export_sales_shift_day?start={start_date}&end={end_date}"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if data.get("success"):
                return {"ok": True, "data": data.get("data", [])}
            err = data.get("data", {})
            msg = err.get("error", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "message": msg}
    except Exception as e:
        logger.error(f"Caffesta sales shift day failed: {e}")
        return {"ok": False, "message": str(e)}


async def caffesta_get_products(restaurant_id: str) -> dict:
    """Get products from Caffesta for mapping. Normalizes response to have consistent title/product_id fields."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]
    pos_id = config.get("pos_id", 1)

    try:
        url = f"{_base_url(account_name)}/v1.0/draft/get_products/{pos_id}/0/0"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            logger.info(f"Caffesta products response code: {data.get('code', 'unknown')}")
            raw_products = []
            if data.get("code") == "ok":
                raw_products = data.get("data", [])
            elif data.get("success"):
                raw_products = data.get("data", [])
            else:
                logger.warning(f"Caffesta products unexpected response: {str(data)[:300]}")
                return {"ok": False, "message": "Ошибка получения товаров"}

            # Normalize product fields — try title, name, product_name
            products = []
            for p in raw_products:
                title = p.get("title") or p.get("name") or p.get("product_name") or p.get("product_title") or ""
                pid = p.get("product_id") or p.get("id") or 0
                products.append({
                    "product_id": pid,
                    "title": title,
                    "price": p.get("price", p.get("prices", [{}])[0].get("price", 0) if isinstance(p.get("prices"), list) and p.get("prices") else 0),
                    "description": p.get("description", ""),
                })
            return {"ok": True, "data": products}
    except Exception as e:
        logger.error(f"Caffesta get products failed: {e}")
        return {"ok": False, "message": str(e)}
