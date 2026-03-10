from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from enum import Enum
import qrcode
from io import BytesIO
import base64
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# JWT Settings
SECRET_KEY = os.environ.get('JWT_SECRET', secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Create the main app
app = FastAPI(title="Restaurant Dashboard API")
app.mount("/api/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
api_router = APIRouter(prefix="/api")

# ============ ENUMS ============
class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    MANAGER = "manager"

class OrderStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class StaffCallStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"

# ============ MODELS ============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str
    role: UserRole = UserRole.MANAGER
    restaurant_ids: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.MANAGER
    restaurant_ids: List[str] = []

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    restaurant_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class Restaurant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    logo_url: Optional[str] = ""
    working_hours: Optional[str] = ""
    slogan: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RestaurantCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    working_hours: Optional[str] = None
    slogan: Optional[str] = None

class MenuSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    name: str
    sort_order: int = 0
    is_active: bool = True

class MenuSectionCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    name: str
    section_id: Optional[str] = None
    display_mode: str = "card"
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    section_id: Optional[str] = None
    display_mode: str = "card"
    sort_order: int = 0
    is_active: bool = True

class MenuItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    category_id: str
    name: str
    description: Optional[str] = ""
    price: float = 0
    weight: Optional[str] = ""
    image_url: Optional[str] = ""
    is_available: bool = True
    is_business_lunch: bool = False
    is_promotion: bool = False
    is_hit: bool = False
    is_new: bool = False
    is_spicy: bool = False
    is_banner: bool = False
    sort_order: int = 0
    label_ids: list = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MenuItemCreate(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = ""
    price: float = 0
    weight: Optional[str] = ""
    image_url: Optional[str] = ""
    is_available: bool = True
    is_business_lunch: bool = False
    is_promotion: bool = False
    is_hit: bool = False
    is_new: bool = False
    is_spicy: bool = False
    is_banner: bool = False
    sort_order: int = 0
    label_ids: list = []

class MenuItemUpdate(BaseModel):
    category_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    weight: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None
    is_business_lunch: Optional[bool] = None
    is_promotion: Optional[bool] = None
    is_hit: Optional[bool] = None
    is_new: Optional[bool] = None
    is_spicy: Optional[bool] = None
    is_banner: Optional[bool] = None
    sort_order: Optional[int] = None
    label_ids: Optional[list] = None

class Label(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    name: str
    color: str = "#ef4444"
    sort_order: int = 0

class LabelCreate(BaseModel):
    name: str
    color: str = "#ef4444"

class LabelUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class Table(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    number: int
    code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    name: Optional[str] = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TableCreate(BaseModel):
    number: int
    name: Optional[str] = ""
    is_active: bool = True

class OrderItem(BaseModel):
    menu_item_id: str
    name: str
    quantity: int
    price: float

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    table_id: str
    table_number: int
    items: List[OrderItem]
    total: float
    status: OrderStatus = OrderStatus.NEW
    notes: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    table_code: str
    items: List[OrderItem]
    notes: Optional[str] = ""

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class CallType(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    name: str
    telegram_message: str = ""
    sort_order: int = 0
    is_active: bool = True

class CallTypeCreate(BaseModel):
    name: str
    telegram_message: str = ""
    sort_order: int = 0
    is_active: bool = True

class StaffCall(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    table_id: str
    table_number: int
    call_type_id: Optional[str] = None
    call_type_name: Optional[str] = None
    status: StaffCallStatus = StaffCallStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StaffCallCreate(BaseModel):
    table_code: str
    call_type_id: Optional[str] = None

class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    name: str
    role: str
    telegram_id: Optional[str] = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployeeCreate(BaseModel):
    name: str
    role: str
    telegram_id: Optional[str] = ""
    is_active: bool = True

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    online_menu_enabled: bool = True
    staff_call_enabled: bool = True
    online_orders_enabled: bool = True
    business_lunch_enabled: bool = True
    promotions_enabled: bool = True
    theme: str = "light"
    primary_color: str = "#5DA9A4"
    secondary_color: str = "#8D6E63"
    currency: str = "BYN"
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""

class SettingsUpdate(BaseModel):
    online_menu_enabled: Optional[bool] = None
    staff_call_enabled: Optional[bool] = None
    online_orders_enabled: Optional[bool] = None
    business_lunch_enabled: Optional[bool] = None
    promotions_enabled: Optional[bool] = None
    theme: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    currency: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class MenuView(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    table_code: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============ AUTH HELPERS ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

async def require_superadmin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != UserRole.SUPERADMIN:
        raise HTTPException(status_code=403, detail="Требуются права суперадмина")
    return current_user

async def check_restaurant_access(user: dict, restaurant_id: str):
    if user.get("role") == UserRole.SUPERADMIN:
        return True
    if restaurant_id in user.get("restaurant_ids", []):
        return True
    raise HTTPException(status_code=403, detail="Нет доступа к этому ресторану")

# ============ HELPER FUNCTIONS ============

def serialize_doc(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop('_id', None)
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

async def create_superadmin():
    admin = await db.users.find_one({"username": "admin"}, {"_id": 0})
    if not admin:
        user = User(
            username="admin",
            password_hash=get_password_hash("220066"),
            role=UserRole.SUPERADMIN,
            restaurant_ids=[]
        )
        doc = user.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.users.insert_one(doc)
        print("Superadmin created: admin/220066")
    return admin

async def get_or_create_settings(restaurant_id: str):
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings:
        default = Settings(restaurant_id=restaurant_id)
        doc = default.model_dump()
        await db.settings.insert_one(doc)
        return doc
    return settings

async def get_or_create_menu_sections(restaurant_id: str):
    sections = await db.menu_sections.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not sections:
        default_sections = [
            MenuSection(restaurant_id=restaurant_id, name="Еда", sort_order=1),
            MenuSection(restaurant_id=restaurant_id, name="Напитки", sort_order=2),
            MenuSection(restaurant_id=restaurant_id, name="Кальяны", sort_order=3),
        ]
        for section in default_sections:
            await db.menu_sections.insert_one(section.model_dump())
        sections = [s.model_dump() for s in default_sections]
    return sections

async def get_or_create_call_types(restaurant_id: str):
    call_types = await db.call_types.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not call_types:
        default_types = [
            CallType(restaurant_id=restaurant_id, name="Вызов официанта", telegram_message="🔔 Стол #{table} - Вызов официанта", sort_order=1),
            CallType(restaurant_id=restaurant_id, name="Вызов кальянного мастера", telegram_message="💨 Стол #{table} - Вызов кальянного мастера", sort_order=2),
            CallType(restaurant_id=restaurant_id, name="Попросить счёт", telegram_message="💳 Стол #{table} - Просят счёт", sort_order=3),
        ]
        for ct in default_types:
            await db.call_types.insert_one(ct.model_dump())
        call_types = [ct.model_dump() for ct in default_types]
    return call_types

# ============ AUTH ENDPOINTS ============

@api_router.post("/auth/login")
async def login(data: LoginRequest):
    user = await db.users.find_one({"username": data.username}, {"_id": 0})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Пользователь деактивирован")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    if user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "restaurant_ids": user.get("restaurant_ids", [])
        },
        "restaurants": [serialize_doc(r) for r in restaurants]
    }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": current_user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)
    
    return {
        "user": {
            "id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
            "restaurant_ids": current_user.get("restaurant_ids", [])
        },
        "restaurants": [serialize_doc(r) for r in restaurants]
    }

# ============ USER MANAGEMENT (SUPERADMIN) ============

@api_router.get("/users")
async def get_users(current_user: dict = Depends(require_superadmin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [serialize_doc(u) for u in users]

@api_router.post("/users")
async def create_user(data: UserCreate, current_user: dict = Depends(require_superadmin)):
    existing = await db.users.find_one({"username": data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    
    user = User(
        username=data.username,
        password_hash=get_password_hash(data.password),
        role=data.role,
        restaurant_ids=data.restaurant_ids
    )
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    doc.pop('password_hash', None)
    return serialize_doc(doc)

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate, current_user: dict = Depends(require_superadmin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    update_data = {}
    if data.username is not None:
        update_data["username"] = data.username
    if data.password is not None:
        update_data["password_hash"] = get_password_hash(data.password)
    if data.role is not None:
        update_data["role"] = data.role
    if data.restaurant_ids is not None:
        update_data["restaurant_ids"] = data.restaurant_ids
    if data.is_active is not None:
        update_data["is_active"] = data.is_active
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return serialize_doc(updated)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_superadmin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return {"message": "Пользователь удален"}

# ============ RESTAURANT ENDPOINTS ============

@api_router.get("/restaurants")
async def get_restaurants(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == UserRole.SUPERADMIN:
        restaurants = await db.restaurants.find({}, {"_id": 0}).to_list(100)
    else:
        restaurants = await db.restaurants.find({"id": {"$in": current_user.get("restaurant_ids", [])}}, {"_id": 0}).to_list(100)
    return [serialize_doc(r) for r in restaurants]

@api_router.post("/restaurants")
async def create_restaurant(data: RestaurantCreate, current_user: dict = Depends(require_superadmin)):
    restaurant = Restaurant(
        name=data.name,
        description=data.description,
        address=data.address,
        phone=data.phone,
        email=data.email
    )
    doc = restaurant.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.restaurants.insert_one(doc)
    
    await get_or_create_settings(doc['id'])
    await get_or_create_menu_sections(doc['id'])
    await get_or_create_call_types(doc['id'])
    
    return serialize_doc(doc)

@api_router.get("/restaurants/{restaurant_id}")
async def get_restaurant_by_id(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    return serialize_doc(restaurant)

@api_router.put("/restaurants/{restaurant_id}")
async def update_restaurant(restaurant_id: str, data: RestaurantUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.restaurants.update_one({"id": restaurant_id}, {"$set": update_data})
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    return serialize_doc(restaurant)

@api_router.delete("/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: str, current_user: dict = Depends(require_superadmin)):
    for coll in ['menu_sections', 'categories', 'menu_items', 'tables', 'orders', 'staff_calls', 'call_types', 'employees', 'settings', 'menu_views']:
        await db[coll].delete_many({"restaurant_id": restaurant_id})
    result = await db.restaurants.delete_one({"id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    return {"message": "Ресторан удален"}

# ============ MENU SECTIONS ============

@api_router.get("/restaurants/{restaurant_id}/menu-sections")
async def get_menu_sections(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_menu_sections(restaurant_id)

@api_router.post("/restaurants/{restaurant_id}/menu-sections")
async def create_menu_section(restaurant_id: str, data: MenuSectionCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    section = MenuSection(restaurant_id=restaurant_id, **data.model_dump())
    doc = section.model_dump()
    await db.menu_sections.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/menu-sections/{section_id}")
async def update_menu_section(restaurant_id: str, section_id: str, data: MenuSectionCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_sections.update_one({"id": section_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    return await db.menu_sections.find_one({"id": section_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/menu-sections/{section_id}")
async def delete_menu_section(restaurant_id: str, section_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_sections.delete_one({"id": section_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.categories.update_many({"section_id": section_id}, {"$set": {"section_id": None}})
    return {"message": "Section deleted"}

# ============ CATEGORIES ============

@api_router.get("/restaurants/{restaurant_id}/categories")
async def get_categories(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    return [serialize_doc(c) for c in categories]

@api_router.post("/restaurants/{restaurant_id}/categories")
async def create_category(restaurant_id: str, data: CategoryCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    category = Category(restaurant_id=restaurant_id, **data.model_dump())
    doc = category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/categories/{category_id}")
async def update_category(restaurant_id: str, category_id: str, data: CategoryCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.categories.update_one({"id": category_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return await db.categories.find_one({"id": category_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/categories/{category_id}")
async def delete_category(restaurant_id: str, category_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.categories.delete_one({"id": category_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.menu_items.delete_many({"category_id": category_id})
    return {"message": "Category deleted"}

@api_router.post("/restaurants/{restaurant_id}/categories/reorder")
async def reorder_categories(restaurant_id: str, order: List[str], current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    for idx, cat_id in enumerate(order):
        await db.categories.update_one({"id": cat_id, "restaurant_id": restaurant_id}, {"$set": {"sort_order": idx}})
    return {"message": "Reordered"}

# ============ MENU ITEMS ============

@api_router.get("/restaurants/{restaurant_id}/menu-items")
async def get_menu_items(restaurant_id: str, category_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if category_id:
        query["category_id"] = category_id
    items = await db.menu_items.find(query, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    return [serialize_doc(i) for i in items]

@api_router.post("/restaurants/{restaurant_id}/menu-items")
async def create_menu_item(restaurant_id: str, data: MenuItemCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    item = MenuItem(restaurant_id=restaurant_id, **data.model_dump())
    doc = item.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_items.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def update_menu_item(restaurant_id: str, item_id: str, data: MenuItemUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": update_data})
    return await db.menu_items.find_one({"id": item_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/menu-items/{item_id}")
async def delete_menu_item(restaurant_id: str, item_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    result = await db.menu_items.delete_one({"id": item_id, "restaurant_id": restaurant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}

@api_router.post("/restaurants/{restaurant_id}/menu-items/reorder")
async def reorder_items(restaurant_id: str, order: List[str], current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    for idx, item_id in enumerate(order):
        await db.menu_items.update_one({"id": item_id, "restaurant_id": restaurant_id}, {"$set": {"sort_order": idx}})
    return {"message": "Reordered"}

# ============ LABELS ============

@api_router.get("/restaurants/{restaurant_id}/labels")
async def get_labels(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    return labels

@api_router.post("/restaurants/{restaurant_id}/labels")
async def create_label(restaurant_id: str, data: LabelCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    label = Label(restaurant_id=restaurant_id, name=data.name, color=data.color)
    doc = label.model_dump()
    await db.labels.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/labels/{label_id}")
async def update_label(restaurant_id: str, label_id: str, data: LabelUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.labels.update_one({"id": label_id, "restaurant_id": restaurant_id}, {"$set": update_data})
    return await db.labels.find_one({"id": label_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/labels/{label_id}")
async def delete_label(restaurant_id: str, label_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.labels.delete_one({"id": label_id, "restaurant_id": restaurant_id})
    # Remove label from all items
    await db.menu_items.update_many(
        {"restaurant_id": restaurant_id, "label_ids": label_id},
        {"$pull": {"label_ids": label_id}}
    )
    return {"message": "Label deleted"}

# ============ TABLES ============

@api_router.get("/restaurants/{restaurant_id}/tables")
async def get_tables(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    tables = await db.tables.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("number", 1).to_list(500)
    return [serialize_doc(t) for t in tables]

@api_router.post("/restaurants/{restaurant_id}/tables")
async def create_table(restaurant_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = Table(restaurant_id=restaurant_id, **data.model_dump())
    doc = table.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tables.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/tables/{table_id}")
async def update_table(restaurant_id: str, table_id: str, data: TableCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.tables.find_one({"id": table_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/tables/{table_id}")
async def delete_table(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.tables.delete_one({"id": table_id, "restaurant_id": restaurant_id})
    return {"message": "Table deleted"}

@api_router.post("/restaurants/{restaurant_id}/tables/{table_id}/regenerate-code")
async def regenerate_table_code(restaurant_id: str, table_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    new_code = str(uuid.uuid4())[:8].upper()
    await db.tables.update_one({"id": table_id, "restaurant_id": restaurant_id}, {"$set": {"code": new_code}})
    return {"code": new_code}

@api_router.get("/restaurants/{restaurant_id}/tables/{table_id}/qr")
async def get_table_qr(restaurant_id: str, table_id: str, base_url: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    table = await db.tables.find_one({"id": table_id, "restaurant_id": restaurant_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    if not base_url:
        base_url = os.environ.get('FRONTEND_URL', 'https://example.com')
    
    menu_url = f"{base_url}/menu/{table['code']}"
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(menu_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return {
        "table_id": table_id,
        "table_number": table['number'],
        "table_code": table['code'],
        "menu_url": menu_url,
        "qr_base64": f"data:image/png;base64,{img_base64}"
    }

# ============ CALL TYPES ============

@api_router.get("/restaurants/{restaurant_id}/call-types")
async def get_call_types(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_call_types(restaurant_id)

@api_router.post("/restaurants/{restaurant_id}/call-types")
async def create_call_type(restaurant_id: str, data: CallTypeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    call_type = CallType(restaurant_id=restaurant_id, **data.model_dump())
    doc = call_type.model_dump()
    await db.call_types.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/call-types/{call_type_id}")
async def update_call_type(restaurant_id: str, call_type_id: str, data: CallTypeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.call_types.update_one({"id": call_type_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.call_types.find_one({"id": call_type_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/call-types/{call_type_id}")
async def delete_call_type(restaurant_id: str, call_type_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.call_types.delete_one({"id": call_type_id, "restaurant_id": restaurant_id})
    return {"message": "Call type deleted"}

# ============ ORDERS ============

@api_router.get("/restaurants/{restaurant_id}/orders")
async def get_orders(restaurant_id: str, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if status:
        query["status"] = status
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(o) for o in orders]

@api_router.put("/restaurants/{restaurant_id}/orders/{order_id}/status")
async def update_order_status(restaurant_id: str, order_id: str, data: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.orders.update_one({"id": order_id, "restaurant_id": restaurant_id}, {"$set": {"status": data.status}})
    return await db.orders.find_one({"id": order_id}, {"_id": 0})

# ============ STAFF CALLS ============

@api_router.get("/restaurants/{restaurant_id}/staff-calls")
async def get_staff_calls(restaurant_id: str, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    query = {"restaurant_id": restaurant_id}
    if status:
        query["status"] = status
    calls = await db.staff_calls.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(c) for c in calls]

@api_router.put("/restaurants/{restaurant_id}/staff-calls/{call_id}/status")
async def update_staff_call_status(restaurant_id: str, call_id: str, status: StaffCallStatus, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.staff_calls.update_one({"id": call_id, "restaurant_id": restaurant_id}, {"$set": {"status": status}})
    return await db.staff_calls.find_one({"id": call_id}, {"_id": 0})

# ============ EMPLOYEES ============

@api_router.get("/restaurants/{restaurant_id}/employees")
async def get_employees(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    employees = await db.employees.find({"restaurant_id": restaurant_id}, {"_id": 0}).to_list(500)
    return [serialize_doc(e) for e in employees]

@api_router.post("/restaurants/{restaurant_id}/employees")
async def create_employee(restaurant_id: str, data: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    employee = Employee(restaurant_id=restaurant_id, **data.model_dump())
    doc = employee.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.employees.insert_one(doc)
    doc.pop('_id', None)
    return doc

@api_router.put("/restaurants/{restaurant_id}/employees/{employee_id}")
async def update_employee(restaurant_id: str, employee_id: str, data: EmployeeCreate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.employees.update_one({"id": employee_id, "restaurant_id": restaurant_id}, {"$set": data.model_dump()})
    return await db.employees.find_one({"id": employee_id}, {"_id": 0})

@api_router.delete("/restaurants/{restaurant_id}/employees/{employee_id}")
async def delete_employee(restaurant_id: str, employee_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.employees.delete_one({"id": employee_id, "restaurant_id": restaurant_id})
    return {"message": "Employee deleted"}

# ============ SETTINGS ============

@api_router.get("/restaurants/{restaurant_id}/settings")
async def get_settings(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    return await get_or_create_settings(restaurant_id)

@api_router.put("/restaurants/{restaurant_id}/settings")
async def update_settings(restaurant_id: str, data: SettingsUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.settings.update_one({"restaurant_id": restaurant_id}, {"$set": update_data})
    return await get_or_create_settings(restaurant_id)

# ============ ANALYTICS ============

@api_router.get("/restaurants/{restaurant_id}/analytics")
async def get_analytics(restaurant_id: str, days: int = 30, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Views
    views_total = await db.menu_views.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}})
    views_today = await db.menu_views.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}})
    
    # Orders
    orders = await db.orders.find({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}}, {"_id": 0}).to_list(5000)
    orders_total = len(orders)
    orders_today = len([o for o in orders if o.get('created_at', '') >= today_start.isoformat()])
    revenue_total = sum(o.get('total', 0) for o in orders)
    revenue_today = sum(o.get('total', 0) for o in orders if o.get('created_at', '') >= today_start.isoformat())
    
    # Staff calls
    calls_total = await db.staff_calls.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": start_date.isoformat()}})
    calls_today = await db.staff_calls.count_documents({"restaurant_id": restaurant_id, "created_at": {"$gte": today_start.isoformat()}})
    
    # Popular items
    item_counts = {}
    for order in orders:
        for item in order.get('items', []):
            item_id = item.get('menu_item_id')
            if item_id:
                item_counts[item_id] = item_counts.get(item_id, 0) + item.get('quantity', 1)
    
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    popular_items = []
    for item_id, count in top_items:
        item = await db.menu_items.find_one({"id": item_id}, {"_id": 0, "name": 1, "price": 1})
        if item:
            popular_items.append({"id": item_id, "name": item.get('name'), "count": count, "revenue": count * item.get('price', 0)})
    
    # Views by day
    views_by_day = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = await db.menu_views.count_documents({
            "restaurant_id": restaurant_id,
            "created_at": {"$gte": day_start.isoformat(), "$lt": day_end.isoformat()}
        })
        views_by_day.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})
    
    # Orders by day
    orders_by_day = []
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_orders = [o for o in orders if day_start.isoformat() <= o.get('created_at', '') < day_end.isoformat()]
        orders_by_day.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": len(day_orders),
            "revenue": sum(o.get('total', 0) for o in day_orders)
        })
    
    employees_count = await db.employees.count_documents({"restaurant_id": restaurant_id})
    
    return {
        "period_days": days,
        "views": {"total": views_total, "today": views_today, "by_day": list(reversed(views_by_day))},
        "orders": {"total": orders_total, "today": orders_today, "by_day": list(reversed(orders_by_day))},
        "revenue": {"total": revenue_total, "today": revenue_today},
        "staff_calls": {"total": calls_total, "today": calls_today},
        "popular_items": popular_items,
        "employees_count": employees_count
    }

# ============ PUBLIC ENDPOINTS (NO AUTH) ============

@api_router.get("/public/menu/{table_code}")
async def get_public_menu(table_code: str):
    table = await db.tables.find_one({"code": table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")
    
    restaurant_id = table.get('restaurant_id')
    if not restaurant_id:
        raise HTTPException(status_code=404, detail="Ресторан не найден")
    
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    settings = await get_or_create_settings(restaurant_id)
    sections = await get_or_create_menu_sections(restaurant_id)
    call_types = await get_or_create_call_types(restaurant_id)
    categories = await db.categories.find({"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(1000)
    items = await db.menu_items.find({"restaurant_id": restaurant_id, "is_available": True}, {"_id": 0}).sort("sort_order", 1).to_list(5000)
    labels = await db.labels.find({"restaurant_id": restaurant_id}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    
    # Record view
    view = MenuView(restaurant_id=restaurant_id, table_code=table_code)
    doc = view.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_views.insert_one(doc)
    
    return {
        "restaurant": serialize_doc(restaurant),
        "table": serialize_doc(table),
        "settings": settings,
        "sections": sections,
        "call_types": call_types,
        "categories": [serialize_doc(c) for c in categories],
        "items": [serialize_doc(i) for i in items],
        "labels": labels
    }

@api_router.post("/public/orders")
async def create_public_order(data: OrderCreate):
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")
    
    restaurant_id = table.get('restaurant_id')
    total = sum(item.price * item.quantity for item in data.items)
    
    order = Order(
        restaurant_id=restaurant_id,
        table_id=table['id'],
        table_number=table['number'],
        items=[i.model_dump() for i in data.items],
        total=total,
        notes=data.notes
    )
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.orders.insert_one(doc)
    doc.pop('_id', None)
    
    # Send Telegram notification
    table_num = table.get('number', '?')
    items_text = "\n".join([f"  - {i.name} x{i.quantity}" for i in data.items])
    msg = f"<b>Новый заказ</b>\nСтол #{table_num}\n\n{items_text}\n\n<b>Итого: {total} BYN</b>"
    if data.notes:
        msg += f"\nКомментарий: {data.notes}"
    await notify_restaurant_telegram(restaurant_id, msg)
    
    return doc

@api_router.post("/public/staff-calls")
async def create_public_staff_call(data: StaffCallCreate):
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Стол не найден")
    
    restaurant_id = table.get('restaurant_id')
    call_type_name = None
    if data.call_type_id:
        call_type = await db.call_types.find_one({"id": data.call_type_id}, {"_id": 0})
        if call_type:
            call_type_name = call_type.get('name')
    
    staff_call = StaffCall(
        restaurant_id=restaurant_id,
        table_id=table['id'],
        table_number=table['number'],
        call_type_id=data.call_type_id,
        call_type_name=call_type_name
    )
    doc = staff_call.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.staff_calls.insert_one(doc)
    doc.pop('_id', None)
    
    # Send Telegram notification
    table_num = table.get('number', '?')
    msg = f"<b>{call_type_name or 'Вызов персонала'}</b>\nСтол #{table_num}"
    await notify_restaurant_telegram(restaurant_id, msg)
    
    return doc

# ============ FILE UPLOAD ============

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

@api_router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимум 5MB")
    
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOADS_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    
    return {"url": f"/api/uploads/{filename}", "filename": filename}

async def download_and_save_image(image_url: str) -> str:
    """Download image from external URL and save locally. Returns local URL."""
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

@api_router.post("/restaurants/{restaurant_id}/download-images")
async def download_menu_images(restaurant_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """Start background download of all external images in menu items"""
    await check_restaurant_access(current_user, restaurant_id)
    
    items = await db.menu_items.find(
        {"restaurant_id": restaurant_id, "image_url": {"$regex": "^https?://"}},
        {"_id": 0, "id": 1, "image_url": 1}
    ).to_list(5000)
    
    if not items:
        return {"message": "Нет внешних изображений", "total": 0}
    
    # Start background task
    background_tasks.add_task(download_images_task, restaurant_id, items)
    
    return {"message": f"Запущено скачивание {len(items)} изображений. Это может занять несколько минут.", "total": len(items)}

async def download_images_task(restaurant_id: str, items: list):
    """Background task to download images in batches"""
    import asyncio
    downloaded = 0
    failed = 0
    
    # Process in batches of 10
    batch_size = 10
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        tasks = []
        for item in batch:
            tasks.append(download_and_update_item(restaurant_id, item))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                downloaded += 1
            else:
                failed += 1
    
    logging.info(f"Image download complete for {restaurant_id}: {downloaded} ok, {failed} failed")

async def download_and_update_item(restaurant_id: str, item: dict) -> bool:
    """Download single image and update item"""
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

# ============ IMPORT MENU (JSON & .DATA) ============

import re as _re

def strip_html(text: str) -> str:
    """Remove HTML tags from string"""
    if not text:
        return ""
    return _re.sub(r'<[^>]+>', '', text).strip()

def parse_lunchpad_data(raw_data: list) -> dict:
    """Parse LunchPad .data format into our import format"""
    categories = []
    pending_banners = []  # type=2 banners to attach to next category
    
    for entry in raw_data:
        entry_type = entry.get("type")
        
        # type=2: banner/separator - collect banners with images
        if entry_type == 2:
            foto = entry.get("foto", {}) or {}
            image_url = foto.get("image_url", "") or ""
            if image_url:
                banner_name = strip_html(entry.get("name", "")).strip()
                banner_desc = strip_html(entry.get("description", "")).strip()
                if banner_name == "--":
                    banner_name = ""
                pending_banners.append({
                    "name": banner_name,
                    "description": banner_desc,
                    "image_url": image_url,
                    "is_banner": True,
                    "price": 0,
                })
            continue
        
        if entry_type != 0:
            continue
        
        cat_name = strip_html(entry.get("name", "")).strip()
        if not cat_name:
            continue
        
        items_raw = entry.get("items", [])
        
        display = entry.get("display", "")
        display_mode = "card" if display == "grid" else "compact"
        
        items = []
        
        # Add pending banners to this category
        for banner in pending_banners:
            items.append(banner)
        pending_banners = []
        
        for item in items_raw:
            item_type = item.get("type")
            
            # type=2 inside category = banner/separator
            if item_type == 2:
                item_foto = item.get("foto", {}) or {}
                item_img = item_foto.get("image_url", "") or ""
                if item_img:
                    banner_name = strip_html(item.get("name", "")).strip()
                    if banner_name == "--":
                        banner_name = ""
                    items.append({
                        "name": banner_name,
                        "description": strip_html(item.get("description", "")),
                        "image_url": item_img,
                        "is_banner": True,
                        "price": 0,
                    })
                continue
            
            # type=0 inside category = sub-category header (skip for now, not a menu item)
            if item_type == 0:
                continue
            
            if item_type != 4:
                continue
            
            item_name = strip_html(item.get("name", "")).strip()
            if not item_name:
                continue
            
            description = strip_html(item.get("description", ""))
            
            prices = item.get("prices", [])
            price = 0
            weight = ""
            if prices:
                p = prices[0]
                raw_price = p.get("price", 0)
                if isinstance(raw_price, (int, float)):
                    price = float(raw_price)
                elif isinstance(raw_price, str):
                    # Extract number from strings like "75 р", "8.5 р", "12,50 р"
                    cleaned = raw_price.replace(',', '.').strip()
                    match = _re.search(r'[\d]+[.]?[\d]*', cleaned)
                    price = float(match.group()) if match else 0
                weight = p.get("measure", "")
            
            foto = item.get("foto", {}) or {}
            image_url = foto.get("image_url", "") or ""
            
            in_stop = item.get("in_stop_list", False)
            
            items.append({
                "name": item_name,
                "description": description,
                "price": price,
                "weight": weight,
                "image_url": image_url,
                "is_available": not in_stop,
            })
        
        categories.append({
            "name": cat_name,
            "display_mode": display_mode,
            "items": items,
        })
    
    return {"categories": categories}

class ImportMenuRequest(BaseModel):
    data: dict
    mode: str = "append"  # "append" or "replace"

@api_router.post("/restaurants/{restaurant_id}/import-menu")
async def import_menu_json(restaurant_id: str, request: ImportMenuRequest, current_user: dict = Depends(get_current_user)):
    """Import menu from JSON (old service format)"""
    await check_restaurant_access(current_user, restaurant_id)
    
    data = request.data
    imported_categories = 0
    imported_items = 0
    
    try:
        # If replace mode, delete all existing categories and items
        if request.mode == "replace":
            await db.menu_items.delete_many({"restaurant_id": restaurant_id})
            await db.categories.delete_many({"restaurant_id": restaurant_id})
        # Get existing menu sections
        sections = await get_or_create_menu_sections(restaurant_id)
        section_map = {s['name'].lower(): s['id'] for s in sections}
        default_section_id = sections[0]['id'] if sections else None
        
        # Process categories
        categories_data = data.get('categories', [])
        for cat_data in categories_data:
            cat_name = cat_data.get('name', '').strip()
            if not cat_name:
                continue
            
            # Determine section based on category name or use default
            section_id = default_section_id
            cat_lower = cat_name.lower()
            if any(kw in cat_lower for kw in ['напиток', 'коктейль', 'вино', 'пиво', 'виски', 'кофе', 'чай', 'сок', 'лимонад', 'бар']):
                section_id = section_map.get('напитки', default_section_id)
            elif any(kw in cat_lower for kw in ['кальян', 'табак', 'hookah']):
                section_id = section_map.get('кальяны', default_section_id)
            else:
                section_id = section_map.get('еда', default_section_id)
            
            # Check if category exists
            existing_cat = await db.categories.find_one({
                "restaurant_id": restaurant_id,
                "name": cat_name
            })
            
            if existing_cat:
                cat_id = existing_cat['id']
            else:
                # Create new category
                category = Category(
                    restaurant_id=restaurant_id,
                    name=cat_name,
                    section_id=section_id,
                    display_mode=cat_data.get('display_mode', 'card'),
                    sort_order=cat_data.get('sort_order', imported_categories),
                    is_active=cat_data.get('is_active', True)
                )
                doc = category.model_dump()
                doc['created_at'] = doc['created_at'].isoformat()
                await db.categories.insert_one(doc)
                cat_id = doc['id']
                imported_categories += 1
            
            # Process items in this category
            items_data = cat_data.get('items', [])
            for idx, item_data in enumerate(items_data):
                item_name = item_data.get('name', '').strip()
                is_banner = item_data.get('is_banner', False)
                
                # Skip non-banner items without names
                if not item_name and not is_banner:
                    continue
                
                # For banners, check by image_url; for items check by name
                if not is_banner:
                    existing_item = await db.menu_items.find_one({
                        "restaurant_id": restaurant_id,
                        "category_id": cat_id,
                        "name": item_name
                    })
                else:
                    existing_item = None
                
                if not existing_item:
                    item = MenuItem(
                        restaurant_id=restaurant_id,
                        category_id=cat_id,
                        name=item_name,
                        description=item_data.get('description', ''),
                        price=float(item_data.get('price', 0) or 0),
                        weight=item_data.get('weight', item_data.get('portion', '')),
                        image_url=item_data.get('image_url', item_data.get('image', '')),
                        is_available=item_data.get('is_available', True),
                        is_hit=item_data.get('is_hit', False),
                        is_new=item_data.get('is_new', False),
                        is_spicy=item_data.get('is_spicy', False),
                        is_banner=is_banner,
                        sort_order=item_data.get('sort_order', idx)
                    )
                    doc = item.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.menu_items.insert_one(doc)
                    imported_items += 1
        
        # Also handle flat items list if present
        if 'items' in data and not categories_data:
            for idx, item_data in enumerate(data.get('items', [])):
                item_name = item_data.get('name', '').strip()
                cat_name = item_data.get('category', item_data.get('category_name', 'Без категории'))
                
                if not item_name:
                    continue
                
                # Find or create category
                existing_cat = await db.categories.find_one({
                    "restaurant_id": restaurant_id,
                    "name": cat_name
                })
                
                if existing_cat:
                    cat_id = existing_cat['id']
                else:
                    category = Category(
                        restaurant_id=restaurant_id,
                        name=cat_name,
                        section_id=default_section_id,
                        sort_order=imported_categories
                    )
                    doc = category.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.categories.insert_one(doc)
                    cat_id = doc['id']
                    imported_categories += 1
                
                # Create item
                existing_item = await db.menu_items.find_one({
                    "restaurant_id": restaurant_id,
                    "name": item_name
                })
                
                if not existing_item:
                    item = MenuItem(
                        restaurant_id=restaurant_id,
                        category_id=cat_id,
                        name=item_name,
                        description=item_data.get('description', ''),
                        price=float(item_data.get('price', 0)),
                        weight=item_data.get('weight', item_data.get('portion', '')),
                        image_url=item_data.get('image_url', item_data.get('image', '')),
                        is_available=item_data.get('is_available', True),
                        sort_order=idx
                    )
                    doc = item.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.menu_items.insert_one(doc)
                    imported_items += 1
        
        return {
            "message": "Импорт завершён",
            "imported_categories": imported_categories,
            "imported_items": imported_items
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка импорта: {str(e)}")

@api_router.post("/restaurants/{restaurant_id}/import-file")
async def import_menu_file(restaurant_id: str, file: UploadFile = File(...), mode: str = Query("append"), current_user: dict = Depends(get_current_user)):
    """Import menu from .data or .json file upload"""
    await check_restaurant_access(current_user, restaurant_id)
    
    ext = Path(file.filename).suffix.lower()
    if ext not in {'.data', '.json'}:
        raise HTTPException(status_code=400, detail="Допустимые форматы: .data, .json")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимум 10MB")
    
    try:
        import json as _json
        raw = _json.loads(content.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл. Проверьте формат JSON.")
    
    # Detect format: LunchPad .data (array of objects with type field) vs our format (dict with categories)
    if isinstance(raw, list):
        # LunchPad format
        parsed = parse_lunchpad_data(raw)
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise HTTPException(status_code=400, detail="Неизвестный формат данных")
    
    # Reuse existing import logic
    request = ImportMenuRequest(data=parsed, mode=mode)
    return await import_menu_json(restaurant_id, request, current_user)

# ============ TELEGRAM BOT ============

TELEGRAM_API = "https://api.telegram.org/bot"

async def send_telegram_message(bot_token: str, chat_id: str, text: str):
    """Send message via Telegram Bot API"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{TELEGRAM_API}{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            return resp.status_code == 200
    except Exception as e:
        logging.error(f"Telegram send error: {e}")
        return False

async def notify_restaurant_telegram(restaurant_id: str, message: str):
    """Send notification to all Telegram subscribers of a restaurant"""
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return
    
    bot_token = settings["telegram_bot_token"]
    subscribers = await db.telegram_subscribers.find(
        {"restaurant_id": restaurant_id, "is_active": True}, {"_id": 0}
    ).to_list(500)
    
    for sub in subscribers:
        await send_telegram_message(bot_token, sub["chat_id"], message)

class TelegramBotUpdate(BaseModel):
    telegram_bot_token: str

@api_router.get("/restaurants/{restaurant_id}/telegram-bot")
async def get_telegram_bot(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    bot_token = settings.get("telegram_bot_token", "") if settings else ""
    
    subscribers = await db.telegram_subscribers.find(
        {"restaurant_id": restaurant_id}, {"_id": 0}
    ).to_list(500)
    
    bot_info = None
    webhook_set = False
    if bot_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{TELEGRAM_API}{bot_token}/getMe")
                if resp.status_code == 200:
                    bot_info = resp.json().get("result")
                wh_resp = await client.get(f"{TELEGRAM_API}{bot_token}/getWebhookInfo")
                if wh_resp.status_code == 200:
                    wh_url = wh_resp.json().get("result", {}).get("url", "")
                    webhook_set = bool(wh_url)
        except Exception:
            pass
    
    return {
        "bot_token": bot_token,
        "bot_info": bot_info,
        "webhook_set": webhook_set,
        "subscribers": [{"chat_id": s["chat_id"], "username": s.get("username", ""), "first_name": s.get("first_name", ""), "subscribed_at": s.get("subscribed_at", "")} for s in subscribers]
    }

@api_router.put("/restaurants/{restaurant_id}/telegram-bot")
async def update_telegram_bot(restaurant_id: str, data: TelegramBotUpdate, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    bot_token = data.telegram_bot_token.strip()
    
    # Validate token with Telegram
    if bot_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{TELEGRAM_API}{bot_token}/getMe")
                if resp.status_code != 200:
                    raise HTTPException(status_code=400, detail="Невалидный токен бота. Проверьте токен от @BotFather")
        except httpx.RequestError:
            raise HTTPException(status_code=400, detail="Не удалось подключиться к Telegram API")
        
        # Set webhook
        webhook_url = f"{os.environ.get('REACT_APP_BACKEND_URL', '')}/api/telegram/webhook/{restaurant_id}"
        # Try to get the external URL from frontend env 
        frontend_env_path = ROOT_DIR.parent / "frontend" / ".env"
        if frontend_env_path.exists():
            with open(frontend_env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        external_url = line.split("=", 1)[1].strip()
                        webhook_url = f"{external_url}/api/telegram/webhook/{restaurant_id}"
                        break
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Set webhook
                wh_resp = await client.post(
                    f"{TELEGRAM_API}{bot_token}/setWebhook",
                    json={"url": webhook_url}
                )
                # Set bot commands
                await client.post(
                    f"{TELEGRAM_API}{bot_token}/setMyCommands",
                    json={"commands": [{"command": "start", "description": "Подписаться на уведомления"}]}
                )
        except Exception as e:
            logging.error(f"Webhook setup error: {e}")
    else:
        # Remove webhook if token is cleared
        old_settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
        old_token = old_settings.get("telegram_bot_token") if old_settings else None
        if old_token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(f"{TELEGRAM_API}{old_token}/deleteWebhook")
            except Exception:
                pass
    
    await db.settings.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"telegram_bot_token": bot_token}}
    )
    
    return {"message": "Настройки бота обновлены", "webhook_url": webhook_url if bot_token else ""}

@api_router.delete("/restaurants/{restaurant_id}/telegram-bot")
async def disconnect_telegram_bot(restaurant_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    old_token = settings.get("telegram_bot_token") if settings else None
    if old_token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(f"{TELEGRAM_API}{old_token}/deleteWebhook")
        except Exception:
            pass
    
    await db.settings.update_one(
        {"restaurant_id": restaurant_id},
        {"$set": {"telegram_bot_token": ""}}
    )
    await db.telegram_subscribers.delete_many({"restaurant_id": restaurant_id})
    
    return {"message": "Бот отключён"}

@api_router.delete("/restaurants/{restaurant_id}/telegram-bot/subscribers/{chat_id}")
async def remove_telegram_subscriber(restaurant_id: str, chat_id: str, current_user: dict = Depends(get_current_user)):
    await check_restaurant_access(current_user, restaurant_id)
    await db.telegram_subscribers.delete_one({"restaurant_id": restaurant_id, "chat_id": chat_id})
    return {"message": "Подписчик удалён"}

@api_router.post("/telegram/webhook/{restaurant_id}")
async def telegram_webhook(restaurant_id: str, request: dict):
    """Handle incoming Telegram updates (public endpoint)"""
    message = request.get("message", {})
    if not message:
        return {"ok": True}
    
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    text = message.get("text", "")
    
    if not chat_id:
        return {"ok": True}
    
    settings = await db.settings.find_one({"restaurant_id": restaurant_id}, {"_id": 0})
    if not settings or not settings.get("telegram_bot_token"):
        return {"ok": True}
    
    bot_token = settings["telegram_bot_token"]
    restaurant = await db.restaurants.find_one({"id": restaurant_id}, {"_id": 0})
    restaurant_name = restaurant.get("name", "Ресторан") if restaurant else "Ресторан"
    
    if text.startswith("/start"):
        # Subscribe user
        existing = await db.telegram_subscribers.find_one(
            {"restaurant_id": restaurant_id, "chat_id": chat_id}
        )
        if not existing:
            await db.telegram_subscribers.insert_one({
                "restaurant_id": restaurant_id,
                "chat_id": chat_id,
                "username": chat.get("username", ""),
                "first_name": chat.get("first_name", ""),
                "is_active": True,
                "subscribed_at": datetime.now(timezone.utc).isoformat()
            })
            await send_telegram_message(
                bot_token, chat_id,
                f"Вы подписаны на уведомления <b>{restaurant_name}</b>!\n\n"
                f"Вы будете получать уведомления о:\n"
                f"- Вызовах персонала\n"
                f"- Запросах счёта\n"
                f"- Новых заказах"
            )
        else:
            await send_telegram_message(
                bot_token, chat_id,
                f"Вы уже подписаны на уведомления <b>{restaurant_name}</b>."
            )
    
    return {"ok": True}

# ============ SEED & HEALTH ============

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@api_router.post("/seed")
async def seed_data():
    await create_superadmin()
    
    # Check if restaurants exist
    count = await db.restaurants.count_documents({})
    if count == 0:
        # Create first restaurant
        r1 = Restaurant(
            name="Мята Спортивная",
            description="Уютный ресторан с авторской кухней и кальянами",
            address="ул. Спортивная, 15",
            phone="+375 (29) 123-45-67",
            email="info@myata-sport.by",
            slogan="Вкус, который запоминается",
            working_hours="Пн-Вс: 12:00 - 02:00"
        )
        doc1 = r1.model_dump()
        doc1['created_at'] = doc1['created_at'].isoformat()
        await db.restaurants.insert_one(doc1)
        
        # Create second restaurant
        r2 = Restaurant(
            name="Мята Центральная",
            description="Ресторан в центре города с панорамным видом",
            address="пр. Независимости, 50",
            phone="+375 (29) 765-43-21",
            email="info@myata-central.by",
            slogan="Вкус на высоте",
            working_hours="Пн-Вс: 11:00 - 01:00"
        )
        doc2 = r2.model_dump()
        doc2['created_at'] = doc2['created_at'].isoformat()
        await db.restaurants.insert_one(doc2)
        
        # Initialize both restaurants
        for doc in [doc1, doc2]:
            rid = doc['id']
            await get_or_create_settings(rid)
            await get_or_create_menu_sections(rid)
            await get_or_create_call_types(rid)
            
            # Create tables
            for i in range(1, 11):
                table = Table(restaurant_id=rid, number=i, name=f"Стол {i}")
                tdoc = table.model_dump()
                tdoc['created_at'] = tdoc['created_at'].isoformat()
                await db.tables.insert_one(tdoc)
    
    return {"message": "Data seeded successfully"}

# Include router
app.include_router(api_router)

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
