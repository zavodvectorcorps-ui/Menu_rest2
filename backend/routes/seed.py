from fastapi import APIRouter
from datetime import datetime, timezone

from database import db
from models import Restaurant, Table
from helpers import (
    create_superadmin, get_or_create_settings,
    get_or_create_menu_sections, get_or_create_call_types
)

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/seed")
async def seed_data():
    await create_superadmin()

    count = await db.restaurants.count_documents({})
    if count == 0:
        r1 = Restaurant(
            name="Мята Спортивная",
            description="Уютный ресторан с авторской кухней и кальянами",
            address="ул. Спортивная, 15",
            phone="+375 (29) 123-45-67",
            email="info@myata-sport.by",
            slogan="Вкус, который запоминается",
            working_hours="Пн-Вс: 12:00 - 02:00"
        )
        doc1 = r1.model_dump()
        doc1['created_at'] = doc1['created_at'].isoformat()
        await db.restaurants.insert_one(doc1)

        r2 = Restaurant(
            name="Мята Центральная",
            description="Ресторан в центре города с панорамным видом",
            address="пр. Независимости, 50",
            phone="+375 (29) 765-43-21",
            email="info@myata-central.by",
            slogan="Вкус на высоте",
            working_hours="Пн-Вс: 11:00 - 01:00"
        )
        doc2 = r2.model_dump()
        doc2['created_at'] = doc2['created_at'].isoformat()
        await db.restaurants.insert_one(doc2)

        for doc in [doc1, doc2]:
            rid = doc['id']
            await get_or_create_settings(rid)
            await get_or_create_menu_sections(rid)
            await get_or_create_call_types(rid)

            for i in range(1, 11):
                table = Table(restaurant_id=rid, number=i, name=f"Стол {i}")
                tdoc = table.model_dump()
                tdoc['created_at'] = tdoc['created_at'].isoformat()
                await db.tables.insert_one(tdoc)

    return {"message": "Data seeded successfully"}
