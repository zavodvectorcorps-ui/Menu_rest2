"""Dedicated demo restaurant for the public /demo landing page.

Idempotent: safe to re-run. Identifies its restaurant by `slug == "demo"`
so it never collides with real customer data on production deploys.
"""
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from database import db
from models import (
    Restaurant, Table, MenuSection, Category, MenuItem,
    Order, OrderItem, StaffCall, OrderStatus, StaffCallStatus,
    CallType,
)

log = logging.getLogger(__name__)

DEMO_SLUG = "demo"
DEMO_NAME = "Demo Restaurant"

# ---- Menu data: short, photogenic, mostly self-explanatory ----
SECTIONS = [
    {"name": "Кухня", "name_en": "Kitchen", "sort": 0},
    {"name": "Бар", "name_en": "Bar", "sort": 1},
]

CATEGORIES = [
    # Kitchen
    {"section": "Кухня", "name": "Завтраки", "name_en": "Breakfast"},
    {"section": "Кухня", "name": "Закуски", "name_en": "Starters"},
    {"section": "Кухня", "name": "Салаты", "name_en": "Salads"},
    {"section": "Кухня", "name": "Супы", "name_en": "Soups"},
    {"section": "Кухня", "name": "Паста", "name_en": "Pasta"},
    {"section": "Кухня", "name": "Бургеры", "name_en": "Burgers"},
    {"section": "Кухня", "name": "Десерты", "name_en": "Desserts"},
    # Bar
    {"section": "Бар", "name": "Кофе", "name_en": "Coffee"},
    {"section": "Бар", "name": "Чай", "name_en": "Tea"},
    {"section": "Бар", "name": "Лимонады", "name_en": "Lemonades"},
    {"section": "Бар", "name": "Вино", "name_en": "Wine"},
]

# Curated stock-photo URLs from Unsplash (free for commercial use, hot-link OK)
ITEMS = [
    # Завтраки
    {"cat": "Завтраки", "name": "Сырники со сметаной", "name_en": "Syrniki with sour cream",
     "desc": "Творожные сырники с домашним вареньем и сметаной", "desc_en": "Cottage cheese pancakes with homemade jam and sour cream",
     "price": 14.5, "image": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800", "is_hit": True},
    {"cat": "Завтраки", "name": "Овсяная каша с ягодами", "name_en": "Oatmeal with berries",
     "desc": "На молоке, с черникой, малиной и мёдом", "desc_en": "With milk, blueberries, raspberries and honey",
     "price": 11.0, "image": "https://images.unsplash.com/photo-1517673400267-0251440c45dc?w=800"},
    {"cat": "Завтраки", "name": "Авокадо-тост с яйцом пашот", "name_en": "Avocado toast with poached egg",
     "desc": "На зерновом хлебе, со сметаной и зеленью", "desc_en": "On grain bread with sour cream and herbs",
     "price": 17.5, "image": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=800", "is_new": True},
    # Закуски
    {"cat": "Закуски", "name": "Брускетта с томатами", "name_en": "Tomato bruschetta",
     "desc": "Чиабатта, томаты, базилик, оливковое масло", "desc_en": "Ciabatta, tomatoes, basil, olive oil",
     "price": 13.0, "image": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=800"},
    {"cat": "Закуски", "name": "Сырная тарелка", "name_en": "Cheese platter",
     "desc": "Бри, чеддер, дорблю, мёд, орехи", "desc_en": "Brie, cheddar, blue cheese, honey, nuts",
     "price": 32.0, "image": "https://images.unsplash.com/photo-1452195100486-9cc805987862?w=800"},
    # Салаты
    {"cat": "Салаты", "name": "Цезарь с курицей", "name_en": "Caesar salad with chicken",
     "desc": "Романо, гриль-курица, пармезан, домашний соус", "desc_en": "Romaine, grilled chicken, parmesan, house dressing",
     "price": 19.0, "image": "https://images.unsplash.com/photo-1546793665-c74683f339c1?w=800", "is_hit": True},
    {"cat": "Салаты", "name": "Греческий", "name_en": "Greek salad",
     "desc": "Свежие овощи, фета, оливки, орегано", "desc_en": "Fresh veggies, feta, olives, oregano",
     "price": 16.5, "image": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=800"},
    # Супы
    {"cat": "Супы", "name": "Том ям с креветками", "name_en": "Tom yum with shrimp",
     "desc": "Острый тайский суп с кокосовым молоком", "desc_en": "Spicy Thai soup with coconut milk",
     "price": 22.0, "image": "https://images.unsplash.com/photo-1547592180-85f173990554?w=800", "is_spicy": True},
    {"cat": "Супы", "name": "Грибной крем-суп", "name_en": "Mushroom cream soup",
     "desc": "С трюфельным маслом и гренками", "desc_en": "With truffle oil and croutons",
     "price": 14.0, "image": "https://images.unsplash.com/photo-1547308283-b941640ee5b1?w=800"},
    # Паста
    {"cat": "Паста", "name": "Карбонара", "name_en": "Carbonara",
     "desc": "Спагетти, гуанчале, желток, пармезан", "desc_en": "Spaghetti, guanciale, egg yolk, parmesan",
     "price": 21.0, "image": "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=800", "is_hit": True},
    {"cat": "Паста", "name": "Болоньезе", "name_en": "Bolognese",
     "desc": "С мясным соусом и пармезаном", "desc_en": "With meat sauce and parmesan",
     "price": 19.0, "image": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?w=800"},
    {"cat": "Паста", "name": "Песто с курицей", "name_en": "Pesto with chicken",
     "desc": "Тальятелле, песто, гриль-курица, томаты", "desc_en": "Tagliatelle, pesto, grilled chicken, tomatoes",
     "price": 20.0, "image": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=800"},
    # Бургеры
    {"cat": "Бургеры", "name": "Чизбургер классический", "name_en": "Classic cheeseburger",
     "desc": "200 г говядина, чеддер, лук, бекон, картофель фри", "desc_en": "200 g beef, cheddar, onion, bacon, fries",
     "price": 24.0, "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800", "is_hit": True, "is_takeaway": True},
    {"cat": "Бургеры", "name": "BBQ бургер", "name_en": "BBQ burger",
     "desc": "Говядина, BBQ соус, лук-фри, чеддер, картофель", "desc_en": "Beef, BBQ sauce, onion rings, cheddar, fries",
     "price": 26.0, "image": "https://images.unsplash.com/photo-1572802419224-296b0aeee0d9?w=800", "is_takeaway": True},
    # Десерты
    {"cat": "Десерты", "name": "Чизкейк Нью-Йорк", "name_en": "New York cheesecake",
     "desc": "С ягодным соусом", "desc_en": "With berry sauce",
     "price": 12.0, "image": "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800"},
    {"cat": "Десерты", "name": "Тирамису", "name_en": "Tiramisu",
     "desc": "Классический итальянский десерт", "desc_en": "Classic Italian dessert",
     "price": 13.0, "image": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800"},
    # Кофе
    {"cat": "Кофе", "name": "Эспрессо", "name_en": "Espresso", "desc": "30 мл", "desc_en": "30 ml",
     "price": 4.0, "image": "https://images.unsplash.com/photo-1510707577719-ae7c14805e3a?w=800"},
    {"cat": "Кофе", "name": "Капучино", "name_en": "Cappuccino", "desc": "200 мл", "desc_en": "200 ml",
     "price": 6.5, "image": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=800"},
    {"cat": "Кофе", "name": "Раф", "name_en": "Raf coffee", "desc": "Со сливочным сиропом", "desc_en": "With cream syrup",
     "price": 7.5, "image": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800", "is_hit": True},
    # Чай
    {"cat": "Чай", "name": "Чай с облепихой", "name_en": "Sea buckthorn tea",
     "desc": "Тёплый зимний чайник", "desc_en": "Warm winter pot", "price": 9.0,
     "image": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=800"},
    {"cat": "Чай", "name": "Зелёный жасмин", "name_en": "Green jasmine",
     "desc": "Чайник 600 мл", "desc_en": "600 ml pot", "price": 8.0,
     "image": "https://images.unsplash.com/photo-1556909212-d5b604d0c90d?w=800"},
    # Лимонады
    {"cat": "Лимонады", "name": "Манго-маракуйя", "name_en": "Mango passion",
     "desc": "0.5 л", "desc_en": "0.5 L", "price": 11.0,
     "image": "https://images.unsplash.com/photo-1497534446932-c925b458314e?w=800", "is_hit": True},
    {"cat": "Лимонады", "name": "Малина-базилик", "name_en": "Raspberry basil",
     "desc": "0.5 л", "desc_en": "0.5 L", "price": 10.0,
     "image": "https://images.unsplash.com/photo-1437418747212-8d9709afab22?w=800"},
    # Вино
    {"cat": "Вино", "name": "Каберне Совиньон", "name_en": "Cabernet Sauvignon",
     "desc": "Чили, бокал 175 мл", "desc_en": "Chile, 175 ml glass", "price": 18.0,
     "image": "https://images.unsplash.com/photo-1553361371-9b22f78e8b1d?w=800"},
    {"cat": "Вино", "name": "Просекко", "name_en": "Prosecco",
     "desc": "Италия, бокал 150 мл", "desc_en": "Italy, 150 ml glass", "price": 16.0,
     "image": "https://images.unsplash.com/photo-1547595628-c61a29f496f0?w=800", "is_new": True},
]


async def ensure_demo_restaurant() -> str:
    """Create the demo restaurant if it doesn't exist. Returns its id."""
    existing = await db.restaurants.find_one({"slug": DEMO_SLUG}, {"_id": 0})
    if existing:
        return existing["id"]

    r = Restaurant(
        name=DEMO_NAME,
        slug=DEMO_SLUG,
        description="Демонстрационный ресторан REST-MENU. Полный набор данных для ознакомления с функционалом.",
        address="ул. Демонстрационная, 1",
        phone="+375 (29) 000-00-00",
        email="demo@rest-menu.by",
        slogan="Попробуйте платформу изнутри",
        working_hours="Пн-Вс: 09:00 - 23:00",
        currency="BYN",
        enabled_modules=[],  # base modules only — no Caffesta integration etc.
    )
    doc = r.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.restaurants.insert_one(doc)
    log.info("demo restaurant created: %s", doc["id"])
    return doc["id"]


async def ensure_demo_menu(rid: str) -> dict:
    """Idempotently create demo menu sections, categories and items."""
    # Sections
    section_ids = {}
    for s in SECTIONS:
        existing = await db.menu_sections.find_one({"restaurant_id": rid, "name": s["name"]}, {"_id": 0})
        if existing:
            section_ids[s["name"]] = existing["id"]
            continue
        sec = MenuSection(restaurant_id=rid, name=s["name"], name_en=s["name_en"], sort_order=s["sort"])
        d = sec.model_dump()
        await db.menu_sections.insert_one(d)
        section_ids[s["name"]] = d["id"]

    # Categories
    category_ids = {}
    for idx, c in enumerate(CATEGORIES):
        existing = await db.categories.find_one({"restaurant_id": rid, "name": c["name"]}, {"_id": 0})
        if existing:
            category_ids[c["name"]] = existing["id"]
            continue
        cat = Category(
            restaurant_id=rid, name=c["name"], name_en=c["name_en"],
            section_id=section_ids.get(c["section"]),
            sort_order=idx, display_mode="card",
        )
        d = cat.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        await db.categories.insert_one(d)
        category_ids[c["name"]] = d["id"]

    # Items
    items_created = 0
    for idx, it in enumerate(ITEMS):
        existing = await db.menu_items.find_one(
            {"restaurant_id": rid, "name": it["name"]}, {"_id": 0, "id": 1}
        )
        if existing:
            continue
        cat_id = category_ids.get(it["cat"])
        if not cat_id:
            continue
        item = MenuItem(
            restaurant_id=rid, category_id=cat_id,
            name=it["name"], name_en=it.get("name_en", ""),
            description=it.get("desc", ""), description_en=it.get("desc_en", ""),
            price=it["price"], image_url=it.get("image", ""),
            is_hit=it.get("is_hit", False),
            is_new=it.get("is_new", False),
            is_spicy=it.get("is_spicy", False),
            is_takeaway=it.get("is_takeaway", False),
            sort_order=idx, is_available=True,
        )
        d = item.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        await db.menu_items.insert_one(d)
        items_created += 1

    return {"sections": len(section_ids), "categories": len(category_ids), "items_created": items_created}


async def ensure_demo_tables(rid: str) -> List[dict]:
    """8 tables with QR codes."""
    existing = await db.tables.count_documents({"restaurant_id": rid})
    if existing >= 8:
        return await db.tables.find({"restaurant_id": rid}, {"_id": 0}).to_list(20)
    out = []
    for i in range(1, 9):
        already = await db.tables.find_one({"restaurant_id": rid, "number": i}, {"_id": 0})
        if already:
            out.append(already); continue
        t = Table(restaurant_id=rid, number=i, name=f"Стол {i}")
        d = t.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        await db.tables.insert_one(d)
        out.append(d)
    return out


async def ensure_demo_call_types(rid: str):
    if await db.call_types.count_documents({"restaurant_id": rid}) > 0:
        return
    presets = [
        {"name": "Официант", "name_en": "Waiter", "msg": "Гость зовёт официанта"},
        {"name": "Счёт", "name_en": "Bill", "msg": "Гость просит счёт"},
        {"name": "Уточнение", "name_en": "Question", "msg": "У гостя вопрос"},
    ]
    for i, p in enumerate(presets):
        ct = CallType(restaurant_id=rid, name=p["name"], name_en=p["name_en"], telegram_message=p["msg"], sort_order=i)
        await db.call_types.insert_one(ct.model_dump())


async def ensure_demo_orders_and_calls(rid: str, tables: List[dict]):
    """Generate fake orders + staff calls in the past 7 days for analytics depth."""
    if await db.orders.count_documents({"restaurant_id": rid}) >= 30:
        return  # already populated

    items = await db.menu_items.find({"restaurant_id": rid}, {"_id": 0}).to_list(200)
    if not items or not tables:
        return

    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    statuses = [OrderStatus.NEW, OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED, OrderStatus.COMPLETED, OrderStatus.COMPLETED]

    for _ in range(45):
        days_ago = rng.randint(0, 6)
        hours_ago = rng.randint(0, 23)
        ts = now - timedelta(days=days_ago, hours=hours_ago, minutes=rng.randint(0, 59))
        table = rng.choice(tables)
        n_items = rng.randint(1, 4)
        order_items = []
        total = 0.0
        for it in rng.sample(items, n_items):
            qty = rng.randint(1, 3)
            order_items.append(OrderItem(menu_item_id=it["id"], name=it["name"], quantity=qty, price=it["price"]).model_dump())
            total += qty * it["price"]
        order = Order(
            restaurant_id=rid,
            table_id=table["id"],
            table_number=table["number"],
            items=[],  # will set raw dicts below
            total=round(total, 2),
            status=rng.choice(statuses),
        )
        d = order.model_dump()
        d["items"] = order_items
        d["created_at"] = ts.isoformat()
        await db.orders.insert_one(d)

    # Staff calls
    if await db.staff_calls.count_documents({"restaurant_id": rid}) >= 15:
        return
    call_types = await db.call_types.find({"restaurant_id": rid}, {"_id": 0}).to_list(10)
    for _ in range(20):
        days_ago = rng.randint(0, 6)
        ts = now - timedelta(days=days_ago, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        table = rng.choice(tables)
        ct = rng.choice(call_types) if call_types else None
        sc = StaffCall(
            restaurant_id=rid,
            table_id=table["id"], table_number=table["number"],
            call_type_id=ct["id"] if ct else None,
            call_type_name=ct["name"] if ct else None,
            status=StaffCallStatus.RESOLVED if rng.random() < 0.8 else StaffCallStatus.PENDING,
        )
        d = sc.model_dump()
        d["created_at"] = ts.isoformat()
        await db.staff_calls.insert_one(d)

    # Menu views — 4-8x orders for realism
    for _ in range(180):
        days_ago = rng.randint(0, 6)
        ts = now - timedelta(days=days_ago, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        table = rng.choice(tables)
        await db.menu_views.insert_one({
            "id": f"v_{rng.randint(0, 1_000_000_000)}",
            "restaurant_id": rid,
            "table_id": table["id"],
            "table_number": table["number"],
            "created_at": ts.isoformat(),
        })


async def seed_demo_restaurant() -> str:
    """Idempotent: create + populate demo restaurant. Returns its id."""
    from helpers import get_or_create_settings  # local to avoid cycles
    rid = await ensure_demo_restaurant()
    await get_or_create_settings(rid)
    await ensure_demo_call_types(rid)
    tables = await ensure_demo_tables(rid)
    await ensure_demo_menu(rid)
    await ensure_demo_orders_and_calls(rid, tables)
    return rid
