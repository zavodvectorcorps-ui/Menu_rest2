"""
Image-to-video generation via fal.ai (Kling 2.5 Pro image-to-video).

Public functions:
    submit_image_to_video(image_url, prompt, duration) -> request_id
    check_status(request_id)                          -> dict {status, video_url?}

Uses fal_client's async queue API. Все запросы async. Ключ читается из
переменной окружения FAL_KEY (стандарт fal.ai SDK).
"""
import os
import asyncio
import uuid
from pathlib import Path
from typing import Optional

import httpx
import fal_client

# Кластерная модель в fal.ai. Обновляется когда fal.ai выпускает новую версию.
FAL_MODEL = "fal-ai/kling-video/v2.5-turbo/pro/image-to-video"

# Локальная директория для сохранения готовых mp4 (та же, что и обычные uploads).
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"


async def submit_image_to_video(
    image_url: str,
    prompt: str,
    duration: str = "5",
) -> str:
    """
    Отправить задачу на генерацию видео. Возвращает request_id.
    duration — "5" или "10" (в секундах).
    """
    if not os.environ.get("FAL_KEY"):
        raise RuntimeError("FAL_KEY not configured on backend")

    handler = await fal_client.submit_async(
        FAL_MODEL,
        arguments={
            "prompt": prompt or "smooth cinematic camera rotation around subject",
            "image_url": image_url,
            "duration": duration,
        },
    )
    return handler.request_id


async def check_status(request_id: str) -> dict:
    """
    Проверить статус задачи и, если готова, скачать mp4 локально.

    Возвращает:
      {"status": "queued"|"in_progress"|"completed"|"failed",
       "video_url": "/api/uploads/<uuid>.mp4"?,
       "error": str?}
    """
    try:
        status = await fal_client.status_async(FAL_MODEL, request_id, with_logs=False)
    except Exception as exc:
        return {"status": "failed", "error": f"status check error: {exc}"}
    kind = type(status).__name__

    if kind == "Queued":
        return {"status": "queued"}
    if kind == "InProgress":
        return {"status": "in_progress"}
    if kind != "Completed":
        return {"status": "failed", "error": f"Unknown status: {kind}"}

    # Completed — забираем результат
    try:
        result = await fal_client.result_async(FAL_MODEL, request_id)
    except Exception as exc:
        return {"status": "failed", "error": f"fal.ai result error: {exc}"}
    video_info = (result or {}).get("video")
    remote_url = (video_info or {}).get("url") if isinstance(video_info, dict) else None
    if not remote_url:
        return {"status": "failed", "error": "no video in fal.ai result"}

    # Скачиваем себе
    local_name = f"{uuid.uuid4()}.mp4"
    local_path = UPLOADS_DIR / local_name
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(remote_url)
        resp.raise_for_status()
        local_path.write_bytes(resp.content)

    return {"status": "completed", "video_url": f"/api/uploads/{local_name}"}
