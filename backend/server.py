from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Restaurant Dashboard API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============ ENUMS ============
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

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    working_hours: Optional[str] = None
    slogan: Optional[str] = None

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True

class MenuItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str
    name: str
    description: Optional[str] = ""
    price: float
    weight: Optional[str] = ""
    image_url: Optional[str] = ""
    is_available: bool = True
    is_business_lunch: bool = False
    is_promotion: bool = False
    is_hit: bool = False
    is_new: bool = False
    is_spicy: bool = False
    sort_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MenuItemCreate(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = ""
    price: float
    weight: Optional[str] = ""
    image_url: Optional[str] = ""
    is_available: bool = True
    is_business_lunch: bool = False
    is_promotion: bool = False
    is_hit: bool = False
    is_new: bool = False
    is_spicy: bool = False
    sort_order: int = 0

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
    sort_order: Optional[int] = None

class Table(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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

class StaffCall(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    table_id: str
    table_number: int
    status: StaffCallStatus = StaffCallStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StaffCallCreate(BaseModel):
    table_code: str

class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    id: str = "main"
    online_menu_enabled: bool = True
    staff_call_enabled: bool = True
    online_orders_enabled: bool = True
    business_lunch_enabled: bool = True
    promotions_enabled: bool = True
    theme: str = "light"
    primary_color: str = "#5DA9A4"
    secondary_color: str = "#8D6E63"
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
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class SupportTicket(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    description: str
    contact_email: str
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    contact_email: str

class MenuView(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    table_code: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Stats(BaseModel):
    views_today: int = 0
    views_month: int = 0
    calls_today: int = 0
    calls_month: int = 0
    orders_today: int = 0
    orders_month: int = 0
    employees_count: int = 0

# ============ HELPER FUNCTIONS ============

def serialize_doc(doc: dict) -> dict:
    """Remove MongoDB _id and convert datetime to ISO string"""
    if doc is None:
        return None
    doc.pop('_id', None)
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

async def get_or_create_restaurant():
    """Get or create default restaurant"""
    restaurant = await db.restaurants.find_one({}, {"_id": 0})
    if not restaurant:
        default = Restaurant(
            name="Мята Спортивная",
            description="Уютный ресторан с авторской кухней и кальянами",
            address="ул. Спортивная, 15",
            phone="+7 (999) 123-45-67",
            email="info@myata-sport.ru",
            slogan="Вкус, который запоминается",
            working_hours="Пн-Вс: 12:00 - 02:00"
        )
        doc = default.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.restaurants.insert_one(doc)
        return serialize_doc(doc)
    return serialize_doc(restaurant)

async def get_or_create_settings():
    """Get or create default settings"""
    settings = await db.settings.find_one({"id": "main"}, {"_id": 0})
    if not settings:
        default = Settings()
        doc = default.model_dump()
        await db.settings.insert_one(doc)
        return doc
    return settings

# ============ RESTAURANT ENDPOINTS ============

@api_router.get("/restaurant")
async def get_restaurant():
    return await get_or_create_restaurant()

@api_router.put("/restaurant")
async def update_restaurant(data: RestaurantUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.restaurants.update_one({}, {"$set": update_data})
    return await get_or_create_restaurant()

# ============ CATEGORIES ENDPOINTS ============

@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return [serialize_doc(c) for c in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(data: CategoryCreate):
    category = Category(**data.model_dump())
    doc = category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/categories/{category_id}")
async def update_category(category_id: str, data: CategoryCreate):
    update_data = data.model_dump()
    result = await db.categories.update_one({"id": category_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    category = await db.categories.find_one({"id": category_id}, {"_id": 0})
    return serialize_doc(category)

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    result = await db.categories.delete_one({"id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    # Also delete all menu items in this category
    await db.menu_items.delete_many({"category_id": category_id})
    return {"message": "Category deleted"}

class ReorderItem(BaseModel):
    id: str
    sort_order: int

class ReorderRequest(BaseModel):
    items: List[ReorderItem]

@api_router.put("/categories/reorder")
async def reorder_categories(data: ReorderRequest):
    """Reorder categories by updating their sort_order"""
    for item in data.items:
        await db.categories.update_one(
            {"id": item.id}, 
            {"$set": {"sort_order": item.sort_order}}
        )
    return {"message": "Categories reordered"}

@api_router.put("/menu-items/reorder")
async def reorder_menu_items(data: ReorderRequest):
    """Reorder menu items by updating their sort_order"""
    for item in data.items:
        await db.menu_items.update_one(
            {"id": item.id}, 
            {"$set": {"sort_order": item.sort_order}}
        )
    return {"message": "Menu items reordered"}

# ============ MENU ITEMS ENDPOINTS ============

@api_router.get("/menu-items", response_model=List[MenuItem])
async def get_menu_items(category_id: Optional[str] = None):
    query = {}
    if category_id:
        query["category_id"] = category_id
    items = await db.menu_items.find(query, {"_id": 0}).sort("sort_order", 1).to_list(500)
    return [serialize_doc(i) for i in items]

@api_router.post("/menu-items", response_model=MenuItem)
async def create_menu_item(data: MenuItemCreate):
    item = MenuItem(**data.model_dump())
    doc = item.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.menu_items.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/menu-items/{item_id}")
async def update_menu_item(item_id: str, data: MenuItemUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        result = await db.menu_items.update_one({"id": item_id}, {"$set": update_data})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Menu item not found")
    item = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    return serialize_doc(item)

@api_router.delete("/menu-items/{item_id}")
async def delete_menu_item(item_id: str):
    result = await db.menu_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"message": "Menu item deleted"}

# ============ TABLES ENDPOINTS ============

@api_router.get("/tables", response_model=List[Table])
async def get_tables():
    tables = await db.tables.find({}, {"_id": 0}).sort("number", 1).to_list(100)
    return [serialize_doc(t) for t in tables]

@api_router.post("/tables", response_model=Table)
async def create_table(data: TableCreate):
    table = Table(**data.model_dump())
    doc = table.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tables.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/tables/{table_id}")
async def update_table(table_id: str, data: TableCreate):
    update_data = data.model_dump()
    result = await db.tables.update_one({"id": table_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Table not found")
    table = await db.tables.find_one({"id": table_id}, {"_id": 0})
    return serialize_doc(table)

@api_router.delete("/tables/{table_id}")
async def delete_table(table_id: str):
    result = await db.tables.delete_one({"id": table_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"message": "Table deleted"}

@api_router.post("/tables/{table_id}/regenerate-code")
async def regenerate_table_code(table_id: str):
    new_code = str(uuid.uuid4())[:8].upper()
    result = await db.tables.update_one({"id": table_id}, {"$set": {"code": new_code}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Table not found")
    table = await db.tables.find_one({"id": table_id}, {"_id": 0})
    return serialize_doc(table)

# ============ ORDERS ENDPOINTS ============

@api_router.get("/orders", response_model=List[Order])
async def get_orders(status: Optional[OrderStatus] = None, date: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status.value
    if date:
        query["created_at"] = {"$regex": f"^{date}"}
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(o) for o in orders]

@api_router.post("/orders", response_model=Order)
async def create_order(data: OrderCreate):
    # Find table by code
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Check if online orders are enabled
    settings = await get_or_create_settings()
    if not settings.get("online_orders_enabled", True):
        raise HTTPException(status_code=400, detail="Online orders are disabled")
    
    total = sum(item.price * item.quantity for item in data.items)
    order = Order(
        table_id=table["id"],
        table_number=table["number"],
        items=[item.model_dump() for item in data.items],
        total=total,
        notes=data.notes
    )
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.orders.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, data: OrderStatusUpdate):
    result = await db.orders.update_one({"id": order_id}, {"$set": {"status": data.status.value}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return serialize_doc(order)

# ============ STAFF CALLS ENDPOINTS ============

@api_router.get("/staff-calls", response_model=List[StaffCall])
async def get_staff_calls(status: Optional[StaffCallStatus] = None):
    query = {}
    if status:
        query["status"] = status.value
    calls = await db.staff_calls.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(c) for c in calls]

@api_router.post("/staff-calls", response_model=StaffCall)
async def create_staff_call(data: StaffCallCreate):
    # Find table by code
    table = await db.tables.find_one({"code": data.table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Check if staff calls are enabled
    settings = await get_or_create_settings()
    if not settings.get("staff_call_enabled", True):
        raise HTTPException(status_code=400, detail="Staff calls are disabled")
    
    call = StaffCall(
        table_id=table["id"],
        table_number=table["number"]
    )
    doc = call.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.staff_calls.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/staff-calls/{call_id}/status")
async def update_staff_call_status(call_id: str, status: StaffCallStatus):
    result = await db.staff_calls.update_one({"id": call_id}, {"$set": {"status": status.value}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Staff call not found")
    call = await db.staff_calls.find_one({"id": call_id}, {"_id": 0})
    return serialize_doc(call)

# ============ EMPLOYEES ENDPOINTS ============

@api_router.get("/employees", response_model=List[Employee])
async def get_employees():
    employees = await db.employees.find({}, {"_id": 0}).to_list(100)
    return [serialize_doc(e) for e in employees]

@api_router.post("/employees", response_model=Employee)
async def create_employee(data: EmployeeCreate):
    employee = Employee(**data.model_dump())
    doc = employee.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.employees.insert_one(doc)
    return serialize_doc(doc)

@api_router.put("/employees/{employee_id}")
async def update_employee(employee_id: str, data: EmployeeCreate):
    update_data = data.model_dump()
    result = await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    return serialize_doc(employee)

@api_router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: str):
    result = await db.employees.delete_one({"id": employee_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted"}

# ============ SETTINGS ENDPOINTS ============

@api_router.get("/settings")
async def get_settings():
    return await get_or_create_settings()

@api_router.put("/settings")
async def update_settings(data: SettingsUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.settings.update_one({"id": "main"}, {"$set": update_data}, upsert=True)
    return await get_or_create_settings()

# ============ STATISTICS ENDPOINTS ============

@api_router.get("/stats", response_model=Stats)
async def get_stats():
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    # Views today
    views_today = await db.menu_views.count_documents({
        "created_at": {"$gte": today_start}
    })
    
    # Views this month
    views_month = await db.menu_views.count_documents({
        "created_at": {"$gte": month_start}
    })
    
    # Staff calls today
    calls_today = await db.staff_calls.count_documents({
        "created_at": {"$gte": today_start}
    })
    
    # Staff calls this month
    calls_month = await db.staff_calls.count_documents({
        "created_at": {"$gte": month_start}
    })
    
    # Orders today
    orders_today = await db.orders.count_documents({
        "created_at": {"$gte": today_start}
    })
    
    # Orders this month
    orders_month = await db.orders.count_documents({
        "created_at": {"$gte": month_start}
    })
    
    # Employees count
    employees_count = await db.employees.count_documents({"is_active": True})
    
    return Stats(
        views_today=views_today,
        views_month=views_month,
        calls_today=calls_today,
        calls_month=calls_month,
        orders_today=orders_today,
        orders_month=orders_month,
        employees_count=employees_count
    )

# ============ SUPPORT ENDPOINTS ============

@api_router.get("/support-tickets", response_model=List[SupportTicket])
async def get_support_tickets():
    tickets = await db.support_tickets.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(t) for t in tickets]

@api_router.post("/support-tickets", response_model=SupportTicket)
async def create_support_ticket(data: SupportTicketCreate):
    ticket = SupportTicket(**data.model_dump())
    doc = ticket.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.support_tickets.insert_one(doc)
    return serialize_doc(doc)

# ============ PUBLIC MENU ENDPOINTS (for guests) ============

@api_router.get("/public/menu/{table_code}")
async def get_public_menu(table_code: str):
    # Find table
    table = await db.tables.find_one({"code": table_code, "is_active": True}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    # Get restaurant info
    restaurant = await get_or_create_restaurant()
    
    # Get settings
    settings = await get_or_create_settings()
    
    # Check if online menu is enabled
    if not settings.get("online_menu_enabled", True):
        raise HTTPException(status_code=400, detail="Online menu is disabled")
    
    # Get categories
    categories = await db.categories.find({"is_active": True}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    
    # Get menu items
    items = await db.menu_items.find({"is_available": True}, {"_id": 0}).sort("sort_order", 1).to_list(500)
    
    # Filter items based on settings
    filtered_items = []
    for item in items:
        if item.get("is_business_lunch") and not settings.get("business_lunch_enabled", True):
            continue
        if item.get("is_promotion") and not settings.get("promotions_enabled", True):
            continue
        filtered_items.append(serialize_doc(item))
    
    # Record menu view
    view = MenuView(table_code=table_code)
    view_doc = view.model_dump()
    view_doc['created_at'] = view_doc['created_at'].isoformat()
    await db.menu_views.insert_one(view_doc)
    
    return {
        "table": serialize_doc(table),
        "restaurant": restaurant,
        "settings": settings,
        "categories": [serialize_doc(c) for c in categories],
        "items": filtered_items
    }

# ============ FAQ ENDPOINTS ============

class FAQItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    category: str
    sort_order: int = 0

@api_router.get("/faq", response_model=List[FAQItem])
async def get_faq():
    faqs = await db.faqs.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    if not faqs:
        # Create default FAQs
        default_faqs = [
            FAQItem(question="Как добавить новую позицию в меню?", answer="Перейдите в раздел 'Меню', выберите категорию и нажмите кнопку 'Добавить позицию'. Заполните все необходимые поля и сохраните.", category="Меню", sort_order=1),
            FAQItem(question="Как настроить QR-код для стола?", answer="В разделе 'Настройки' -> 'Столы' вы можете создать стол и получить уникальный код/ссылку для QR-кода.", category="Столы", sort_order=2),
            FAQItem(question="Как включить/выключить онлайн-заказы?", answer="Перейдите в 'Настройки' -> 'Функции' и переключите опцию 'Онлайн-заказы'.", category="Настройки", sort_order=3),
            FAQItem(question="Как подключить Telegram-бота?", answer="В разделе 'Настройки' -> 'Интеграции' введите токен вашего бота и ID чата для получения уведомлений.", category="Интеграции", sort_order=4),
            FAQItem(question="Как изменить тему оформления?", answer="В 'Настройки' -> 'Оформление' выберите светлую или тёмную тему и настройте цвета.", category="Настройки", sort_order=5),
        ]
        for faq in default_faqs:
            await db.faqs.insert_one(faq.model_dump())
        faqs = [f.model_dump() for f in default_faqs]
    return faqs

# ============ SEED DATA ENDPOINT ============

@api_router.post("/seed")
async def seed_data():
    """Seed database with test data"""
    
    # Create restaurant
    await get_or_create_restaurant()
    
    # Create settings
    await get_or_create_settings()
    
    # Create categories if none exist
    existing_categories = await db.categories.count_documents({})
    if existing_categories == 0:
        categories_data = [
            {"name": "Закуски", "sort_order": 1},
            {"name": "Салаты", "sort_order": 2},
            {"name": "Горячее", "sort_order": 3},
            {"name": "Гриль", "sort_order": 4},
            {"name": "Паста", "sort_order": 5},
            {"name": "Десерты", "sort_order": 6},
            {"name": "Напитки", "sort_order": 7},
            {"name": "Кальяны", "sort_order": 8},
        ]
        created_categories = []
        for cat_data in categories_data:
            cat = Category(**cat_data)
            doc = cat.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.categories.insert_one(doc)
            created_categories.append(doc)
        
        # Create menu items
        menu_items_data = [
            {"category_id": created_categories[0]["id"], "name": "Брускетта с томатами", "description": "Хрустящий тост с томатами, базиликом и оливковым маслом", "price": 350, "weight": "150 г", "is_hit": True},
            {"category_id": created_categories[0]["id"], "name": "Карпаччо из говядины", "description": "Тонко нарезанная говядина с рукколой и пармезаном", "price": 590, "weight": "120 г", "is_new": True},
            {"category_id": created_categories[0]["id"], "name": "Сырная тарелка", "description": "Ассорти из 4 видов сыра с мёдом и орехами", "price": 650, "weight": "200 г"},
            
            {"category_id": created_categories[1]["id"], "name": "Цезарь с курицей", "description": "Классический салат с куриной грудкой, сыром пармезан и соусом цезарь", "price": 420, "weight": "250 г", "is_hit": True, "image_url": "https://images.unsplash.com/photo-1765894711192-d35787eee3b6"},
            {"category_id": created_categories[1]["id"], "name": "Греческий салат", "description": "Свежие овощи с сыром фета и оливками", "price": 380, "weight": "220 г"},
            {"category_id": created_categories[1]["id"], "name": "Тёплый салат с говядиной", "description": "Микс салатов с тёплой говядиной и овощами гриль", "price": 520, "weight": "280 г", "is_spicy": True},
            
            {"category_id": created_categories[2]["id"], "name": "Стейк рибай", "description": "Сочный стейк из мраморной говядины", "price": 1890, "weight": "300 г", "is_hit": True},
            {"category_id": created_categories[2]["id"], "name": "Лосось на гриле", "description": "Филе лосося с овощами и лимонным соусом", "price": 890, "weight": "200 г"},
            {"category_id": created_categories[2]["id"], "name": "Куриная грудка", "description": "Сочная куриная грудка с картофельным пюре", "price": 490, "weight": "250 г"},
            
            {"category_id": created_categories[3]["id"], "name": "Шашлык из свинины", "description": "Маринованная свинина на углях с луком", "price": 590, "weight": "250 г"},
            {"category_id": created_categories[3]["id"], "name": "Люля-кебаб", "description": "Из говядины и баранины с лавашом", "price": 450, "weight": "200 г", "is_spicy": True},
            
            {"category_id": created_categories[4]["id"], "name": "Паста Карбонара", "description": "Спагетти с беконом, яйцом и пармезаном", "price": 420, "weight": "300 г", "is_hit": True},
            {"category_id": created_categories[4]["id"], "name": "Паста с морепродуктами", "description": "Феттучине с креветками, мидиями и кальмарами", "price": 620, "weight": "320 г", "is_new": True},
            
            {"category_id": created_categories[5]["id"], "name": "Чизкейк Нью-Йорк", "description": "Классический чизкейк с ягодным соусом", "price": 320, "weight": "150 г"},
            {"category_id": created_categories[5]["id"], "name": "Тирамису", "description": "Итальянский десерт с маскарпоне и кофе", "price": 350, "weight": "160 г", "is_hit": True},
            {"category_id": created_categories[5]["id"], "name": "Мороженое ассорти", "description": "3 шарика мороженого на выбор", "price": 250, "weight": "150 г"},
            
            {"category_id": created_categories[6]["id"], "name": "Мятный лимонад", "description": "Освежающий лимонад с мятой и лаймом", "price": 220, "weight": "400 мл", "is_hit": True, "image_url": "https://images.unsplash.com/photo-1660225411990-6d5a97be1966"},
            {"category_id": created_categories[6]["id"], "name": "Свежевыжатый апельсин", "description": "100% натуральный апельсиновый сок", "price": 280, "weight": "300 мл"},
            {"category_id": created_categories[6]["id"], "name": "Капучино", "description": "Классический итальянский кофе", "price": 180, "weight": "200 мл"},
            {"category_id": created_categories[6]["id"], "name": "Чай в чайнике", "description": "Чёрный, зелёный или травяной чай", "price": 220, "weight": "500 мл"},
            
            {"category_id": created_categories[7]["id"], "name": "Кальян классический", "description": "На выбор: яблоко, виноград, мята, персик", "price": 1200, "weight": ""},
            {"category_id": created_categories[7]["id"], "name": "Кальян премиум", "description": "Авторские миксы от нашего кальянного мастера", "price": 1500, "weight": "", "is_hit": True},
        ]
        
        for item_data in menu_items_data:
            item = MenuItem(**item_data)
            doc = item.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.menu_items.insert_one(doc)
    
    # Create tables if none exist
    existing_tables = await db.tables.count_documents({})
    if existing_tables == 0:
        for i in range(1, 11):
            table = Table(number=i, name=f"Стол {i}")
            doc = table.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.tables.insert_one(doc)
    
    # Create employees if none exist
    existing_employees = await db.employees.count_documents({})
    if existing_employees == 0:
        employees_data = [
            {"name": "Иван Петров", "role": "Официант"},
            {"name": "Мария Сидорова", "role": "Официант"},
            {"name": "Алексей Козлов", "role": "Администратор"},
        ]
        for emp_data in employees_data:
            emp = Employee(**emp_data)
            doc = emp.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.employees.insert_one(doc)
    
    # Create FAQ
    await get_faq()
    
    return {"message": "Data seeded successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
