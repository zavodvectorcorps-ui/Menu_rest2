from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/db-backup/download")
async def download_db_backup():
    path = os.path.join(os.path.dirname(__file__), "db_backup.tar.gz")
    if not os.path.exists(path):
        return {"error": "Backup not found"}
    return FileResponse(path, filename="db_backup.tar.gz", media_type="application/gzip")
