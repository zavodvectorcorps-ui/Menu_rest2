from datetime import datetime

from database import db
from models import (
    User, Settings, MenuSection, CallType, Restaurant, Table,
    UserRole
)
from auth import get_password_hash


def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop('_id', None)
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc


async def create_superadmin():
    admin = await db.users.find_one({"username": "admin"}, {"_id": 0})
    if not admin:
        user = User(
            username="admin",
            password_hash=get_password_hash("220066"),
            role=UserRole.SUPERADMIN,
            restaurant_ids=[]
        )
        doc = user.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        print("Superadmin created: admin/220066")
    return admin


async def get_or_create_settings(restaurant_id: str):
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings:
        default = Settings(restaurant_id=restaurant_id)
        doc = default.model_dump()
        await db.settings.insert_one(doc)
        return doc
    return settings


async def get_or_create_menu_sections(restaurant_id: str):
    sections = await db.menu_sections.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not sections:
        default_sections = [
            MenuSection(restaurant_id=restaurant_id, name="Еда", sort_order=1),
            MenuSection(restaurant_id=restaurant_id, name="Напитки", sort_order=2),
            MenuSection(restaurant_id=restaurant_id, name="Кальяны", sort_order=3),
        ]
        for section in default_sections:
            await db.menu_sections.insert_one(section.model_dump())
        sections = [s.model_dump() for s in default_sections]
    return sections


async def get_or_create_call_types(restaurant_id: str):
    call_types = await db.call_types.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not call_types:
        default_types = [
            CallType(restaurant_id=restaurant_id, name="Вызов официанта", telegram_message="🔔 Стол #{table} - Вызов официанта", sort_order=1),
            CallType(restaurant_id=restaurant_id, name="Вызов кальянного мастера", telegram_message="💨 Стол #{table} - Вызов кальянного мастера", sort_order=2),
            CallType(restaurant_id=restaurant_id, name="Попросить счёт", telegram_message="💳 Стол #{table} - Просят счёт", sort_order=3),
        ]
        for ct in default_types:
            await db.call_types.insert_one(ct.model_dump())
        call_types = [ct.model_dump() for ct in default_types]
    return call_types
