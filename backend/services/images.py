import logging
import uuid
import asyncio
import httpx
from pathlib import Path

from database import db

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


async def download_and_save_image(image_url: str) -> str:
    if not image_url or not image_url.startswith("http"):
        return image_url
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(image_url)
            if resp.status_code != 200:
                return image_url

            content_type = resp.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            else:
                ext = ".jpg"

            filename = f"{uuid.uuid4()}{ext}"
            filepath = UPLOADS_DIR / filename
            with open(filepath, "wb") as f:
                f.write(resp.content)

            return f"/api/uploads/{filename}"
    except Exception as e:
        logging.error(f"Image download failed for {image_url}: {e}")
        return image_url


async def download_and_update_item(restaurant_id: str, item: dict) -> bool:
    try:
        old_url = item["image_url"]
        new_url = await download_and_save_image(old_url)
        if new_url != old_url:
            await db.menu_items.update_one(
                {"id": item["id"], "restaurant_id": restaurant_id},
                {"$set": {"image_url": new_url}}
            )
            return True
        return False
    except Exception:
        return False


async def download_images_task(restaurant_id: str, items: list):
    downloaded = 0
    failed = 0
    batch_size = 10
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        tasks = [download_and_update_item(restaurant_id, item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                downloaded += 1
            else:
                failed += 1
    logging.info(f"Image download complete for {restaurant_id}: {downloaded} ok, {failed} failed")
