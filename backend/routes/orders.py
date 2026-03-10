from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from database import db
from models import OrderStatusUpdate, StaffCallStatus, CallType, CallTypeCreate
from auth import get_current_user, check_restaurant_access
from helpers import serialize_doc, get_or_create_call_types
from services.websocket import manager

router = APIRouter()


# ============ ORDERS ============

@router.get("/restaurants/{restaurant_id}/orders")
async def get_orders(restaurant_id: str, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if status:
        query["status"] = status
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(o) for o in orders]


@router.put("/restaurants/{restaurant_id}/orders/{order_id}/status")
async def update_order_status(restaurant_id: str, order_id: str, data: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.orders.update_one({"id": order_id, "restaurant_id": restaurant_id}, {"$set": {"status": data.status}})
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if order:
        await manager.broadcast(restaurant_id, "order_status_changed", serialize_doc(order))
    return order


@router.post("/restaurants/{restaurant_id}/orders/complete-all")
async def complete_all_orders(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.orders.update_many(
        {"restaurant_id": restaurant_id, "status": {"$in": ["new", "in_progress"]}},
        {"$set": {"status": "completed"}}
    )
    return {"message": f"Завершено заказов: {result.modified_count}", "count": result.modified_count}


# ============ STAFF CALLS ============

@router.get("/restaurants/{restaurant_id}/staff-calls")
async def get_staff_calls(restaurant_id: str, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if status:
        query["status"] = status
    calls = await db.staff_calls.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(c) for c in calls]


@router.put("/restaurants/{restaurant_id}/staff-calls/{call_id}/status")
async def update_staff_call_status(restaurant_id: str, call_id: str, status: StaffCallStatus, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.staff_calls.update_one({"id": call_id, "restaurant_id": restaurant_id}, {"$set": {"status": status}})
    return await db.staff_calls.find_one({"id": call_id}, {"_id": 0})


@router.post("/restaurants/{restaurant_id}/staff-calls/complete-all")
async def complete_all_staff_calls(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.staff_calls.update_many(
        {"restaurant_id": restaurant_id, "status": {"$in": ["pending", "acknowledged"]}},
        {"$set": {"status": "completed"}}
    )
    return {"message": f"Завершено вызовов: {result.modified_count}", "count": result.modified_count}


# ============ CALL TYPES ============

@router.get("/restaurants/{restaurant_id}/call-types")
async def get_call_types(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_call_types(restaurant_id)


@router.post("/restaurants/{restaurant_id}/call-types")
async def create_call_type(restaurant_id: str, data: CallTypeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    call_type = CallType(restaurant_id=restaurant_id, **data.model_dump())
    doc = call_type.model_dump()
    await db.call_types.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/call-types/{call_type_id}")
async def update_call_type(restaurant_id: str, call_type_id: str, data: CallTypeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.call_types.update_one({"id": call_type_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.call_types.find_one({"id": call_type_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/call-types/{call_type_id}")
async def delete_call_type(restaurant_id: str, call_type_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.call_types.delete_one({"id": call_type_id, "restaurant_id": restaurant_id})
    return {"message": "Call type deleted"}
