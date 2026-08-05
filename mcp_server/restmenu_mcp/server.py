"""
REST-MENU MCP server.

Оборачивает REST API REST-MENU в набор MCP-инструментов, чтобы Claude Desktop
(и любой другой MCP-клиент — Cursor, Cline и т.п.) мог управлять меню:
листать блюда, создавать/редактировать/удалять позиции, менять цены,
переписывать описания, привязывать блюда к каталогу Caffesta и т.д.

Транспорт: stdio. Клиент запускает этот скрипт как subprocess и общается
с ним по stdin/stdout (см. README).

Авторизация:
* `REST_MENU_API_URL` — обычно `https://rest-menu.by` (без /api в конце).
* `REST_MENU_USERNAME` + `REST_MENU_PASSWORD` — учётка администратора.
  Токен получаем при первом вызове и держим в памяти процесса.
* Дополнительно можно задать `REST_MENU_DEFAULT_RESTAURANT` — id ресторана,
  на который автоматически «переключимся» при старте. Иначе клиент вызовет
  `select_restaurant`.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

API_URL = (os.environ.get("REST_MENU_API_URL") or "https://rest-menu.by").rstrip("/")
USERNAME = os.environ.get("REST_MENU_USERNAME") or ""
PASSWORD = os.environ.get("REST_MENU_PASSWORD") or ""
DEFAULT_RESTAURANT = os.environ.get("REST_MENU_DEFAULT_RESTAURANT") or ""

mcp = FastMCP("restmenu")


# ─── глобальное состояние сессии ────────────────────────────────────────────

class Session:
    token: str | None = None
    restaurant_id: str | None = None
    restaurants_cache: list[dict[str, Any]] = []


session = Session()


# ─── helpers ────────────────────────────────────────────────────────────────

async def _login() -> str:
    """Логин по username/password → JWT токен. Кэшируется в памяти."""
    if session.token:
        return session.token
    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "REST_MENU_USERNAME / REST_MENU_PASSWORD не заданы в окружении. "
            "Задайте их в claude_desktop_config.json (env)."
        )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )
        resp.raise_for_status()
        data = resp.json()
        session.token = data.get("access_token") or data.get("token")
        if not session.token:
            raise RuntimeError(f"Login failed: {data}")
    return session.token


async def _request(
    method: str,
    path: str,
    *,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """Универсальный HTTP-запрос с автоматическим повтором логина при 401."""
    token = await _login()
    url = f"{API_URL}{path}" if path.startswith("/") else f"{API_URL}/{path}"
    async with httpx.AsyncClient(timeout=60) as client:
        for attempt in (1, 2):
            resp = await client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=json_body,
                params=params,
            )
            if resp.status_code == 401 and attempt == 1:
                # Токен истёк — сбросим и попробуем снова.
                session.token = None
                token = await _login()
                continue
            break
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"{method} {path} → {resp.status_code}: {detail}")
    if not resp.content:
        return {"ok": True}
    return resp.json()


def _need_rid() -> str:
    if not session.restaurant_id:
        raise RuntimeError(
            "Ресторан не выбран. Вызови list_restaurants и затем select_restaurant."
        )
    return session.restaurant_id


# ─── auth & restaurants ─────────────────────────────────────────────────────

@mcp.tool()
async def whoami() -> dict:
    """Проверить авторизацию: вернёт текущего пользователя и активный ресторан."""
    me = await _request("GET", "/api/auth/me")
    return {
        "user": me,
        "current_restaurant_id": session.restaurant_id,
        "api_url": API_URL,
    }


@mcp.tool()
async def list_restaurants() -> list[dict]:
    """
    Список ресторанов, к которым у пользователя есть доступ.
    Кэшируется в сессии — использовать перед select_restaurant.
    """
    data = await _request("GET", "/api/restaurants")
    session.restaurants_cache = data if isinstance(data, list) else []
    return session.restaurants_cache


@mcp.tool()
async def select_restaurant(id_or_name: str) -> dict:
    """
    Выбрать активный ресторан по id или по имени (case-insensitive substring).
    Все последующие операции с меню будут работать с ним.
    """
    if not session.restaurants_cache:
        await list_restaurants()
    q = id_or_name.strip().lower()
    match = next(
        (
            r
            for r in session.restaurants_cache
            if r.get("id") == id_or_name or q in (r.get("name") or "").lower()
        ),
        None,
    )
    if not match:
        raise RuntimeError(f"Ресторан не найден: {id_or_name}")
    session.restaurant_id = match["id"]
    return {"selected": match}


# ─── меню: чтение ───────────────────────────────────────────────────────────

@mcp.tool()
async def list_sections() -> list[dict]:
    """Все секции меню (например: Гастрономическое, Барное, Кальянное)."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/sections")


@mcp.tool()
async def list_categories(section_id: str | None = None) -> list[dict]:
    """Все категории (или в конкретной секции)."""
    rid = _need_rid()
    params = {"section_id": section_id} if section_id else None
    return await _request("GET", f"/api/restaurants/{rid}/categories", params=params)


@mcp.tool()
async def list_menu_items(
    category_id: str | None = None,
    search: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """
    Список блюд. Можно фильтровать по category_id и/или по search-подстроке
    в названии/описании (регистронезависимо).
    """
    rid = _need_rid()
    params: dict[str, Any] = {}
    if category_id:
        params["category_id"] = category_id
    items = await _request(
        "GET", f"/api/restaurants/{rid}/menu-items", params=params or None
    )
    if search:
        s = search.lower()
        items = [
            i
            for i in items
            if s in (i.get("name") or "").lower()
            or s in (i.get("description") or "").lower()
        ]
    return items[:limit]


@mcp.tool()
async def get_menu_item(item_id: str) -> dict:
    """Полная информация об одном блюде."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/menu-items/{item_id}")


# ─── меню: запись ───────────────────────────────────────────────────────────

@mcp.tool()
async def create_category(
    name: str,
    section_id: str | None = None,
    display_mode: str | None = None,
    sort_order: int | None = None,
    is_active: bool = True,
) -> dict:
    """
    Создать новую категорию.
    Поля модели: name, section_id, display_mode ('card' | 'compact'), sort_order, is_active.
    """
    rid = _need_rid()
    payload: dict[str, Any] = {"name": name, "is_active": is_active}
    if section_id:
        payload["section_id"] = section_id
    if display_mode:
        payload["display_mode"] = display_mode
    if sort_order is not None:
        payload["sort_order"] = sort_order
    return await _request("POST", f"/api/restaurants/{rid}/categories", json_body=payload)


@mcp.tool()
async def update_category(category_id: str, updates: dict) -> dict:
    """
    Обновить категорию. Допустимые поля (все опциональные):
    - name (str)
    - section_id (str)
    - display_mode ('card' | 'compact')
    - sort_order (int)
    - is_active (bool) — включена ли категория. Скрыть = is_active: false.
    Прочие поля молча игнорируются сервером.
    """
    rid = _need_rid()
    return await _request(
        "PUT", f"/api/restaurants/{rid}/categories/{category_id}", json_body=updates
    )


@mcp.tool()
async def bulk_rename_categories(mapping: dict[str, str]) -> dict:
    """
    Массово переименовать категории. mapping = {category_id: new_name, ...}
    """
    rid = _need_rid()
    return await _request(
        "POST",
        f"/api/restaurants/{rid}/categories/bulk-rename",
        json_body={"renames": mapping},
    )


@mcp.tool()
async def create_menu_item(
    name: str,
    price: float,
    category_id: str,
    description: str | None = None,
    weight: str | None = None,
    image_url: str | None = None,
    is_available: bool = True,
    extra: dict | None = None,
) -> dict:
    """
    Создать блюдо. extra — любые дополнительные поля, если модель их поддерживает
    (labels, nutrition, allergens и т.д.).
    """
    rid = _need_rid()
    payload: dict[str, Any] = {
        "name": name,
        "price": price,
        "category_id": category_id,
        "is_available": is_available,
    }
    if description:
        payload["description"] = description
    if weight:
        payload["weight"] = weight
    if image_url:
        payload["image_url"] = image_url
    if extra:
        payload.update(extra)
    return await _request("POST", f"/api/restaurants/{rid}/menu-items", json_body=payload)


@mcp.tool()
async def update_menu_item(item_id: str, updates: dict) -> dict:
    """
    Обновить блюдо. updates — любые поля модели MenuItem:
    name, description, price, weight, image_url, video_url, category_id,
    is_available, is_new, is_hit, nutrition, labels и т.д.
    """
    rid = _need_rid()
    return await _request(
        "PUT", f"/api/restaurants/{rid}/menu-items/{item_id}", json_body=updates
    )


@mcp.tool()
async def delete_menu_item(item_id: str) -> dict:
    """Удалить блюдо."""
    rid = _need_rid()
    return await _request("DELETE", f"/api/restaurants/{rid}/menu-items/{item_id}")


# ─── batch-операции для быстрых сценариев ───────────────────────────────────

@mcp.tool()
async def bulk_update_prices(updates: list[dict]) -> dict:
    """
    Массово обновить цены. updates — список {"id": str, "price": float}.
    Возвращает {ok: [...], failed: [...]}.
    """
    ok, failed = [], []
    for u in updates:
        try:
            r = await update_menu_item(u["id"], {"price": u["price"]})
            ok.append({"id": u["id"], "price": u["price"], "name": r.get("name")})
        except Exception as e:
            failed.append({"id": u.get("id"), "error": str(e)})
    return {"ok": ok, "failed": failed}


@mcp.tool()
async def bulk_update_items(updates: list[dict]) -> dict:
    """
    Массово обновить блюда произвольными полями.
    updates — список {"id": str, ...любые поля...}.
    Пример: [{"id": "abc", "description": "new text"}, {"id": "def", "is_hit": true}]
    """
    ok, failed = [], []
    for u in updates:
        item_id = u.pop("id", None)
        if not item_id:
            failed.append({"error": "missing id", "payload": u})
            continue
        try:
            r = await update_menu_item(item_id, u)
            ok.append({"id": item_id, "name": r.get("name")})
        except Exception as e:
            failed.append({"id": item_id, "error": str(e)})
    return {"ok": ok, "failed": failed}


# ─── Caffesta ───────────────────────────────────────────────────────────────

@mcp.tool()
async def list_caffesta_products(search: str | None = None, limit: int = 200) -> list[dict]:
    """
    Каталог POS Caffesta (продукты + полуфабрикаты). Используется для привязки
    блюд к каталогу (для контроля себестоимости).
    """
    rid = _need_rid()
    products = await _request("GET", f"/api/restaurants/{rid}/caffesta/products")
    if search:
        s = search.lower()
        products = [
            p for p in products if s in (p.get("name") or "").lower()
        ]
    return products[:limit]


@mcp.tool()
async def caffesta_sales_report(date_from: str, date_to: str) -> dict:
    """
    Отчёт по продажам из Caffesta (POS). date_from / date_to в формате YYYY-MM-DD.
    Возвращает по каждому блюду: количество продаж, сумму, средний чек.
    """
    rid = _need_rid()
    return await _request(
        "GET",
        f"/api/restaurants/{rid}/caffesta/sales-report",
        params={"date_from": date_from, "date_to": date_to},
    )


@mcp.tool()
async def caffesta_analytics(days: int = 30) -> dict:
    """
    Сводная аналитика продаж Caffesta за последние N дней:
    выручка, топ-блюда, топ-категории, dynamics.
    """
    rid = _need_rid()
    return await _request(
        "GET", f"/api/restaurants/{rid}/caffesta/analytics", params={"days": days}
    )


# ─── Заказы ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_orders(status: str | None = None, limit: int = 100) -> list[dict]:
    """
    Список заказов ресторана. status: `new`, `processing`, `completed`, `cancelled`.
    """
    rid = _need_rid()
    params: dict[str, Any] = {"limit": limit}
    if status:
        params["status"] = status
    return await _request("GET", f"/api/restaurants/{rid}/orders", params=params)


@mcp.tool()
async def update_order_status(order_id: str, status: str) -> dict:
    """
    Изменить статус заказа. status: `new` | `processing` | `completed` | `cancelled`.
    """
    rid = _need_rid()
    return await _request(
        "PUT",
        f"/api/restaurants/{rid}/orders/{order_id}/status",
        json_body={"status": status},
    )


@mcp.tool()
async def complete_all_orders() -> dict:
    """Пометить все активные заказы как выполненные (bulk)."""
    rid = _need_rid()
    return await _request("POST", f"/api/restaurants/{rid}/orders/complete-all")


# ─── Вызовы официанта ──────────────────────────────────────────────────────

@mcp.tool()
async def list_staff_calls(status: str | None = None) -> list[dict]:
    """История вызовов официанта. status: `pending` | `completed`."""
    rid = _need_rid()
    params = {"status": status} if status else None
    return await _request("GET", f"/api/restaurants/{rid}/staff-calls", params=params)


@mcp.tool()
async def update_staff_call_status(call_id: str, status: str) -> dict:
    """Изменить статус вызова: `pending` | `completed`."""
    rid = _need_rid()
    return await _request(
        "PUT",
        f"/api/restaurants/{rid}/staff-calls/{call_id}/status",
        json_body={"status": status},
    )


@mcp.tool()
async def complete_all_staff_calls() -> dict:
    """Пометить все активные вызовы официанта как обработанные."""
    rid = _need_rid()
    return await _request("POST", f"/api/restaurants/{rid}/staff-calls/complete-all")


# ─── Аналитика & Digest ────────────────────────────────────────────────────

@mcp.tool()
async def get_analytics(days: int = 30) -> dict:
    """Внутренняя аналитика (заказы через QR-меню) за последние N дней."""
    rid = _need_rid()
    return await _request(
        "GET", f"/api/restaurants/{rid}/analytics", params={"days": days}
    )


@mcp.tool()
async def get_digest_preview(date: str | None = None) -> dict:
    """
    Превью Telegram-сводки за конкретную дату (YYYY-MM-DD).
    Без даты — за вчера.
    """
    rid = _need_rid()
    params = {"date": date} if date else None
    return await _request(
        "GET", f"/api/restaurants/{rid}/digest/preview", params=params
    )


@mcp.tool()
async def send_digest_now(date: str | None = None) -> dict:
    """Отправить Telegram-сводку сейчас (админ-триггер, не ждать 10:00)."""
    rid = _need_rid()
    payload = {"date": date} if date else {}
    return await _request(
        "POST", f"/api/restaurants/{rid}/digest/send", json_body=payload
    )


# ─── Видео (fal.ai) ────────────────────────────────────────────────────────

@mcp.tool()
async def generate_video_from_image(
    image_url: str,
    prompt: str = "cinematic slow zoom",
    duration: str = "5",
) -> dict:
    """
    Сгенерировать mp4 из фото блюда через fal.ai (Kling).
    image_url — публичный HTTP(S) URL картинки.
    Возвращает {request_id}. Дальше опрашивай check_video_status.
    """
    rid = _need_rid()
    return await _request(
        "POST",
        f"/api/restaurants/{rid}/videos/generate",
        json_body={"image_url": image_url, "prompt": prompt, "duration": duration},
    )


@mcp.tool()
async def check_video_status(request_id: str) -> dict:
    """
    Проверить статус генерации видео: `queued` | `in_progress` | `completed` | `failed`.
    При completed возвращает `video_url`, который можно сразу подставить в menu_item.
    """
    rid = _need_rid()
    return await _request(
        "GET", f"/api/restaurants/{rid}/videos/status/{request_id}"
    )


# ─── Столы & QR ────────────────────────────────────────────────────────────

@mcp.tool()
async def list_tables() -> list[dict]:
    """Список столов ресторана (с QR-кодами)."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/tables")


@mcp.tool()
async def create_table(number: int, name: str | None = None) -> dict:
    """Создать стол с номером `number`."""
    rid = _need_rid()
    payload: dict[str, Any] = {"number": number}
    if name:
        payload["name"] = name
    return await _request(
        "POST", f"/api/restaurants/{rid}/tables", json_body=payload
    )


# ─── Splash-Ads (сториз-заставки) ──────────────────────────────────────────

@mcp.tool()
async def list_splash_ads() -> list[dict]:
    """Активные splash-заставки (рекламные попапы) при открытии меню."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/splash-ads")


@mcp.tool()
async def create_splash_ad(
    title: str | None = None,
    text: str | None = None,
    image_url: str | None = None,
    is_active: bool = True,
) -> dict:
    """Создать splash-заставку. Хотя бы одно из title / text / image_url обязательно."""
    rid = _need_rid()
    payload: dict[str, Any] = {"is_active": is_active}
    if title:
        payload["title"] = title
    if text:
        payload["text"] = text
    if image_url:
        payload["image_url"] = image_url
    return await _request(
        "POST", f"/api/restaurants/{rid}/splash-ads", json_body=payload
    )


@mcp.tool()
async def delete_splash_ad(ad_id: str) -> dict:
    """Удалить splash-заставку."""
    rid = _need_rid()
    return await _request(
        "DELETE", f"/api/restaurants/{rid}/splash-ads/{ad_id}"
    )


# ─── Лейблы (Веган / Острый / Новинка / …) ─────────────────────────────────

@mcp.tool()
async def list_labels() -> list[dict]:
    """Каталог кастомных лейблов ресторана."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/labels")


@mcp.tool()
async def create_label(
    name: str,
    icon: str | None = None,
    color: str | None = None,
) -> dict:
    """Создать кастомный лейбл (например «Веган», «Острое»)."""
    rid = _need_rid()
    payload: dict[str, Any] = {"name": name}
    if icon:
        payload["icon"] = icon
    if color:
        payload["color"] = color
    return await _request(
        "POST", f"/api/restaurants/{rid}/labels", json_body=payload
    )


# ─── Настройки ресторана ───────────────────────────────────────────────────

@mcp.tool()
async def get_settings() -> dict:
    """Настройки: валюта, темы, включённые языки, cart_enabled, staff_call_enabled и т.д."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/settings")


@mcp.tool()
async def update_settings(updates: dict) -> dict:
    """
    Обновить настройки. Примеры полей:
    - currency: "BYN" | "RUB" | "USD" | ...
    - theme: "light" | "dark"
    - enabled_languages: ["ru", "en", "zh"]
    - cart_enabled: bool
    - staff_call_enabled: bool
    """
    rid = _need_rid()
    return await _request(
        "PUT", f"/api/restaurants/{rid}/settings", json_body=updates
    )


@mcp.tool()
async def update_restaurant(updates: dict) -> dict:
    """
    Обновить сам ресторан. Поля: name, description, address, phone, email,
    logo_url, working_hours, slogan, currency, slug.
    """
    rid = _need_rid()
    return await _request("PUT", f"/api/restaurants/{rid}", json_body=updates)


# ─── Рецепты & себестоимость ───────────────────────────────────────────────

@mcp.tool()
async def get_recipe(item_id: str) -> dict:
    """Рецепт (тех.карта) блюда с ингредиентами и себестоимостью."""
    rid = _need_rid()
    return await _request(
        "GET", f"/api/restaurants/{rid}/menu-items/{item_id}/recipe"
    )


@mcp.tool()
async def set_recipe(item_id: str, ingredients: list[dict], yield_g: float | None = None) -> dict:
    """
    Установить/обновить рецепт блюда.
    ingredients — список {"product_id": "...", "quantity_g": 120, "name": "Курица"}.
    """
    rid = _need_rid()
    payload: dict[str, Any] = {"ingredients": ingredients}
    if yield_g is not None:
        payload["yield_g"] = yield_g
    return await _request(
        "PUT",
        f"/api/restaurants/{rid}/menu-items/{item_id}/recipe",
        json_body=payload,
    )


@mcp.tool()
async def ai_parse_recipe(item_id: str, raw_text: str) -> dict:
    """
    AI Chef Assistant: пропарсить свободный текст раскладки блюда
    (напр. «Курица 120г, соус ткемали 30г, руккола 20г») в структурированный
    рецепт с fuzzy-матчингом ингредиентов на каталог Caffesta.
    """
    rid = _need_rid()
    return await _request(
        "POST",
        f"/api/restaurants/{rid}/recipes/ai-parse",
        json_body={"item_id": item_id, "raw_text": raw_text},
    )


@mcp.tool()
async def factual_margin(days: int = 30) -> dict:
    """
    Фактическая маржа: сколько заработали / потратили за N дней
    на основе продаж Caffesta и рецептов.
    """
    rid = _need_rid()
    return await _request(
        "GET", f"/api/restaurants/{rid}/costs/factual-margin", params={"days": days}
    )


# ─── Лояльность ────────────────────────────────────────────────────────────

@mcp.tool()
async def loyalty_list_clients(search: str | None = None, linked_only: bool = True, limit: int = 200) -> list[dict]:
    """Клиенты программы лояльности. По умолчанию — только те, у кого привязан Telegram."""
    rid = _need_rid()
    params: dict[str, Any] = {"limit": limit, "linked_only": linked_only}
    if search:
        params["search"] = search
    return await _request("GET", f"/api/restaurants/{rid}/loyalty/clients", params=params)


@mcp.tool()
async def loyalty_send_message(client_id: str, text: str) -> dict:
    """
    Отправить сообщение одному клиенту программы лояльности.
    Поддерживает плейсхолдеры {name}, {balance}. Клиент должен быть привязан к Telegram.
    """
    rid = _need_rid()
    return await _request(
        "POST",
        f"/api/restaurants/{rid}/loyalty/clients/{client_id}/message",
        json_body={"text": text},
    )


@mcp.tool()
async def loyalty_broadcast(
    text: str,
    min_balance: float | None = None,
    max_balance: float | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Массовая рассылка всем привязанным клиентам. dry_run=true — сначала посмотреть,
    сколько получателей, без отправки. Поддерживает {name}, {balance}.
    """
    rid = _need_rid()
    payload: dict[str, Any] = {"text": text, "dry_run": dry_run}
    if min_balance is not None:
        payload["min_balance"] = min_balance
    if max_balance is not None:
        payload["max_balance"] = max_balance
    return await _request(
        "POST", f"/api/restaurants/{rid}/loyalty/broadcast", json_body=payload
    )


@mcp.tool()
async def loyalty_stats() -> dict:
    """Сводка по программе лояльности: клиентов всего, привязано TG, уведомлений сегодня."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/loyalty/stats")


# ─── Экспорт ───────────────────────────────────────────────────────────────

@mcp.tool()
async def export_menu_csv(save_to: str | None = None) -> dict:
    """
    Экспорт всего меню ресторана в CSV (UTF-8 c BOM, разделитель `;`).
    Возвращает {rows, csv_text, saved_to?}.
    Если `save_to` задан — сохраняет файл по этому абсолютному пути и добавляет `saved_to`.
    """
    rid = _need_rid()
    token = await _login()
    url = f"{API_URL}/api/restaurants/{rid}/menu-items/export.csv"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")
    result: dict[str, Any] = {"rows": max(0, text.count("\n") - 1), "csv_text": text}
    if save_to:
        with open(save_to, "wb") as f:
            f.write(resp.content)
        result["saved_to"] = save_to
    return result


# ─── Переводы (RU/EN/ZH) ───────────────────────────────────────────────────

@mcp.tool()
async def translate_all_now() -> dict:
    """Запустить AI-перевод всех текстов меню на включённые языки."""
    rid = _need_rid()
    return await _request("POST", f"/api/restaurants/{rid}/translate-all")


@mcp.tool()
async def get_translate_status() -> dict:
    """Статус фонового перевода: сколько текстов уже готово, сколько в очереди."""
    rid = _need_rid()
    return await _request("GET", f"/api/restaurants/{rid}/translate-status")


# ─── entrypoint ─────────────────────────────────────────────────────────────

def main() -> None:
    """Запуск через stdio (для Claude Desktop / Cursor)."""
    if DEFAULT_RESTAURANT:
        # Просто ставим id — валидация случится при первом обращении.
        session.restaurant_id = DEFAULT_RESTAURANT
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
