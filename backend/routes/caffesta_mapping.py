"""
Fuzzy auto-mapping of local menu items to Caffesta products (by name).
Uses rapidfuzz token_sort_ratio.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from rapidfuzz import fuzz, process as rfprocess

from auth import check_restaurant_access, get_current_user
from database import db
from services.caffesta import caffesta_get_products

router = APIRouter()


def _normalize(s: str) -> str:
    import re
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s


@router.get("/restaurants/{restaurant_id}/caffesta/auto-mapping/suggest")
async def suggest_mapping(
    restaurant_id: str,
    threshold: int = 60,
    only_unmapped: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """Return top-3 Caffesta product candidates for each menu item with score >= threshold."""
    await check_restaurant_access(current_user, restaurant_id)

    products_res = await caffesta_get_products(restaurant_id)
    if not products_res.get("ok"):
        raise HTTPException(status_code=400, detail=products_res.get("message", "Ошибка Caffesta"))
    products = products_res.get("data", [])
    if not products:
        return {"suggestions": [], "caffesta_count": 0, "menu_count": 0}

    query = {"restaurant_id": restaurant_id, "is_banner": {"$ne": True}}
    if only_unmapped:
        query["$or"] = [{"caffesta_product_id": None}, {"caffesta_product_id": {"$exists": False}}]
    items = await db.menu_items.find(query, {"_id": 0}).to_list(10000)

    # Build choice map: normalized_title -> product
    choices = {}
    for p in products:
        t = _normalize(p.get("title") or "")
        if not t:
            continue
        # If duplicate normalized name, keep first
        if t not in choices:
            choices[t] = p
    choice_keys = list(choices.keys())

    suggestions = []
    for item in items:
        name = item.get("name", "")
        if not name:
            continue
        norm = _normalize(name)
        if not norm or not choice_keys:
            continue
        # Top-3 matches
        matches = rfprocess.extract(norm, choice_keys, scorer=fuzz.token_sort_ratio, limit=3)
        candidates = []
        for match_text, score, _ in matches:
            if score < threshold:
                continue
            prod = choices[match_text]
            candidates.append({
                "product_id": prod.get("product_id"),
                "title": prod.get("title"),
                "type": prod.get("type", "product"),
                "price": prod.get("price"),
                "score": round(score),
            })
        if candidates:
            suggestions.append({
                "menu_item": {
                    "id": item["id"],
                    "name": name,
                    "current_caffesta_id": item.get("caffesta_product_id"),
                },
                "candidates": candidates,
            })

    return {
        "suggestions": suggestions,
        "caffesta_count": len(products),
        "menu_count": len(items),
        "matched_count": len(suggestions),
    }


class MappingApplyItem(BaseModel):
    menu_item_id: str
    caffesta_product_id: Optional[int]  # None = unlink


class MappingApplyRequest(BaseModel):
    mappings: List[MappingApplyItem]


@router.post("/restaurants/{restaurant_id}/caffesta/auto-mapping/apply")
async def apply_mapping(
    restaurant_id: str,
    payload: MappingApplyRequest,
    current_user: dict = Depends(get_current_user),
):
    """Batch-apply caffesta_product_id to menu items."""
    await check_restaurant_access(current_user, restaurant_id)
    updated = 0
    for m in payload.mappings:
        res = await db.menu_items.update_one(
            {"id": m.menu_item_id, "restaurant_id": restaurant_id},
            {"$set": {"caffesta_product_id": m.caffesta_product_id}},
        )
        if res.modified_count:
            updated += 1
    return {"updated": updated, "total": len(payload.mappings)}
