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
from routes.seed import router as seed_router
from routes.ws import router as ws_router

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
    seed_router, ws_router,
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


@app.on_event("startup")
async def startup():
    logging.info("Starting up...")
    await create_superadmin()


@app.on_event("shutdown")
async def shutdown():
    logging.info("Shutting down...")
    client.close()
