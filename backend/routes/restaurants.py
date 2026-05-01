import re
import socket
import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from database import db
from models import Restaurant, RestaurantCreate, RestaurantUpdate
from auth import get_current_user, require_superadmin, check_restaurant_access
from models import UserRole
from helpers import serialize_doc, get_or_create_settings, get_or_create_menu_sections, get_or_create_call_types

router = APIRouter()


@router.get("/restaurants")
async def get_restaurants(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": current_user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)
    return [serialize_doc(r) for r in restaurants]


@router.post("/restaurants")
async def create_restaurant(data: RestaurantCreate, current_user: dict = Depends(require_superadmin)):
    restaurant = Restaurant(
        name=data.name,
        description=data.description,
        address=data.address,
        phone=data.phone,
        email=data.email,
        enabled_modules=data.enabled_modules or [],
        currency=data.currency or "BYN",
    )
    doc = restaurant.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.restaurants.insert_one(doc)

    await get_or_create_settings(doc['id'])
    await get_or_create_menu_sections(doc['id'])
    await get_or_create_call_types(doc['id'])

    return serialize_doc(doc)


@router.get("/restaurants/{restaurant_id}")
async def get_restaurant_by_id(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    return serialize_doc(restaurant)


@router.put("/restaurants/{restaurant_id}")
async def update_restaurant(restaurant_id: str, data: RestaurantUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    # enabled_modules — only superadmin can change feature flags
    if 'enabled_modules' in update_data and current_user.get('role') != 'superadmin':
        update_data.pop('enabled_modules')

    # custom_domains — only superadmin can manage tenant domains.
    # Normalise to lowercase, no scheme/path, deduplicated.
    if 'custom_domains' in update_data:
        if current_user.get('role') != 'superadmin':
            update_data.pop('custom_domains')
        else:
            cleaned = []
            for d in (update_data['custom_domains'] or []):
                if not isinstance(d, str):
                    continue
                d = d.strip().lower()
                if d.startswith('http://'):
                    d = d[7:]
                elif d.startswith('https://'):
                    d = d[8:]
                d = d.split('/', 1)[0].split(':', 1)[0]  # drop path/port
                if d and d not in cleaned:
                    # uniqueness across all restaurants
                    other = await db.restaurants.find_one(
                        {"custom_domains": d, "id": {"$ne": restaurant_id}}, {"_id": 0, "name": 1}
                    )
                    if other:
                        raise HTTPException(status_code=400, detail=f"Домен {d} уже привязан к ресторану «{other.get('name','?')}»")
                    cleaned.append(d)
            update_data['custom_domains'] = cleaned

    # Validate slug uniqueness and format
    if 'slug' in update_data:
        slug = update_data['slug'].lower().strip()
        if slug:
            if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', slug):
                raise HTTPException(status_code=400, detail="Slug может содержать только латинские буквы, цифры и дефис")
            existing = await db.restaurants.find_one({"slug": slug, "id": {"$ne": restaurant_id}}, {"_id": 0})
            if existing:
                raise HTTPException(status_code=400, detail="Этот slug уже занят другим рестораном")
        update_data['slug'] = slug

    if update_data:
        await db.restaurants.update_one({"id": restaurant_id}, {"$set": update_data})
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    return serialize_doc(restaurant)


@router.delete("/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: str, current_user: dict = Depends(require_superadmin)):
    for coll in ['menu_sections', 'categories', 'menu_items', 'tables', 'orders', 'staff_calls', 'call_types', 'employees', 'settings', 'menu_views']:
        await db[coll].delete_many({"restaurant_id": restaurant_id})
    result = await db.restaurants.delete_one({"id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    return {"message": "Ресторан удален"}


@router.get("/restaurants/{restaurant_id}/domains/check")
async def check_custom_domain(
    restaurant_id: str,
    domain: str,
    current_user: dict = Depends(require_superadmin),
):
    """Diagnose whether a custom domain is fully wired up.

    Performs three checks:
    1. DNS — does the domain resolve at all?
    2. HTTPS reachable — does GET https://{domain}/api/health succeed?
    3. Domain bound to THIS restaurant in DB?

    Returns a structured object the UI can render as a green/yellow/red traffic
    light. Does NOT modify anything (read-only diagnostic).
    """
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")

    domain = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/", 1)[0].split(":", 1)[0]
    if not domain:
        raise HTTPException(status_code=400, detail="Не указан домен")

    result = {
        "domain": domain,
        "dns": {"ok": False, "ips": [], "error": None},
        "https": {"ok": False, "status_code": None, "error": None},
        "binding": {"ok": False, "bound_to": None},
        "overall": "error",
        "summary": "",
    }

    # 1. DNS check
    try:
        infos = await asyncio.get_event_loop().getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
        ips = sorted({info[4][0] for info in infos})
        result["dns"]["ips"] = ips
        result["dns"]["ok"] = bool(ips)
    except Exception as e:
        result["dns"]["error"] = str(e)

    # 2. HTTPS reachability — hit /api/health (defined in routes/seed.py)
    try:
        async with httpx.AsyncClient(timeout=8, verify=True, follow_redirects=False) as client:
            r = await client.get(f"https://{domain}/api/health")
            result["https"]["status_code"] = r.status_code
            result["https"]["ok"] = r.status_code == 200
    except httpx.ConnectError as e:
        result["https"]["error"] = f"Не удалось подключиться: {e}"
    except Exception as e:
        result["https"]["error"] = str(e)

    # 3. Binding check
    bound = await db.restaurants.find_one({"custom_domains": domain}, {"_id": 0, "id": 1, "name": 1})
    if bound:
        result["binding"]["bound_to"] = {"id": bound["id"], "name": bound.get("name")}
        result["binding"]["ok"] = bound["id"] == restaurant_id

    # Overall verdict
    if result["dns"]["ok"] and result["https"]["ok"] and result["binding"]["ok"]:
        result["overall"] = "ok"
        result["summary"] = f"✓ Домен полностью настроен и привязан к ресторану «{restaurant.get('name','')}»."
    elif not result["dns"]["ok"]:
        result["overall"] = "error"
        result["summary"] = f"DNS не настроен. Сделайте A-запись {domain} → IP вашего VPS у регистратора."
    elif not result["https"]["ok"]:
        result["overall"] = "warning"
        result["summary"] = f"DNS настроен ({', '.join(result['dns']['ips'])}), но HTTPS не отвечает. Запустите на VPS: ./scripts/add-domain.sh {domain}"
    elif not result["binding"]["ok"]:
        result["overall"] = "warning"
        if result["binding"]["bound_to"]:
            result["summary"] = f"Домен HTTPS работает, но привязан к другому ресторану «{result['binding']['bound_to']['name']}»."
        else:
            result["summary"] = "Домен отвечает, но не сохранён в списке custom_domains этого ресторана."

    return result
