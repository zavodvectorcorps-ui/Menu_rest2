"""
Endpoints for daily Caffesta Telegram digest:
- Preview the digest text for now
- Manually trigger send (for testing)
- Scheduler is registered globally in server.py lifespan.
"""
from fastapi import APIRouter, Depends, HTTPException

from auth import check_restaurant_access, get_current_user
from services.digest import build_digest_text, send_daily_digest

router = APIRouter()


@router.get("/restaurants/{restaurant_id}/digest/preview")
async def digest_preview(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    try:
        text = await build_digest_text(restaurant_id)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restaurants/{restaurant_id}/digest/send")
async def digest_send(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    """Force-send digest now (ignores daily_digest_enabled, but still needs creds)."""
    await check_restaurant_access(current_user, restaurant_id)
    result = await send_daily_digest(restaurant_id, force=True)
    if not result.get("sent"):
        raise HTTPException(400, f"Не отправлено: {result.get('reason')}")
    return {"sent": True}
