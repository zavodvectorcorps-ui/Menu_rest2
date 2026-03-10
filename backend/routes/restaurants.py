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
        email=data.email
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
