from fastapi import APIRouter, HTTPException, Request
import html as html_module

from database import db
from models import (
    OrderCreate, Order, StaffCall, StaffCallCreate, MenuView
)
from helpers import serialize_doc, get_or_create_settings, get_or_create_menu_sections, get_or_create_call_types
from services.telegram import notify_restaurant_telegram, build_order_keyboard, build_call_keyboard
from services.caffesta import is_caffesta_enabled, caffesta_send_order
from services.websocket import manager

router = APIRouter()


def _normalize_host(host: str) -> str:
    """Strip port + lowercase. Accepts 'Catch.com:443' → 'catch.com'."""
    if not host:
        return ""
    return host.split(':', 1)[0].strip().lower()


@router.get("/public/menu/{table_code}")
async def get_public_menu(table_code: str):
    table = await db.tables.find_one({"code": table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")

    restaurant_id = table.get('restaurant_id')
    if not restaurant_id:
        raise HTTPException(status_code=404, detail="Ресторан не найден")

    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    settings = await get_or_create_settings(restaurant_id)
    # Restaurant currency is source of truth — override settings.currency
    if isinstance(settings, dict) and restaurant and restaurant.get('currency'):
        settings['currency'] = restaurant['currency']
    sections = await get_or_create_menu_sections(restaurant_id)
    call_types = await get_or_create_call_types(restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    items = await db.menu_items.find({"restaurant_id": restaurant_id, "is_available": True}, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    splash_ads = await db.splash_ads.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)

    view = MenuView(restaurant_id=restaurant_id, table_code=table_code)
    doc = view.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_views.insert_one(doc)

    return {
        "restaurant": serialize_doc(restaurant),
        "table": serialize_doc(table),
        "settings": settings,
        "sections": sections,
        "call_types": call_types,
        "categories": [serialize_doc(c) for c in categories],
        "items": [serialize_doc(i) for i in items],
        "labels": labels,
        "splash_ads": [serialize_doc(s) for s in splash_ads],
    }


@router.get("/public/menu-by-slug/{slug}/{table_number}")
async def get_public_menu_by_slug(slug: str, table_number: int):
    restaurant = await db.restaurants.find_one({"slug": slug}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")

    restaurant_id = restaurant['id']
    table = await db.tables.find_one({"restaurant_id": restaurant_id, "number": table_number}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")

    settings = await get_or_create_settings(restaurant_id)
    if isinstance(settings, dict) and restaurant.get('currency'):
        settings['currency'] = restaurant['currency']
    sections = await get_or_create_menu_sections(restaurant_id)
    call_types = await get_or_create_call_types(restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    items = await db.menu_items.find({"restaurant_id": restaurant_id, "is_available": True}, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    splash_ads = await db.splash_ads.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)

    view = MenuView(restaurant_id=restaurant_id, table_code=table.get('code'))
    doc = view.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_views.insert_one(doc)

    return {
        "restaurant": serialize_doc(restaurant),
        "table": serialize_doc(table),
        "settings": settings,
        "sections": sections,
        "call_types": call_types,
        "categories": [serialize_doc(c) for c in categories],
        "items": [serialize_doc(i) for i in items],
        "labels": labels,
        "splash_ads": [serialize_doc(s) for s in splash_ads],
    }


@router.get("/public/menu-by-domain/{table_number}")
async def get_public_menu_by_domain(table_number: int, request: Request, host: str | None = None):
    """Resolve restaurant by the domain that the client is currently visiting.

    The client passes the active hostname either via Host header (set by Nginx)
    or as `?host=` query (browser fallback). Nginx must already route this
    domain to the backend; this endpoint just looks up which restaurant owns it.
    """
    raw_host = (
        host
        or request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    )
    domain = _normalize_host(raw_host)
    if not domain:
        raise HTTPException(status_code=400, detail="Не удалось определить домен")

    restaurant = await db.restaurants.find_one({"custom_domains": domain}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail=f"Домен {domain} не привязан к ресторану")
    restaurant_id = restaurant['id']
    table = await db.tables.find_one({"restaurant_id": restaurant_id, "number": table_number}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")

    settings = await get_or_create_settings(restaurant_id)
    if isinstance(settings, dict) and restaurant.get('currency'):
        settings['currency'] = restaurant['currency']
    sections = await get_or_create_menu_sections(restaurant_id)
    call_types = await get_or_create_call_types(restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    items = await db.menu_items.find({"restaurant_id": restaurant_id, "is_available": True}, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    splash_ads = await db.splash_ads.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(50)

    view = MenuView(restaurant_id=restaurant_id, table_code=table.get('code'))
    doc = view.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_views.insert_one(doc)

    return {
        "restaurant": serialize_doc(restaurant),
        "table": serialize_doc(table),
        "settings": settings,
        "sections": sections,
        "call_types": call_types,
        "categories": [serialize_doc(c) for c in categories],
        "items": [serialize_doc(i) for i in items],
        "labels": labels,
        "splash_ads": [serialize_doc(s) for s in splash_ads],
    }


@router.get("/public/domain-info")
async def get_public_domain_info(request: Request, host: str | None = None):
    """Lightweight endpoint used by the SPA root route to redirect a bare custom
    domain visit to the restaurant's default menu URL.

    Returns the restaurant slug + the table number of the «Сайт» (website)
    table, if one is marked. Falls back to table #1 otherwise.
    """
    raw_host = (
        host
        or request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    )
    domain = _normalize_host(raw_host)
    if not domain:
        raise HTTPException(status_code=400, detail="Не удалось определить домен")

    restaurant = await db.restaurants.find_one({"custom_domains": domain}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail=f"Домен {domain} не привязан к ресторану")

    # Prefer table marked as «Сайт» (is_website=True). Otherwise default to 1.
    website_table = await db.tables.find_one(
        {"restaurant_id": restaurant["id"], "is_website": True, "is_active": True},
        {"_id": 0, "number": 1},
        sort=[("number", 1)],
    )
    default_table_number = website_table["number"] if website_table else 1

    return {
        "id": restaurant["id"],
        "name": restaurant.get("name", ""),
        "slug": restaurant.get("slug", "") or "",
        "default_table_number": default_table_number,
    }


@router.post("/public/orders")
async def create_public_order(data: OrderCreate):
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")

    restaurant_id = table.get('restaurant_id')
    total = sum(item.price * item.quantity for item in data.items)
    is_preorder = table.get('is_preorder', False)
    is_delivery = table.get('is_delivery', False)

    # Load restaurant currency for notifications
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0, "currency": 1})
    cur = (restaurant or {}).get('currency') or 'BYN'

    order = Order(
        restaurant_id=restaurant_id,
        table_id=table['id'],
        table_number=table['number'],
        items=[i.model_dump() for i in data.items],
        total=total,
        notes=data.notes,
        is_preorder=is_preorder,
        is_delivery=is_delivery,
        customer_name=data.customer_name if (is_preorder or is_delivery) else "",
        customer_phone=data.customer_phone if (is_preorder or is_delivery) else "",
        customer_city=data.customer_city if is_delivery else "",
        customer_address=data.customer_address if is_delivery else "",
        preorder_date=data.preorder_date if is_preorder else "",
        preorder_time=data.preorder_time if is_preorder else "",
    )
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.orders.insert_one(doc)
    doc.pop('_id', None)

    # Telegram notification with inline buttons
    table_num = table.get('number', '?')
    items_text = "\n".join([f"  • {html_module.escape(i.name)} x{i.quantity}" for i in data.items])
    if is_delivery:
        addr_line = f"{html_module.escape(data.customer_city or '')}, {html_module.escape(data.customer_address or '')}".strip(', ')
        msg = (
            f"🚚 <b>Заказ на доставку</b>\n"
            f"👤 {html_module.escape(data.customer_name or '—')}\n"
            f"📱 {html_module.escape(data.customer_phone or '—')}\n"
            f"📍 {addr_line or '—'}\n\n"
            f"{items_text}\n\n"
            f"💰 <b>Итого: {total} {cur}</b>"
        )
    elif is_preorder:
        msg = f"📋 <b>Предзаказ</b>\n👤 {html_module.escape(data.customer_name or '—')}\n📱 {html_module.escape(data.customer_phone or '—')}\n📅 {data.preorder_date or '—'} {data.preorder_time or ''}\n\n{items_text}\n\n💰 <b>Итого: {total} {cur}</b>"
    else:
        msg = f"🍽 <b>Новый заказ</b>\n📍 Стол #{table_num}\n\n{items_text}\n\n💰 <b>Итого: {total} {cur}</b>"
    if data.notes:
        msg += f"\n📝 {html_module.escape(data.notes)}"

    keyboard = build_order_keyboard(doc['id'])
    await notify_restaurant_telegram(restaurant_id, msg, keyboard)

    # Send to Caffesta POS if enabled
    if await is_caffesta_enabled(restaurant_id):
        await caffesta_send_order(restaurant_id, doc)

    await manager.broadcast(restaurant_id, "new_order", doc)

    return doc


@router.post("/public/staff-calls")
async def create_public_staff_call(data: StaffCallCreate):
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")

    restaurant_id = table.get('restaurant_id')
    call_type_name = None
    if data.call_type_id:
        call_type = await db.call_types.find_one({"id": data.call_type_id}, {"_id": 0})
        if call_type:
            call_type_name = call_type.get('name')

    staff_call = StaffCall(
        restaurant_id=restaurant_id,
        table_id=table['id'],
        table_number=table['number'],
        call_type_id=data.call_type_id,
        call_type_name=call_type_name
    )
    doc = staff_call.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.staff_calls.insert_one(doc)
    doc.pop('_id', None)

    table_num = table.get('number', '?')
    if data.call_type_id:
        call_type = await db.call_types.find_one({"id": data.call_type_id}, {"_id": 0})
        tg_template = call_type.get('telegram_message', '') if call_type else ''
        if tg_template:
            msg = tg_template.replace('{table}', str(table_num))
        else:
            msg = f"🔔 <b>{call_type_name or 'Вызов персонала'}</b>\nСтол #{table_num}"
    else:
        msg = f"🔔 <b>Вызов персонала</b>\nСтол #{table_num}"

    keyboard = build_call_keyboard(doc['id'])
    await notify_restaurant_telegram(restaurant_id, msg, keyboard)

    await manager.broadcast(restaurant_id, "new_staff_call", doc)

    return doc


@router.get("/public/orders/{order_id}/status")
async def get_order_status(order_id: str):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0, "id": 1, "status": 1, "created_at": 1, "is_preorder": 1})
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order
