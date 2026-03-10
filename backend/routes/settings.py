from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta

from database import db
from models import SettingsUpdate, Employee, EmployeeCreate
from auth import get_current_user, check_restaurant_access
from helpers import serialize_doc, get_or_create_settings

router = APIRouter()


# ============ SETTINGS ============

@router.get("/restaurants/{restaurant_id}/settings")
async def get_settings(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_settings(restaurant_id)


@router.put("/restaurants/{restaurant_id}/settings")
async def update_settings(restaurant_id: str, data: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.settings.update_one({"restaurant_id": restaurant_id}, {"$set": update_data})
    return await get_or_create_settings(restaurant_id)


# ============ EMPLOYEES ============

@router.get("/restaurants/{restaurant_id}/employees")
async def get_employees(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    employees = await db.employees.find({"restaurant_id": restaurant_id}, {"_id": 0}).to_list(500)
    return [serialize_doc(e) for e in employees]


@router.post("/restaurants/{restaurant_id}/employees")
async def create_employee(restaurant_id: str, data: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    employee = Employee(restaurant_id=restaurant_id, **data.model_dump())
    doc = employee.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.employees.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/employees/{employee_id}")
async def update_employee(restaurant_id: str, employee_id: str, data: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.employees.update_one({"id": employee_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.employees.find_one({"id": employee_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/employees/{employee_id}")
async def delete_employee(restaurant_id: str, employee_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.employees.delete_one({"id": employee_id, "restaurant_id": restaurant_id})
    return {"message": "Employee deleted"}


# ============ ANALYTICS ============

@router.get("/restaurants/{restaurant_id}/analytics")
async def get_analytics(restaurant_id: str, days: int = 30, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    views_total = await db.menu_views.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}})
    views_today = await db.menu_views.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}})

    orders = await db.orders.find({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}}, {"_id": 0}).to_list(5000)
    orders_total = len(orders)
    orders_today = len([o for o in orders if o.get('created_at', '') >= today_start.isoformat()])
    revenue_total = sum(o.get('total', 0) for o in orders)
    revenue_today = sum(o.get('total', 0) for o in orders if o.get('created_at', '') >= today_start.isoformat())

    calls_total = await db.staff_calls.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}})
    calls_today = await db.staff_calls.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}})

    item_counts = {}
    for order in orders:
        for item in order.get('items', []):
            item_id = item.get('menu_item_id')
            if item_id:
                item_counts[item_id] = item_counts.get(item_id, 0) + item.get('quantity', 1)

    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    popular_items = []
    for item_id, count in top_items:
        item = await db.menu_items.find_one({"id": item_id}, {"_id": 0, "name": 1, "price": 1})
        if item:
            popular_items.append({"id": item_id, "name": item.get('name'), "count": count, "revenue": count * item.get('price', 0)})

    views_by_day = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = await db.menu_views.count_documents({
            "restaurant_id": restaurant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        views_by_day.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    orders_by_day = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_orders = [o for o in orders if day_start.isoformat() <= o.get('created_at', '') < day_end.isoformat()]
        orders_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": len(day_orders),
            "revenue": sum(o.get('total', 0) for o in day_orders)
        })

    employees_count = await db.employees.count_documents({"restaurant_id": restaurant_id})

    return {
        "period_days": days,
        "views": {"total": views_total, "today": views_today, "by_day": list(reversed(views_by_day))},
        "orders": {"total": orders_total, "today": orders_today, "by_day": list(reversed(orders_by_day))},
        "revenue": {"total": revenue_total, "today": revenue_today},
        "staff_calls": {"total": calls_total, "today": calls_today},
        "popular_items": popular_items,
        "employees_count": employees_count
    }
