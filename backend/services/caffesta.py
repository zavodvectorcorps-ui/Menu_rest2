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
        return resp.json()
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
    """Get products + tech cards from Caffesta for mapping. Handles pagination."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]
    pos_id = config.get("pos_id", 1)

    all_raw = []
    start_id = 0
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Paginate: fetch until no more data
            for _ in range(20):  # safety limit
                url = f"{_base_url(account_name)}/v1.0/draft/get_products/{pos_id}/{start_id}/0"
                resp = await client.get(url, headers=_headers(api_key))
                data = _safe_json(resp)

                raw_list = []
                if data.get("code") == "ok":
                    raw_list = data.get("data", [])
                elif data.get("success"):
                    raw_list = data.get("data", [])
                elif isinstance(data, list):
                    raw_list = data
                else:
                    if not all_raw:
                        logger.warning(f"Caffesta products response: {str(data)[:300]}")
                    break

                if not raw_list:
                    break

                all_raw.extend(raw_list)
                # Check for pagination - use last product_id as next start_id
                last_id = raw_list[-1].get("product_id") or raw_list[-1].get("id") or 0
                if last_id and last_id != start_id and len(raw_list) >= 100:
                    start_id = last_id
                else:
                    break

        logger.info(f"Caffesta: loaded {len(all_raw)} products/tech_cards for pos {pos_id}")

        # Normalize product fields
        products = []
        for p in all_raw:
            title = p.get("title") or p.get("name") or p.get("product_name") or p.get("product_title") or ""
            pid = p.get("product_id") or p.get("id") or 0
            entity_type = p.get("entityType") or p.get("entity_type") or p.get("type") or "product"
            price_val = 0
            if isinstance(p.get("prices"), list) and p["prices"]:
                price_val = p["prices"][0].get("price", 0) if isinstance(p["prices"][0], dict) else 0
            elif p.get("price"):
                price_val = p["price"]

            products.append({
                "product_id": pid,
                "title": title,
                "type": entity_type,
                "price": price_val,
                "description": p.get("description", ""),
            })
        return {"ok": True, "data": products}
    except Exception as e:
        logger.error(f"Caffesta get products failed: {e}")
        return {"ok": False, "message": str(e)}



# ============ v1.1/draft receipts (real per-receipt data with timestamps) ============

async def caffesta_get_terminals(restaurant_id: str, start_date: str, end_date: str) -> list:
    """Discover terminal IDs used in a date range via export_sales_totals."""
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return []
    account_name = config["account_name"]
    api_key = config["api_key"]
    try:
        url = f"{_base_url(account_name)}/v1.0/product/export_sales_totals?start={start_date}&end={end_date}&add_gr_by=terminal_id"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if data.get("success"):
                rows = data.get("data", []) or []
                ids = set()
                for r in rows:
                    tid = r.get("caf_terminal_id") or r.get("terminal_id")
                    if tid:
                        try:
                            ids.add(int(tid))
                        except (ValueError, TypeError):
                            pass
                return sorted(ids)
    except Exception as e:
        logger.warning(f"Caffesta terminals discovery failed: {e}")
    return []


async def caffesta_get_receipts_for_day(account_name: str, api_key: str, terminal_id: int, date: str) -> list:
    """Fetch raw receipts for one terminal + one date."""
    url = f"{_base_url(account_name)}/v1.1/draft/receipts_by_shift_day/{terminal_id}/{date}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and data.get("success") and isinstance(data.get("data"), list):
                return data["data"]
    except Exception as e:
        logger.warning(f"Caffesta receipts fetch failed for {terminal_id}/{date}: {e}")
    return []


async def caffesta_get_all_receipts(restaurant_id: str, start_date: str, end_date: str) -> dict:
    """
    Fetch all per-receipt data across terminals for [start_date, end_date].
    Returns {ok, data: [normalized_receipt, ...]}.
    Each receipt has: id, terminal_id, total_sum, discount_sum, cash_pay, card_pay,
    cashless_pay, cashlessPayment_id, created_at, created_dt (datetime), order_dishes.
    """
    from datetime import datetime as _dt, timedelta as _td
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}

    account_name = config["account_name"]
    api_key = config["api_key"]

    terminals = await caffesta_get_terminals(restaurant_id, start_date, end_date)
    if not terminals and config.get("pos_id"):
        terminals = [int(config["pos_id"])]
    if not terminals:
        return {"ok": False, "message": "Не удалось определить терминалы Caffesta"}

    # Build list of dates
    try:
        d_from = _dt.strptime(start_date, "%Y-%m-%d").date()
        d_to = _dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return {"ok": False, "message": "Неверный формат даты"}
    if (d_to - d_from).days > 120:
        return {"ok": False, "message": "Период слишком большой (макс 120 дней)"}
    dates = []
    cur = d_from
    while cur <= d_to:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += _td(days=1)

    # Parallel fetch (bounded)
    import asyncio
    sem = asyncio.Semaphore(8)

    async def _fetch(tid, dt):
        async with sem:
            rows = await caffesta_get_receipts_for_day(account_name, api_key, tid, dt)
            for r in rows:
                r["_terminal_id"] = tid
                r["_date"] = dt
            return rows

    tasks = [_fetch(tid, dt) for tid in terminals for dt in dates]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    flat = []
    for res in results:
        if isinstance(res, list):
            flat.extend(res)

    # Normalize
    from zoneinfo import ZoneInfo
    MINSK_TZ = ZoneInfo("Europe/Minsk")
    UTC_TZ = ZoneInfo("UTC")

    def _parse_caffesta_dt(s):
        """Parse Caffesta datetime. Caffesta returns naive timestamps in UTC.
        Returns naive datetime in Minsk local time, or None."""
        if not s:
            return None
        cleaned = s.strip().replace("Z", "+00:00")
        try:
            dt = _dt.fromisoformat(cleaned)
        except (ValueError, TypeError):
            dt = None
        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M",
                        "%Y-%m-%d"):
                try:
                    dt = _dt.strptime(s.strip()[:len("2025-01-01 00:00:00")], fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
        # Caffesta returns NAIVE timestamps in UTC (verified by user comparing UI vs API).
        # Naive → assume UTC; tz-aware → keep as is. Then convert to Minsk local.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt.astimezone(MINSK_TZ).replace(tzinfo=None)

    normalized = []
    skipped_no_time = 0
    for r in flat:
        # Prefer created_at, fall back to updated_at (for open/draft receipts)
        dt_obj = _parse_caffesta_dt(r.get("created_at"))
        if not dt_obj:
            dt_obj = _parse_caffesta_dt(r.get("updated_at"))

        # Whether we have an actual time-of-day (not just a date)
        has_time = dt_obj is not None and (dt_obj.hour > 0 or dt_obj.minute > 0 or dt_obj.second > 0 or
                                            (r.get("created_at") and "T" in r["created_at"] or
                                             r.get("created_at") and ":" in r.get("created_at", "")))
        if not has_time:
            # If only date came (00:00:00 from a pure date string), treat as no-time
            ca = (r.get("created_at") or "").strip()
            if ca and ":" not in ca:
                dt_obj = None
                skipped_no_time += 1

        # Permissive income filter: exclude only explicit cancellations
        income_raw = r.get("income")
        is_cancel = (income_raw == 0) or (str(r.get("type", "")).lower() in ("cancel", "void", "return"))

        normalized.append({
            "id": r.get("id") or r.get("uuid") or "",
            "terminal_id": r.get("_terminal_id") or r.get("terminal_number"),
            "type": r.get("type", ""),
            "income": income_raw if income_raw is not None else 1,
            "is_cancel": is_cancel,
            "total_sum": float(r.get("total_sum", 0) or 0),
            "discount_sum": float(r.get("discount_sum", 0) or 0),
            "cash_pay": float(r.get("cash_pay", 0) or 0),
            "card_pay": float(r.get("card_pay", 0) or 0),
            "cashless_pay": float(r.get("cashless_pay", 0) or 0),
            "cashlessPayment_id": r.get("cashlessPayment_id"),
            "back_pay": float(r.get("back_pay", 0) or 0),
            "created_at": r.get("created_at") or r.get("updated_at") or "",
            "created_dt": dt_obj,
            "updated_dt": _parse_caffesta_dt(r.get("updated_at")),
            "order_dishes": r.get("order_dishes", []) or [],
            "count_clients": r.get("count_clients", 0),
        })
    # Exclude only explicit cancellations/voids; keep open receipts (income=null/0 means draft).
    filtered = [n for n in normalized if not n.get("is_cancel")]
    logger.info(
        f"Caffesta receipts: total={len(flat)}, kept={len(filtered)}, "
        f"skipped_no_time={skipped_no_time}, cancelled={len(normalized) - len(filtered)}"
    )
    return {"ok": True, "data": filtered, "diagnostics": {
        "fetched": len(flat),
        "kept": len(filtered),
        "skipped_no_time": skipped_no_time,
        "cancelled": len(normalized) - len(filtered),
    }}


def split_receipt_payments(receipt: dict, payment_methods: list) -> list:
    """
    Split a single receipt into per-payment-type entries using cash_pay/card_pay/cashless_pay
    and payment_methods mapping (list of {name, payment_id}).
    Returns list of {name, amount}.
    """
    result = []
    if receipt.get("cash_pay", 0) > 0:
        # Find a payment method whose name hints "cash" or id=1; else default label
        name = None
        for m in payment_methods or []:
            if int(m.get("payment_id", 0)) == 1:
                name = m.get("name")
                break
        result.append({"name": name or "Наличные", "amount": float(receipt["cash_pay"])})
    if receipt.get("card_pay", 0) > 0:
        name = None
        for m in payment_methods or []:
            if int(m.get("payment_id", 0)) == 2:
                name = m.get("name")
                break
        result.append({"name": name or "Карта", "amount": float(receipt["card_pay"])})
    if receipt.get("cashless_pay", 0) > 0:
        cpid = receipt.get("cashlessPayment_id")
        name = None
        for m in payment_methods or []:
            try:
                if cpid is not None and int(m.get("payment_id", 0)) == int(cpid):
                    name = m.get("name")
                    break
            except (ValueError, TypeError):
                continue
        label = name or (f"Безнал (ID {cpid})" if cpid else "Безналичные")
        result.append({"name": label, "amount": float(receipt["cashless_pay"])})
    return result


# ============ Balances (self_cost) ============

async def caffesta_get_balances(restaurant_id: str) -> dict:
    """Get product balances including self_cost from /v1.0/draft/get_balances/{pos_id}/0.
    Returns {ok, data: [{product_id, self_cost, balance}, ...]}.
    """
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}
    account_name = config["account_name"]
    api_key = config["api_key"]
    pos_id = config.get("pos_id", 1)

    url = f"{_base_url(account_name)}/v1.0/draft/get_balances/{pos_id}/0"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and (data.get("success") or data.get("code") == "ok"):
                rows = data.get("data", []) or []
            else:
                err = data.get("data", {}) if isinstance(data, dict) else {}
                msg = err.get("error", str(err)) if isinstance(err, dict) else str(err)
                return {"ok": False, "message": msg or "Не удалось получить балансы"}

        result = []
        for row in rows:
            try:
                pid = int(row.get("product_id") or row.get("id") or 0)
            except (ValueError, TypeError):
                continue
            if not pid:
                continue
            try:
                sc = float(row.get("self_cost") or 0)
            except (ValueError, TypeError):
                sc = 0
            try:
                bal = float(row.get("balance") or 0)
            except (ValueError, TypeError):
                bal = 0
            result.append({"product_id": pid, "self_cost": sc, "balance": bal})
        return {"ok": True, "data": result}
    except Exception as e:
        logger.error(f"Caffesta balances failed: {e}")
        return {"ok": False, "message": str(e)}


# ============ Shop data (stop-list, avgInvoicedSelfCost) ============

async def caffesta_get_product_shop_data(restaurant_id: str) -> dict:
    """Get per-shop product availability + stop-list status.
    Returns {ok, data: [{product_id, inStopList, availableForSale, price, avgInvoicedSelfCost}, ...]}.
    """
    config = await get_caffesta_config(restaurant_id)
    if not config or not config.get("enabled"):
        return {"ok": False, "message": "Caffesta не настроена"}
    account_name = config["account_name"]
    api_key = config["api_key"]
    pos_id = config.get("pos_id", 1)

    url = f"{_base_url(account_name)}/v1.0/draft/get_product_shop_data/{pos_id}/0"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_headers(api_key))
            data = _safe_json(resp)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and (data.get("success") or data.get("code") == "ok"):
                rows = data.get("data", []) or []
            else:
                err = data.get("data", {}) if isinstance(data, dict) else {}
                msg = err.get("error", str(err)) if isinstance(err, dict) else str(err)
                return {"ok": False, "message": msg or "Не удалось получить данные точки"}

        result = []
        for row in rows:
            try:
                pid = int(row.get("product_id") or 0)
            except (ValueError, TypeError):
                continue
            if not pid:
                continue
            try:
                asc = float(row.get("avgInvoicedSelfCost") or 0)
            except (ValueError, TypeError):
                asc = 0
            result.append({
                "product_id": pid,
                "inStopList": bool(row.get("inStopList", False)),
                "availableForSale": bool(row.get("availableForSale", True)),
                "price": row.get("price"),
                "avgInvoicedSelfCost": asc,
            })
        return {"ok": True, "data": result}
    except Exception as e:
        logger.error(f"Caffesta shop data failed: {e}")
        return {"ok": False, "message": str(e)}


