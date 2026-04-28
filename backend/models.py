from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone
import uuid


# ============ ENUMS ============

class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMINISTRATOR = "administrator"
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


# ============ USER MODELS ============

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


# ============ RESTAURANT MODELS ============

class Restaurant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: Optional[str] = ""
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
    slug: Optional[str] = ""
    description: Optional[str] = ""
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    working_hours: Optional[str] = None
    slogan: Optional[str] = None


# ============ MENU MODELS ============

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

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    section_id: Optional[str] = None
    display_mode: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

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
    caffesta_product_id: Optional[int] = None
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
    caffesta_product_id: Optional[int] = None

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
    caffesta_product_id: Optional[int] = None

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


# ============ TABLE MODELS ============

class Table(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    number: int
    code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    name: Optional[str] = ""
    is_active: bool = True
    is_preorder: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TableCreate(BaseModel):
    number: int
    name: Optional[str] = ""
    is_active: bool = True
    is_preorder: bool = False


# ============ ORDER MODELS ============

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
    is_preorder: bool = False
    customer_name: Optional[str] = ""
    customer_phone: Optional[str] = ""
    preorder_date: Optional[str] = ""
    preorder_time: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderCreate(BaseModel):
    table_code: str
    items: List[OrderItem]
    notes: Optional[str] = ""
    customer_name: Optional[str] = ""
    customer_phone: Optional[str] = ""
    preorder_date: Optional[str] = ""
    preorder_time: Optional[str] = ""

class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ============ STAFF CALL MODELS ============

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


# ============ EMPLOYEE MODELS ============

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


# ============ SETTINGS MODELS ============

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
    # Splash screen (welcome / promo)
    splash_enabled: bool = False
    splash_image_url: Optional[str] = ""
    splash_title: Optional[str] = ""
    splash_text: Optional[str] = ""
    splash_button_text: Optional[str] = "Перейти к меню"
    splash_link_url: Optional[str] = ""
    splash_link_text: Optional[str] = ""
    splash_fit_mode: Optional[str] = "contain"  # "contain" | "cover"
    # Margin control
    margin_threshold_default: int = 30
    margin_alerts_enabled: bool = False
    margin_alerts_bot_token: Optional[str] = ""
    margin_alerts_chat_id: Optional[str] = ""
    # Daily Telegram digest (Caffesta sales summary)
    daily_digest_enabled: bool = False
    daily_digest_bot_token: Optional[str] = ""
    daily_digest_chat_id: Optional[str] = ""
    daily_digest_windows: list = []  # [{name, time_from, time_to}] up to 4

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
    splash_enabled: Optional[bool] = None
    splash_image_url: Optional[str] = None
    splash_title: Optional[str] = None
    splash_text: Optional[str] = None
    splash_button_text: Optional[str] = None
    splash_link_url: Optional[str] = None
    splash_link_text: Optional[str] = None
    splash_fit_mode: Optional[str] = None
    margin_threshold_default: Optional[int] = None
    margin_alerts_enabled: Optional[bool] = None
    margin_alerts_bot_token: Optional[str] = None
    margin_alerts_chat_id: Optional[str] = None
    daily_digest_enabled: Optional[bool] = None
    daily_digest_bot_token: Optional[str] = None
    daily_digest_chat_id: Optional[str] = None
    daily_digest_windows: Optional[list] = None

class MenuView(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    restaurant_id: str
    table_code: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============ TELEGRAM MODELS ============

class TelegramBotUpdate(BaseModel):
    telegram_bot_token: str

class ImportMenuRequest(BaseModel):
    data: dict
    mode: str = "append"
