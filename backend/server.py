from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from database import client
from helpers import create_superadmin

from routes.auth import router as auth_router
from routes.restaurants import router as restaurants_router
from routes.menu import router as menu_router
from routes.tables import router as tables_router
from routes.orders import router as orders_router
from routes.settings import router as settings_router
from routes.public import router as public_router
from routes.telegram import router as telegram_router
from routes.caffesta import router as caffesta_router
from routes.backup import router as backup_router
from routes.seed import router as seed_router
from routes.ws import router as ws_router
from routes.faq import router as faq_router
from routes.splash import router as splash_router
from routes.cost_control import router as cost_router
from routes.cost_control import run_margin_check_job
from routes.caffesta_mapping import router as caffesta_mapping_router
from routes.digest import router as digest_router
from services.digest import run_daily_digest_job

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Restaurant Control Panel API")

# Static files
UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Include all routers under /api prefix
for r in [
    auth_router, restaurants_router, menu_router, tables_router,
    orders_router, settings_router, public_router, telegram_router,
    caffesta_router, backup_router, seed_router, ws_router, faq_router, splash_router, cost_router,
    caffesta_mapping_router, digest_router,
]:
    app.include_router(r, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


scheduler: AsyncIOScheduler = None


@app.on_event("startup")
async def startup():
    global scheduler
    logging.info("Starting up...")
    await create_superadmin()
    # Daily digest at 10:00 Minsk time (UTC+3)
    try:
        scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Minsk"))
        scheduler.add_job(run_daily_digest_job, CronTrigger(hour=10, minute=0), id="daily_digest", replace_existing=True)
        scheduler.add_job(run_margin_check_job, CronTrigger(hour=10, minute=5), id="margin_check", replace_existing=True)
        scheduler.start()
        logging.info("Scheduler started (digest 10:00, margin-check 10:05 Europe/Minsk)")
    except Exception as e:
        logging.exception(f"Scheduler failed to start (continuing without daily digest): {e}")
        scheduler = None


@app.on_event("shutdown")
async def shutdown():
    global scheduler
    logging.info("Shutting down...")
    if scheduler:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
    client.close()
