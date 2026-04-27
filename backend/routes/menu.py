from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from typing import List, Optional
from pathlib import Path
import uuid
import re as _re

from database import db
from models import (
    MenuSection, MenuSectionCreate, Category, CategoryCreate, CategoryUpdate,
    MenuItem, MenuItemCreate, MenuItemUpdate, Label, LabelCreate, LabelUpdate,
    ImportMenuRequest
)
from auth import get_current_user, check_restaurant_access
from helpers import serialize_doc, get_or_create_menu_sections
from services.images import download_images_task

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

router = APIRouter()


# ============ MENU SECTIONS ============

@router.get("/restaurants/{restaurant_id}/menu-sections")
async def get_menu_sections(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_menu_sections(restaurant_id)


@router.post("/restaurants/{restaurant_id}/menu-sections")
async def create_menu_section(restaurant_id: str, data: MenuSectionCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    section = MenuSection(restaurant_id=restaurant_id, **data.model_dump())
    doc = section.model_dump()
    await db.menu_sections.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/menu-sections/{section_id}")
async def update_menu_section(restaurant_id: str, section_id: str, data: MenuSectionCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_sections.update_one({"id": section_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    return await db.menu_sections.find_one({"id": section_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/menu-sections/{section_id}")
async def delete_menu_section(restaurant_id: str, section_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_sections.delete_one({"id": section_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.categories.update_many({"section_id": section_id}, {"$set": {"section_id": None}})
    return {"message": "Section deleted"}


# ============ CATEGORIES ============

@router.get("/restaurants/{restaurant_id}/categories")
async def get_categories(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    return [serialize_doc(c) for c in categories]


@router.post("/restaurants/{restaurant_id}/categories")
async def create_category(restaurant_id: str, data: CategoryCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    category = Category(restaurant_id=restaurant_id, **data.model_dump())
    doc = category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/categories/{category_id}")
async def update_category(restaurant_id: str, category_id: str, data: CategoryUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        result = await db.categories.update_one({"id": category_id, "restaurant_id": restaurant_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
    return await db.categories.find_one({"id": category_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/categories/{category_id}")
async def delete_category(restaurant_id: str, category_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.categories.delete_one({"id": category_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.menu_items.delete_many({"category_id": category_id})
    return {"message": "Category deleted"}


@router.post("/restaurants/{restaurant_id}/categories/reorder")
async def reorder_categories(restaurant_id: str, order: List[str], current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    for idx, cat_id in enumerate(order):
        await db.categories.update_one({"id": cat_id, "restaurant_id": restaurant_id}, {"$set": {"sort_order": idx}})
    return {"message": "Reordered"}


# ============ MENU ITEMS ============

@router.get("/restaurants/{restaurant_id}/menu-items")
async def get_menu_items(restaurant_id: str, category_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if category_id:
        query["category_id"] = category_id
    items = await db.menu_items.find(query, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    return [serialize_doc(i) for i in items]


@router.post("/restaurants/{restaurant_id}/menu-items")
async def create_menu_item(restaurant_id: str, data: MenuItemCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    item = MenuItem(restaurant_id=restaurant_id, **data.model_dump())
    doc = item.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_items.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def update_menu_item(restaurant_id: str, item_id: str, data: MenuItemUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": update_data})
    # If price changed, re-evaluate margin alerts for this restaurant
    if "price" in update_data:
        try:
            from routes.cost_control import _send_margin_alerts
            await _send_margin_alerts(restaurant_id)
        except Exception:
            pass
    return await db.menu_items.find_one({"id": item_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def delete_menu_item(restaurant_id: str, item_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_items.delete_one({"id": item_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}


@router.post("/restaurants/{restaurant_id}/menu-items/reorder")
async def reorder_items(restaurant_id: str, order: List[str], current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    for idx, item_id in enumerate(order):
        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": {"sort_order": idx}})
    return {"message": "Reordered"}


# ============ LABELS ============

@router.get("/restaurants/{restaurant_id}/labels")
async def get_labels(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    return labels


@router.post("/restaurants/{restaurant_id}/labels")
async def create_label(restaurant_id: str, data: LabelCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    label = Label(restaurant_id=restaurant_id, name=data.name, color=data.color)
    doc = label.model_dump()
    await db.labels.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put("/restaurants/{restaurant_id}/labels/{label_id}")
async def update_label(restaurant_id: str, label_id: str, data: LabelUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.labels.update_one({"id": label_id, "restaurant_id": restaurant_id}, {"$set": update_data})
    return await db.labels.find_one({"id": label_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/labels/{label_id}")
async def delete_label(restaurant_id: str, label_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.labels.delete_one({"id": label_id, "restaurant_id": restaurant_id})
    await db.menu_items.update_many(
        {"restaurant_id": restaurant_id, "label_ids": label_id},
        {"$pull": {"label_ids": label_id}}
    )
    return {"message": "Label deleted"}


# ============ FILE UPLOAD ============

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимум 5MB")

    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOADS_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/api/uploads/{filename}", "filename": filename}


@router.post("/restaurants/{restaurant_id}/download-images")
async def download_menu_images(restaurant_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    items = await db.menu_items.find(
        {"restaurant_id": restaurant_id, "image_url": {"$regex": "^https?://"}},
        {"_id": 0, "id": 1, "image_url": 1}
    ).to_list(5000)

    if not items:
        return {"message": "Нет внешних изображений", "total": 0}

    background_tasks.add_task(download_images_task, restaurant_id, items)
    return {"message": f"Запущено скачивание {len(items)} изображений. Это может занять несколько минут.", "total": len(items)}


# ============ IMPORT MENU ============

def strip_html(text: str) -> str:
    if not text:
        return ""
    return _re.sub(r'<[^>]+>', '', text).strip()


def parse_lunchpad_data(raw_data: list) -> dict:
    categories = []
    pending_banners = []

    for entry in raw_data:
        entry_type = entry.get("type")

        if entry_type == 2:
            foto = entry.get("foto", {}) or {}
            image_url = foto.get("image_url", "") or ""
            if image_url:
                banner_name = strip_html(entry.get("name", "")).strip()
                banner_desc = strip_html(entry.get("description", "")).strip()
                if banner_name == "--":
                    banner_name = ""
                pending_banners.append({
                    "name": banner_name, "description": banner_desc,
                    "image_url": image_url, "is_banner": True, "price": 0,
                })
            continue

        if entry_type != 0:
            continue

        cat_name = strip_html(entry.get("name", "")).strip()
        if not cat_name:
            continue

        items_raw = entry.get("items", [])
        display = entry.get("display", "")
        display_mode = "compact" if display == "list" else "card"
        items = []
        sub_categories = []

        for banner in pending_banners:
            items.append(banner)
        pending_banners = []

        for item in items_raw:
            item_type = item.get("type")

            if item_type == 2:
                item_foto = item.get("foto", {}) or {}
                item_img = item_foto.get("image_url", "") or ""
                if item_img:
                    banner_name = strip_html(item.get("name", "")).strip()
                    if banner_name == "--":
                        banner_name = ""
                    items.append({
                        "name": banner_name, "description": strip_html(item.get("description", "")),
                        "image_url": item_img, "is_banner": True, "price": 0,
                    })
                continue

            if item_type == 0:
                sub_name = strip_html(item.get("name", "")).strip()
                sub_items_raw = item.get("items", [])
                if sub_name and sub_items_raw:
                    sub_items = []
                    for sub_item in sub_items_raw:
                        if sub_item.get("type") != 4:
                            continue
                        si_name = strip_html(sub_item.get("name", "")).strip()
                        if not si_name:
                            continue
                        si_desc = strip_html(sub_item.get("description", ""))
                        si_prices = sub_item.get("prices", [])
                        si_price = 0
                        si_weight = ""
                        if si_prices:
                            sp = si_prices[0]
                            raw_p = sp.get("price", 0)
                            if isinstance(raw_p, (int, float)):
                                si_price = float(raw_p)
                            elif isinstance(raw_p, str):
                                cleaned = raw_p.replace(',', '.').strip()
                                match = _re.search(r'[\d]+[.]?[\d]*', cleaned)
                                si_price = float(match.group()) if match else 0
                            si_weight = sp.get("measure", "")
                        si_foto = sub_item.get("foto", {}) or {}
                        si_img = si_foto.get("image_url", "") or ""
                        sub_items.append({
                            "name": si_name, "description": si_desc, "price": si_price,
                            "weight": si_weight, "image_url": si_img,
                            "is_available": not sub_item.get("in_stop_list", False),
                        })
                    if sub_items:
                        sub_categories.append({
                            "name": f"{cat_name} — {sub_name}",
                            "display_mode": display_mode, "items": sub_items,
                        })
                continue

            if item_type != 4:
                continue

            item_name = strip_html(item.get("name", "")).strip()
            if not item_name:
                continue

            description = strip_html(item.get("description", ""))
            prices = item.get("prices", [])
            price = 0
            weight = ""
            if prices:
                p = prices[0]
                raw_price = p.get("price", 0)
                if isinstance(raw_price, (int, float)):
                    price = float(raw_price)
                elif isinstance(raw_price, str):
                    cleaned = raw_price.replace(',', '.').strip()
                    match = _re.search(r'[\d]+[.]?[\d]*', cleaned)
                    price = float(match.group()) if match else 0
                weight = p.get("measure", "")

            foto = item.get("foto", {}) or {}
            image_url = foto.get("image_url", "") or ""
            in_stop = item.get("in_stop_list", False)

            items.append({
                "name": item_name, "description": description, "price": price,
                "weight": weight, "image_url": image_url, "is_available": not in_stop,
            })

        categories.append({"name": cat_name, "display_mode": display_mode, "items": items})
        categories.extend(sub_categories)

    return {"categories": categories}


@router.post("/restaurants/{restaurant_id}/import-menu")
async def import_menu_json(restaurant_id: str, request: ImportMenuRequest, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    data = request.data
    imported_categories = 0
    imported_items = 0

    try:
        if request.mode == "replace":
            await db.menu_items.delete_many({"restaurant_id": restaurant_id})
            await db.categories.delete_many({"restaurant_id": restaurant_id})

        sections = await get_or_create_menu_sections(restaurant_id)
        section_map = {s['name'].lower(): s['id'] for s in sections}
        default_section_id = sections[0]['id'] if sections else None

        categories_data = data.get('categories', [])
        for cat_data in categories_data:
            cat_name = cat_data.get('name', '').strip()
            if not cat_name:
                continue

            section_id = default_section_id
            cat_lower = cat_name.lower()
            if any(kw in cat_lower for kw in ['напиток', 'коктейль', 'вино', 'пиво', 'виски', 'кофе', 'чай', 'сок', 'лимонад', 'бар']):
                section_id = section_map.get('напитки', default_section_id)
            elif any(kw in cat_lower for kw in ['кальян', 'табак', 'hookah']):
                section_id = section_map.get('кальяны', default_section_id)
            else:
                section_id = section_map.get('еда', default_section_id)

            existing_cat = await db.categories.find_one({"restaurant_id": restaurant_id, "name": cat_name})

            if existing_cat:
                cat_id = existing_cat['id']
            else:
                category = Category(
                    restaurant_id=restaurant_id, name=cat_name, section_id=section_id,
                    display_mode=cat_data.get('display_mode', 'card'),
                    sort_order=cat_data.get('sort_order', imported_categories),
                    is_active=cat_data.get('is_active', True)
                )
                doc = category.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.categories.insert_one(doc)
                cat_id = doc['id']
                imported_categories += 1

            items_data = cat_data.get('items', [])
            for idx, item_data in enumerate(items_data):
                item_name = item_data.get('name', '').strip()
                is_banner = item_data.get('is_banner', False)

                if not item_name and not is_banner:
                    continue

                if not is_banner:
                    existing_item = await db.menu_items.find_one({
                        "restaurant_id": restaurant_id, "category_id": cat_id, "name": item_name
                    })
                else:
                    existing_item = None

                if not existing_item:
                    item = MenuItem(
                        restaurant_id=restaurant_id, category_id=cat_id,
                        name=item_name, description=item_data.get('description', ''),
                        price=float(item_data.get('price', 0) or 0),
                        weight=item_data.get('weight', item_data.get('portion', '')),
                        image_url=item_data.get('image_url', item_data.get('image', '')),
                        is_available=item_data.get('is_available', True),
                        is_hit=item_data.get('is_hit', False),
                        is_new=item_data.get('is_new', False),
                        is_spicy=item_data.get('is_spicy', False),
                        is_banner=is_banner,
                        sort_order=item_data.get('sort_order', idx)
                    )
                    doc = item.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.menu_items.insert_one(doc)
                    imported_items += 1

        if 'items' in data and not categories_data:
            for idx, item_data in enumerate(data.get('items', [])):
                item_name = item_data.get('name', '').strip()
                cat_name = item_data.get('category', item_data.get('category_name', 'Без категории'))

                if not item_name:
                    continue

                existing_cat = await db.categories.find_one({"restaurant_id": restaurant_id, "name": cat_name})

                if existing_cat:
                    cat_id = existing_cat['id']
                else:
                    category = Category(
                        restaurant_id=restaurant_id, name=cat_name,
                        section_id=default_section_id, sort_order=imported_categories
                    )
                    doc = category.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.categories.insert_one(doc)
                    cat_id = doc['id']
                    imported_categories += 1

                existing_item = await db.menu_items.find_one({"restaurant_id": restaurant_id, "name": item_name})

                if not existing_item:
                    item = MenuItem(
                        restaurant_id=restaurant_id, category_id=cat_id,
                        name=item_name, description=item_data.get('description', ''),
                        price=float(item_data.get('price', 0)),
                        weight=item_data.get('weight', item_data.get('portion', '')),
                        image_url=item_data.get('image_url', item_data.get('image', '')),
                        is_available=item_data.get('is_available', True),
                        sort_order=idx
                    )
                    doc = item.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.menu_items.insert_one(doc)
                    imported_items += 1

        return {"message": "Импорт завершён", "imported_categories": imported_categories, "imported_items": imported_items}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {str(e)}")


@router.post("/restaurants/{restaurant_id}/import-file")
async def import_menu_file(restaurant_id: str, file: UploadFile = File(...), mode: str = Query("append"), current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)

    ext = Path(file.filename).suffix.lower()
    if ext not in {'.data', '.json'}:
        raise HTTPException(status_code=400, detail="Допустимые форматы: .data, .json")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимум 10MB")

    try:
        import json as _json
        raw = _json.loads(content.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл. Проверьте формат JSON.")

    if isinstance(raw, list):
        parsed = parse_lunchpad_data(raw)
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise HTTPException(status_code=400, detail="Неизвестный формат данных")

    request = ImportMenuRequest(data=parsed, mode=mode)
    return await import_menu_json(restaurant_id, request, current_user)
