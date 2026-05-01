import re
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
