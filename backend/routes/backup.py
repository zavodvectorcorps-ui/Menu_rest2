from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

BACKUP_DIR = os.path.dirname(os.path.dirname(__file__))

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
