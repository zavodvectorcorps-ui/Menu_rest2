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
    description: str | None = None,
) -> dict:
    """Создать новую категорию."""
    rid = _need_rid()
    payload: dict[str, Any] = {"name": name}
    if section_id:
        payload["section_id"] = section_id
    if description:
        payload["description"] = description
    return await _request("POST", f"/api/restaurants/{rid}/categories", json_body=payload)


@mcp.tool()
async def update_category(category_id: str, updates: dict) -> dict:
    """
    Обновить категорию. updates — словарь с любыми полями:
    name, description, section_id, order, is_visible.
    """
    rid = _need_rid()
    return await _request(
        "PATCH", f"/api/restaurants/{rid}/categories/{category_id}", json_body=updates
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
        "PATCH", f"/api/restaurants/{rid}/menu-items/{item_id}", json_body=updates
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


# ─── entrypoint ─────────────────────────────────────────────────────────────

def main() -> None:
    """Запуск через stdio (для Claude Desktop / Cursor)."""
    if DEFAULT_RESTAURANT:
        # Просто ставим id — валидация случится при первом обращении.
        session.restaurant_id = DEFAULT_RESTAURANT
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
