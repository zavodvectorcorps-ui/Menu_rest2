from datetime import datetime, timezone
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from auth import get_current_user, check_restaurant_access
from database import db

router = APIRouter()


class SplashAd(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    title: Optional[str] = ""
    text: Optional[str] = ""
    image_url: Optional[str] = ""
    button_text: Optional[str] = "Перейти к меню"
    link_text: Optional[str] = ""
    link_url: Optional[str] = ""
    fit_mode: Optional[str] = "contain"  # "contain" | "cover"
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SplashAdCreate(BaseModel):
    title: Optional[str] = ""
    text: Optional[str] = ""
    image_url: Optional[str] = ""
    button_text: Optional[str] = "Перейти к меню"
    link_text: Optional[str] = ""
    link_url: Optional[str] = ""
    fit_mode: Optional[str] = "contain"
    is_active: bool = True
    sort_order: int = 0


class SplashAdUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None
    button_text: Optional[str] = None
    link_text: Optional[str] = None
    link_url: Optional[str] = None
    fit_mode: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/restaurants/{restaurant_id}/splash-ads", response_model=List[SplashAd])
async def list_splash_ads(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    ads = await db.splash_ads.find(
        {"restaurant_id": restaurant_id}, {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    return ads


@router.post("/restaurants/{restaurant_id}/splash-ads", response_model=SplashAd)
async def create_splash_ad(restaurant_id: str, payload: SplashAdCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    ad = SplashAd(restaurant_id=restaurant_id, **payload.model_dump())
    await db.splash_ads.insert_one(ad.model_dump())
    return ad


@router.put("/restaurants/{restaurant_id}/splash-ads/{ad_id}", response_model=SplashAd)
async def update_splash_ad(restaurant_id: str, ad_id: str, payload: SplashAdUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    result = await db.splash_ads.find_one_and_update(
        {"id": ad_id, "restaurant_id": restaurant_id},
        {"$set": update},
        return_document=True,
        projection={"_id": 0},
    )
    if not result:
        raise HTTPException(404, "Заставка не найдена")
    return result


@router.delete("/restaurants/{restaurant_id}/splash-ads/{ad_id}")
async def delete_splash_ad(restaurant_id: str, ad_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.splash_ads.delete_one({"id": ad_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Заставка не найдена")
    return {"deleted": True}
