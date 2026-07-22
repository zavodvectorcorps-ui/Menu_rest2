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
from services.translation import (
    translate_ru_to, translate_ru_to_strict,
    translate_ru_to_en_strict, get_cache_stats, SUPPORTED_LANGS,
    purge_translations,
)

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

router = APIRouter()


# ============ Background translation helpers ============

async def _restaurant_languages(restaurant_id: str) -> list[str]:
    """Return list of target languages enabled for this restaurant.
    Defaults to ['en'] for backwards compat (legacy field absent)."""
    r = await db.restaurants.find_one(
        {"id": restaurant_id},
        {"_id": 0, "enabled_languages": 1},
    )
    langs = (r or {}).get("enabled_languages")
    if not langs:
        return ["en"]
    return [lc for lc in langs if lc in SUPPORTED_LANGS]


async def _translate_menu_item_bg(item_id: str, name: str, description: str, restaurant_id: str = ""):
    langs = await _restaurant_languages(restaurant_id) if restaurant_id else ["en"]
    update = {}
    for lang in langs:
        if name:
            tr = await translate_ru_to(name, lang)
            if tr:
                update[f"name_{lang}"] = tr
        if description:
            tr = await translate_ru_to(description, lang)
            if tr:
                update[f"description_{lang}"] = tr
    if update:
        await db.menu_items.update_one({"id": item_id}, {"$set": update})


async def _translate_category_bg(category_id: str, name: str, restaurant_id: str = ""):
    if not name:
        return
    langs = await _restaurant_languages(restaurant_id) if restaurant_id else ["en"]
    update = {}
    for lang in langs:
        tr = await translate_ru_to(name, lang)
        if tr:
            update[f"name_{lang}"] = tr
    if update:
        await db.categories.update_one({"id": category_id}, {"$set": update})


async def _translate_categories_batch_bg(queue: list, restaurant_id: str = ""):
    """
    Последовательно переводит список (cat_id, name).
    Между категориями делается короткая пауза, чтобы не залпом дёргать LLM.
    """
    import asyncio
    for cat_id, name in queue:
        try:
            await _translate_category_bg(cat_id, name, restaurant_id)
        except Exception:
            # Один сбой не должен останавливать остальные
            pass
        await asyncio.sleep(0.2)


async def _translate_section_bg(section_id: str, name: str, restaurant_id: str = ""):
    if not name:
        return
    langs = await _restaurant_languages(restaurant_id) if restaurant_id else ["en"]
    update = {}
    for lang in langs:
        tr = await translate_ru_to(name, lang)
        if tr:
            update[f"name_{lang}"] = tr
    if update:
        await db.menu_sections.update_one({"id": section_id}, {"$set": update})


# ============ MENU SECTIONS ============

@router.get("/restaurants/{restaurant_id}/menu-sections")
async def get_menu_sections(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_menu_sections(restaurant_id)


@router.post("/restaurants/{restaurant_id}/menu-sections")
async def create_menu_section(restaurant_id: str, data: MenuSectionCreate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    section = MenuSection(restaurant_id=restaurant_id, **data.model_dump())
    doc = section.model_dump()
    await db.menu_sections.insert_one(doc)
    doc.pop('_id', None)
    background_tasks.add_task(_translate_section_bg, doc['id'], doc.get('name', ''), restaurant_id)
    return doc


@router.put("/restaurants/{restaurant_id}/menu-sections/{section_id}")
async def update_menu_section(restaurant_id: str, section_id: str, data: MenuSectionCreate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    # Reset all language translations on every edit so background task re-translates fresh
    payload = data.model_dump()
    payload['name_en'] = ''
    payload['name_zh'] = ''
    result = await db.menu_sections.update_one({"id": section_id, "restaurant_id": restaurant_id}, {"$set": payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    background_tasks.add_task(_translate_section_bg, section_id, payload.get('name', ''), restaurant_id)
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
async def create_category(restaurant_id: str, data: CategoryCreate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    category = Category(restaurant_id=restaurant_id, **data.model_dump())
    doc = category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    doc.pop('_id', None)
    background_tasks.add_task(_translate_category_bg, doc['id'], doc.get('name', ''), restaurant_id)
    return doc


@router.put("/restaurants/{restaurant_id}/categories/{category_id}")
async def update_category(restaurant_id: str, category_id: str, data: CategoryUpdate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        # Reset all language translations so next request re-translates
        if 'name' in update_data:
            update_data['name_en'] = ''
            update_data['name_zh'] = ''
        result = await db.categories.update_one({"id": category_id, "restaurant_id": restaurant_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        if 'name' in update_data:
            background_tasks.add_task(_translate_category_bg, category_id, update_data['name'], restaurant_id)
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


@router.post("/restaurants/{restaurant_id}/categories/bulk-rename")
async def bulk_rename_categories(
    restaurant_id: str,
    renames: List[dict],
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Массовое переименование категорий. Принимает список [{id, name}].
    Имена тримятся, пустые игнорируются. Для каждой изменённой категории
    сбрасываются переводы (name_en, name_zh) и ставится ОДНА фоновая
    задача, которая последовательно переводит все обновлённые категории
    (с небольшой задержкой между запросами, чтобы не перегружать LLM API).
    """
    await check_restaurant_access(current_user, restaurant_id)
    updated = 0
    skipped = 0
    translation_queue: list[tuple[str, str]] = []  # (cat_id, name)
    for entry in renames:
        cat_id = (entry or {}).get("id")
        new_name = ((entry or {}).get("name") or "").strip()
        if not cat_id or not new_name:
            skipped += 1
            continue
        result = await db.categories.update_one(
            {"id": cat_id, "restaurant_id": restaurant_id},
            {"$set": {"name": new_name, "name_en": "", "name_zh": ""}},
        )
        if result.matched_count:
            updated += 1
            translation_queue.append((cat_id, new_name))
        else:
            skipped += 1

    if translation_queue:
        background_tasks.add_task(
            _translate_categories_batch_bg, translation_queue, restaurant_id
        )
    return {"updated": updated, "skipped": skipped}


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
async def create_menu_item(restaurant_id: str, data: MenuItemCreate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    item = MenuItem(restaurant_id=restaurant_id, **data.model_dump())
    doc = item.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_items.insert_one(doc)
    doc.pop('_id', None)
    background_tasks.add_task(
        _translate_menu_item_bg, doc['id'], doc.get('name', ''), doc.get('description', ''), restaurant_id
    )
    return doc


@router.put("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def update_menu_item(restaurant_id: str, item_id: str, data: MenuItemUpdate, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    # Reset all language translations if the RU text changed — caller may edit only one
    if 'name' in update_data:
        update_data['name_en'] = ''
        update_data['name_zh'] = ''
    if 'description' in update_data:
        update_data['description_en'] = ''
        update_data['description_zh'] = ''
    if update_data:
        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": update_data})
    # If price changed, re-evaluate margin alerts for this restaurant
    if "price" in update_data:
        try:
            from routes.cost_control import _send_margin_alerts
            await _send_margin_alerts(restaurant_id)
        except Exception:
            pass
    if 'name' in update_data or 'description' in update_data:
        background_tasks.add_task(
            _translate_menu_item_bg,
            item_id,
            update_data.get('name', ''),
            update_data.get('description', ''),
            restaurant_id,
        )
    return await db.menu_items.find_one({"id": item_id}, {"_id": 0})


@router.delete("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def delete_menu_item(restaurant_id: str, item_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_items.delete_one({"id": item_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}


@router.post("/restaurants/{restaurant_id}/menu-items/nutrition-import")
async def import_nutrition_docx(
    restaurant_id: str,
    file: UploadFile = File(...),
    dry_run: bool = True,
    apply_ids: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Импорт значений БЖУ (Белки/Жиры/Углеводы/ккал/кДж на 100 г) из .docx
    файла в существующие блюда меню. Матчинг по имени через RapidFuzz.

    Параметры:
      - dry_run=True (default): возвращает preview matched/ambiguous/unmatched
        без записи в БД.
      - dry_run=False: применяет обновления для matched-записей.
        Если задан apply_ids (csv строка item_id), обновление ограничивается
        этим списком (используется когда пользователь снял галку с некоторых
        строк в preview UI).

    Возвращает:
      {
        "matched":    [{source, item_id, item_name, score, values}],
        "ambiguous":  [{source, candidates: [...], values}],
        "unmatched":  [{source, values, best_score}],
        "records_total": int,
        "applied": int  # only when dry_run=False
      }
    """
    from services.nutrition_import import parse_docx_nutrition, match_records_to_items

    await check_restaurant_access(current_user, restaurant_id)

    filename = (file.filename or "").lower()
    if not filename.endswith(".docx"):
        raise HTTPException(400, "Ожидается .docx файл")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "Пустой файл")

    try:
        records = parse_docx_nutrition(file_bytes)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Не удалось разобрать docx: {exc}")

    if not records:
        raise HTTPException(400, "В файле не найдено ни одной строки с БЖУ")

    items_cursor = db.menu_items.find(
        {"restaurant_id": restaurant_id, "is_banner": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1},
    )
    items = await items_cursor.to_list(length=5000)

    match_result = match_records_to_items(records, items)

    if dry_run:
        return {**match_result, "records_total": len(records), "applied": 0}

    # apply mode: обновляем matched, опционально фильтруя по apply_ids
    allowed_ids: Optional[set] = None
    if apply_ids:
        allowed_ids = {aid.strip() for aid in apply_ids.split(",") if aid.strip()}

    applied = 0
    skipped = 0
    for m in match_result["matched"]:
        if allowed_ids is not None and m["item_id"] not in allowed_ids:
            skipped += 1
            continue
        v = m["values"]
        update = {
            "nutrition_protein": v.get("protein"),
            "nutrition_fat": v.get("fat"),
            "nutrition_carbs": v.get("carbs"),
            "nutrition_kcal": v.get("kcal"),
            "nutrition_kj": v.get("kj"),
        }
        # Не перетираем существующее значение на None (если строка пришла без числа)
        update = {k: val for k, val in update.items() if val is not None}
        if update:
            result = await db.menu_items.update_one(
                {"id": m["item_id"], "restaurant_id": restaurant_id},
                {"$set": update},
            )
            if result.matched_count:
                applied += 1

    return {**match_result, "records_total": len(records), "applied": applied, "skipped": skipped}


@router.post("/restaurants/{restaurant_id}/menu-items/reorder")
async def reorder_items(restaurant_id: str, order: List[str], current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    for idx, item_id in enumerate(order):        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": {"sort_order": idx}})
    return {"message": "Reordered"}


# ============ I18N / BULK TRANSLATION ============

@router.get("/translation-status")
async def translation_status(current_user: dict = Depends(get_current_user)):
    """Diagnostic endpoint — checks whether the AI translation pipeline
    is configured correctly. Useful when «Перевести меню» fails on prod:
    user can curl this to see the precise error.
    """
    import os
    out = {
        "key_present": bool(os.environ.get("EMERGENT_LLM_KEY")),
        "key_prefix": (os.environ.get("EMERGENT_LLM_KEY") or "")[:14] + "..." if os.environ.get("EMERGENT_LLM_KEY") else None,
        "smoke_test": None,
        "error": None,
    }
    if not out["key_present"]:
        out["error"] = "EMERGENT_LLM_KEY is not set in backend env. Add it to backend/.env or docker-compose.yml."
        return out
    try:
        result = await translate_ru_to_en_strict("Привет", use_cache=False)
        out["smoke_test"] = result
        if not result:
            out["error"] = "LLM returned empty response (possibly out of credits)"
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


@router.get("/translation-cache-stats")
async def translation_cache_stats(current_user: dict = Depends(get_current_user)):
    """Cache hit/miss diagnostic. Lets the admin see how many translations
    are served from cache vs the LLM."""
    return await get_cache_stats()


@router.post("/restaurants/{restaurant_id}/purge-translations")
async def purge_restaurant_translations(
    restaurant_id: str,
    lang: str,
    current_user: dict = Depends(get_current_user),
):
    """Clear all translations for `lang` on this restaurant — useful when the
    LLM produced contaminated results (CoT leakage, residual Russian text).
    The user can then re-run bulk translation from a clean slate."""
    await check_restaurant_access(current_user, restaurant_id)
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail=f"Unknown language: {lang}")
    counts = await purge_translations(restaurant_id, lang)
    return {"message": f"Очищены переводы для {lang.upper()}", "cleared": counts}


@router.post("/restaurants/{restaurant_id}/translate-all")
async def translate_all_menu(
    restaurant_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    lang: str = "all",
    current_user: dict = Depends(get_current_user),
):
    """Kick off a background job that translates sections, categories and items
    of a restaurant. Returns immediately with the count of items that will be
    processed.

    Query params:
    - `force=true` — re-translate everything (otherwise skip already-translated)
    - `lang=en|zh|all` — target language(s). `all` = every language enabled
      on the restaurant (`enabled_languages`). Defaults to `all`.
    """
    await check_restaurant_access(current_user, restaurant_id)

    # 1. Pre-flight: verify the AI key is available.
    import os
    if not os.environ.get("EMERGENT_LLM_KEY"):
        raise HTTPException(
            status_code=400,
            detail=(
                "AI-перевод недоступен: EMERGENT_LLM_KEY не задан в backend/.env "
                "на сервере. Получите ключ в Emergent → Profile → Universal Key, "
                "пропишите его в .env, перезапустите backend и попробуйте снова."
            ),
        )

    # 2. Resolve target languages
    enabled = await _restaurant_languages(restaurant_id)
    if lang == "all":
        targets = enabled or ["en"]
    elif lang in SUPPORTED_LANGS:
        if lang not in enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Язык '{lang}' не активирован для этого ресторана. Включите его в Настройки → Языки.",
            )
        targets = [lang]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown language: {lang}")

    # 3. Smoke-test EACH target language so misconfigured prompts don't waste a long job.
    for target in targets:
        try:
            smoke = await translate_ru_to_strict("Тест", target, use_cache=False)
            if not smoke:
                raise HTTPException(
                    status_code=502,
                    detail=f"AI-перевод ({target}) вернул пустой ответ. Проверьте баланс ключа.",
                )
        except HTTPException:
            raise
        except Exception as e:
            err_text = str(e) or repr(e)
            raise HTTPException(
                status_code=502,
                detail=(
                    f"AI-перевод ({target}) недоступен. Подробности: {err_text}\n\n"
                    "Возможные причины:\n"
                    "• Регион запрещён провайдером LLM (попробуйте VPS в EU/US или прокси).\n"
                    "• Истёк баланс ключа — Emergent → Profile → Universal Key → Add Balance.\n"
                    "• Backend-контейнер не имеет выхода в интернет — проверьте `docker compose logs backend`.\n"
                    "• Неверный ключ — сверьте значение `EMERGENT_LLM_KEY` в backend/.env."
                ),
            )

    # 4. Build the filters once to report an estimate (use first target for the missing-check;
    # union semantics would be confusing). For "force" — count all docs.
    if force:
        q_filter = {"restaurant_id": restaurant_id}
        sect_count = await db.menu_sections.count_documents(q_filter)
        cat_count = await db.categories.count_documents(q_filter)
        item_count = await db.menu_items.count_documents(q_filter)
    else:
        # Items missing translation in ANY of the target languages
        name_missing = {"$or": [
            cond
            for t in targets
            for cond in ({f"name_{t}": {"$exists": False}}, {f"name_{t}": ""})
        ]}
        item_missing = {"$or": [
            cond
            for t in targets
            for cond in (
                {f"name_{t}": {"$exists": False}}, {f"name_{t}": ""},
                {f"description_{t}": {"$exists": False}}, {f"description_{t}": ""},
            )
        ]}
        base = {"restaurant_id": restaurant_id}
        sect_count = await db.menu_sections.count_documents({**base, **name_missing})
        cat_count = await db.categories.count_documents({**base, **name_missing})
        item_count = await db.menu_items.count_documents({**base, **item_missing})

    background_tasks.add_task(_bulk_translate_restaurant, restaurant_id, force, targets,
                              {"sections": sect_count, "categories": cat_count, "items": item_count})
    return {
        "message": "Translation started in background",
        "languages": targets,
        "estimate": {"sections": sect_count, "categories": cat_count, "items": item_count},
    }


@router.get("/restaurants/{restaurant_id}/translate-status")
async def get_translate_status(
    restaurant_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the latest translation job for this restaurant. Used by the
    admin UI to render a progress bar while bulk translation runs."""
    await check_restaurant_access(current_user, restaurant_id)
    job = await db.translation_jobs.find_one(
        {"restaurant_id": restaurant_id},
        {"_id": 0},
        sort=[("started_at", -1)],
    )
    return job or {"status": "idle"}


async def _bulk_translate_restaurant(restaurant_id: str, force: bool, targets: list[str], totals: dict):
    """Long-running worker. Writes incremental progress to `translation_jobs`
    so the admin UI can poll and render a progress bar.

    Yields to the event loop between items so other HTTP requests keep serving."""
    import logging
    import asyncio
    import uuid
    from datetime import datetime, timezone
    log = logging.getLogger(__name__)
    job_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    total_planned = (totals.get("sections", 0) + totals.get("categories", 0) + totals.get("items", 0))

    # Initial job doc — picked up immediately by the polling UI
    await db.translation_jobs.insert_one({
        "id": job_id,
        "restaurant_id": restaurant_id,
        "languages": targets,
        "force": force,
        "status": "running",
        "phase": "sections",
        "total": total_planned,
        "totals": totals,
        "done": 0,
        "stats": {"sections": 0, "categories": 0, "items": 0},
        "started_at": started_at,
        "finished_at": None,
        "error": None,
    })

    stats = {"sections": 0, "categories": 0, "items": 0}
    done = 0

    async def bump(phase: str):
        nonlocal done
        done += 1
        stats[phase] += 1
        # Update every doc — cheap (small collection, single query)
        await db.translation_jobs.update_one(
            {"id": job_id},
            {"$set": {"phase": phase, "done": done, "stats": stats}},
        )

    try:
        # Sections
        async for s in db.menu_sections.find({"restaurant_id": restaurant_id}, {"_id": 0, "id": 1, "name": 1, "name_en": 1, "name_zh": 1}):
            if not s.get('name'):
                continue
            update = {}
            for t in targets:
                field = f"name_{t}"
                if force or not s.get(field):
                    tr = await translate_ru_to(s['name'], t)
                    if tr:
                        update[field] = tr
            if update:
                await db.menu_sections.update_one({"id": s['id']}, {"$set": update})
            await bump("sections")
            await asyncio.sleep(0.05)

        # Categories
        async for c in db.categories.find({"restaurant_id": restaurant_id}, {"_id": 0, "id": 1, "name": 1, "name_en": 1, "name_zh": 1}):
            if not c.get('name'):
                continue
            update = {}
            for t in targets:
                field = f"name_{t}"
                if force or not c.get(field):
                    tr = await translate_ru_to(c['name'], t)
                    if tr:
                        update[field] = tr
            if update:
                await db.categories.update_one({"id": c['id']}, {"$set": update})
            await bump("categories")
            await asyncio.sleep(0.05)

        # Items
        proj = {"_id": 0, "id": 1, "name": 1, "description": 1,
                "name_en": 1, "description_en": 1, "name_zh": 1, "description_zh": 1}
        async for it in db.menu_items.find({"restaurant_id": restaurant_id}, proj):
            update = {}
            for t in targets:
                n_field, d_field = f"name_{t}", f"description_{t}"
                if (force or not it.get(n_field)) and it.get('name'):
                    tr = await translate_ru_to(it['name'], t)
                    if tr:
                        update[n_field] = tr
                if (force or not it.get(d_field)) and it.get('description'):
                    tr = await translate_ru_to(it['description'], t)
                    if tr:
                        update[d_field] = tr
            if update:
                await db.menu_items.update_one({"id": it['id']}, {"$set": update})
            await bump("items")
            await asyncio.sleep(0.1)

        await db.translation_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "done",
                "phase": "done",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        log.info("translate-all finished for %s (langs=%s): %s", restaurant_id, targets, stats)
    except Exception as e:
        await db.translation_jobs.update_one(
            {"id": job_id},
            {"$set": {
                "status": "error",
                "error": f"{type(e).__name__}: {e}",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        log.exception("translate-all failed for %s", restaurant_id)


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


def _parse_lunchpad_price(prices_raw):
    """Возвращает (price: float, weight: str). Поддерживает первое валидное значение из массива prices."""
    price = 0.0
    weight = ""
    if not prices_raw:
        return price, weight
    p = prices_raw[0] or {}
    raw_price = p.get("price", 0)
    if isinstance(raw_price, (int, float)):
        price = float(raw_price)
    elif isinstance(raw_price, str):
        cleaned = raw_price.replace(',', '.').strip()
        match = _re.search(r'[\d]+[.]?[\d]*', cleaned)
        if match:
            try:
                price = float(match.group())
            except ValueError:
                price = 0.0
    weight = p.get("measure", "") or ""
    return price, weight


def _parse_lunchpad_dish(item: dict) -> dict:
    """Преобразует Lunchpad-объект type=4 в dict нашего MenuItem."""
    name = strip_html(item.get("name", "")).strip()
    desc = strip_html(item.get("description", ""))
    price, weight = _parse_lunchpad_price(item.get("prices", []))
    foto = item.get("foto", {}) or {}
    image_url = foto.get("image_url", "") or ""
    return {
        "name": name,
        "description": desc,
        "price": price,
        "weight": weight,
        "image_url": image_url,
        "is_available": not item.get("in_stop_list", False),
    }


def _parse_lunchpad_banner(item: dict) -> dict | None:
    """type=2 → баннер. Возвращает None, если у баннера нет картинки."""
    foto = item.get("foto", {}) or {}
    img = foto.get("image_url", "") or ""
    if not img:
        return None
    bn = strip_html(item.get("name", "")).strip()
    if bn == "--":
        bn = ""
    return {
        "name": bn,
        "description": strip_html(item.get("description", "")),
        "image_url": img,
        "is_banner": True,
        "price": 0,
    }


def _walk_lunchpad_items(items_raw: list, parent_path: str, parent_display: str):
    """
    Рекурсивно обходит дерево Lunchpad-items.

    Lunchpad-экспорт хранит до 3 уровней вложенности:
      cat (type=0) → subcat (type=0) → sub-subcat (type=0) → dish (type=4)

    Эта функция сплющивает дерево в плоский список категорий (наша БД-модель —
    одноуровневая «категория → блюда»). Каждый «лист»-узел (узел type=0,
    у которого среди детей есть type=4 или баннеры) превращается в отдельную
    категорию с конкатенированным именем вида "Родитель — Дитя — Внук".

    Возвращает (dishes_at_this_level, list_of_flattened_subcats):
      • dishes_at_this_level — type=4 и баннеры (type=2 с картинкой) текущего уровня
      • list_of_flattened_subcats — все вложенные категории, уже сплющенные
    """
    dishes = []
    subcats = []
    for item in items_raw or []:
        t = item.get("type")
        if t == 2:
            banner = _parse_lunchpad_banner(item)
            if banner:
                dishes.append(banner)
            continue
        if t == 4:
            d = _parse_lunchpad_dish(item)
            if d["name"]:
                dishes.append(d)
            continue
        if t == 0:
            sub_name = strip_html(item.get("name", "")).strip()
            if not sub_name:
                continue
            sub_display = item.get("display", "") or parent_display
            sub_display_mode = "compact" if sub_display == "list" else "card"
            full_name = f"{parent_path} — {sub_name}"
            child_dishes, child_subcats = _walk_lunchpad_items(
                item.get("items", []), full_name, sub_display
            )
            if child_dishes:
                subcats.append({
                    "name": full_name,
                    "display_mode": sub_display_mode,
                    "items": child_dishes,
                })
            subcats.extend(child_subcats)
            continue
        # type=1 и прочие — игнорируем (это инфо-блоки типа «Оставить отзыв»)
    return dishes, subcats


def parse_lunchpad_data(raw_data: list) -> dict:
    categories = []
    pending_banners = []

    for entry in raw_data:
        entry_type = entry.get("type")

        if entry_type == 2:
            banner = _parse_lunchpad_banner(entry)
            if banner:
                pending_banners.append(banner)
            continue

        if entry_type != 0:
            continue

        cat_name = strip_html(entry.get("name", "")).strip()
        if not cat_name:
            continue

        display = entry.get("display", "")
        display_mode = "compact" if display == "list" else "card"

        # Рекурсивно собираем все блюда + вложенные подкатегории (до 3-х уровней)
        own_dishes, nested_subcats = _walk_lunchpad_items(
            entry.get("items", []), cat_name, display
        )

        items = list(pending_banners) + own_dishes
        pending_banners = []

        # Пропускаем «оболочечные» категории без собственного содержимого
        # (например, «Барное меню» — все её позиции уехали во вложенные
        # категории «Барное меню — Пиво» и т.п.). Если хотя бы один баннер
        # или блюдо есть — категорию создаём.
        if items:
            categories.append({
                "name": cat_name,
                "display_mode": display_mode,
                "items": items,
            })
        categories.extend(nested_subcats)

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
