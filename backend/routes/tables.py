from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import uuid
import qrcode
from io import BytesIO
import base64
import os

from database import db
from models import Table, TableCreate
from auth import get_current_user, check_restaurant_access
from helpers import serialize_doc

router = APIRouter()


@router.get("/restaurants/{restaurant_id}/tables")
async def get_tables(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    tables = await db.tables.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("number", 1).to_list(500)
    return [serialize_doc(t) for t in tables]


@router.post("/restaurants/{restaurant_id}/tables")
async def create_table(restaurant_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = Table(restaurant_id=restaurant_id, **data.model_dump())
    doc = table.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tables.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/tables/{table_id}")
async def update_table(restaurant_id: str, table_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.tables.find_one({"id": table_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/tables/{table_id}")
async def delete_table(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.delete_one({"id": table_id, "restaurant_id": restaurant_id})
    return {"message": "Table deleted"}


@router.post("/restaurants/{restaurant_id}/tables/{table_id}/regenerate-code")
async def regenerate_table_code(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    new_code = str(uuid.uuid4())[:8].upper()
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": {"code": new_code}})
    return {"code": new_code}


@router.get("/restaurants/{restaurant_id}/tables/{table_id}/qr")
async def get_table_qr(restaurant_id: str, table_id: str, base_url: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = await db.tables.find_one({"id": table_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if not base_url:
        base_url = os.environ.get('FRONTEND_URL', 'https://example.com')

    menu_url = f"{base_url}/menu/{table['code']}"

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return {
        "table_id": table_id,
        "table_number": table['number'],
        "table_code": table['code'],
        "menu_url": menu_url,
        "qr_base64": f"data:image/png;base64,{img_base64}"
    }
