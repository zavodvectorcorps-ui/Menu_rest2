import io
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import bson
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from auth import require_superadmin
from database import db

router = APIRouter()

BACKUP_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOADS_DIR = Path(BACKUP_DIR) / "uploads"


# ============ LEGACY (pre-built tarballs, kept for backward compat) ============
@router.get("/db-backup/download")
async def download_db_backup():
    path = os.path.join(BACKUP_DIR, "db_backup.tar.gz")
    if not os.path.exists(path):
        return {"error": "Backup not found"}
    return FileResponse(path, filename="db_backup.tar.gz", media_type="application/gzip")


@router.get("/uploads-backup/download")
async def download_uploads_backup():
    path = os.path.join(BACKUP_DIR, "uploads_backup.tar.gz")
    if not os.path.exists(path):
        return {"error": "Uploads backup not found"}
    return FileResponse(path, filename="uploads_backup.tar.gz", media_type="application/gzip")


# ============ ON-DEMAND BACKUP (admin button) ============
@router.post("/admin/backup/database")
async def admin_create_db_backup(_: dict = Depends(require_superadmin)):
    """Создаёт BSON-дамп всех коллекций MongoDB на лету и отдаёт как .tar.gz"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        collections = await db.list_collection_names()
        for coll_name in collections:
            docs = await db[coll_name].find({}).to_list(None)
            data = b"".join(bson.encode(doc) for doc in docs)
            info = tarfile.TarInfo(name=f"dump/{coll_name}.bson")
            info.size = len(data)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="db_backup_{ts}.tar.gz"',
            "X-Backup-Size": str(len(buf.getvalue())),
        },
    )


@router.post("/admin/backup/uploads")
async def admin_create_uploads_backup(_: dict = Depends(require_superadmin)):
    """Архивирует папку uploads/ на лету и отдаёт как .tar.gz"""
    if not UPLOADS_DIR.exists():
        raise HTTPException(404, "Папка uploads не найдена")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(UPLOADS_DIR, arcname="uploads")
    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buf,
        media_type="application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="uploads_backup_{ts}.tar.gz"',
            "X-Backup-Size": str(len(buf.getvalue())),
        },
    )


@router.get("/admin/backup/info")
async def admin_backup_info(_: dict = Depends(require_superadmin)):
    """Возвращает количество документов и общий размер uploads."""
    collections = await db.list_collection_names()
    counts = {}
    total_docs = 0
    for c in collections:
        n = await db[c].count_documents({})
        counts[c] = n
        total_docs += n

    uploads_size = 0
    uploads_count = 0
    if UPLOADS_DIR.exists():
        for p in UPLOADS_DIR.iterdir():
            if p.is_file():
                uploads_count += 1
                uploads_size += p.stat().st_size

    return {
        "total_documents": total_docs,
        "collections": counts,
        "uploads_count": uploads_count,
        "uploads_size_bytes": uploads_size,
        "uploads_size_mb": round(uploads_size / (1024 * 1024), 1),
    }
