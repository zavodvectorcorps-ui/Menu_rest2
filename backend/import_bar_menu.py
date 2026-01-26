"""
Import bar menu data
"""
import asyncio
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Bar menu data
BAR_MENU = [
    {
        "category": "Коктейли Планеты",
        "dishes": [
            {"name": "Юпитер", "description": "Сливочный коктейль на основе ликера Калуа и Бейлис", "price": "25", "weight": "115ml"},
            {"name": "Сатурн", "description": "Авторский вариант виски-сауэр", "price": "25", "weight": "130ml"},
            {"name": "Венера", "description": "Коктейль на основе текилы с травяным ароматом", "price": "25", "weight": "160ml"},
            {"name": "Земля", "description": "Коктейль на основе белого рома с чайно-цветочным ароматом", "price": "25", "weight": "110ml"},
            {"name": "Меркурий", "description": "Сауэр на основе водки с ягодным послевкусием", "price": "25", "weight": "130ml"},
            {"name": "Марс", "description": "Авторская вариация коктейля Апероль Спритц", "price": "25", "weight": "200ml"},
            {"name": "Плутон", "description": "Коктейль на основе джина с ягодным вкусом", "price": "25", "weight": "90ml"},
            {"name": "Уран", "description": "Коктейль на основе джина с лесным ароматом", "price": "25", "weight": "90ml"},
            {"name": "Нептун", "description": "Тропический коктейль на основе рома с нотками красного вина", "price": "25", "weight": "140ml"},
        ]
    },
    {
        "category": "Авторские коктейли",
        "dishes": [
            {"name": "Родственная Душа", "description": "Уникальный коктейль на основе рома с кокосовым послевкусием", "price": "18", "weight": "250ml"},
            {"name": "Уайт сауэр", "description": "Твист на классический виски сауэр с нотами белого шоколада", "price": "20", "weight": "200ml"},
            {"name": "Ягодный шнапс", "description": "Крепкий коктейль на основе виски с ягодными нотами", "price": "20", "weight": "250ml"},
            {"name": "Эскобар", "description": "Черный ром с оттенками кофе и карамели", "price": "20", "weight": "150ml"},
            {"name": "Банана Стар", "description": "Банановый вариант Мартини порнстар", "price": "20", "weight": "150ml"},
            {"name": "Центурион", "description": "Крепкий цитрусовый коктейль с игристыми нотками", "price": "22", "weight": "250ml"},
            {"name": "Назад в прошлое", "description": "Освежающий коктейль на основе джина с травяными нотами", "price": "20", "weight": "200ml"},
            {"name": "Непростой виски", "description": "Шотландский виски с пюре груши и игристым вином", "price": "20", "weight": "200ml"},
            {"name": "Тропическая фея", "description": "Большой коктейль с кокосом, маракуйей и ананасом", "price": "40", "weight": "1000ml"},
            {"name": "Я не такая", "description": "Сладкий коктейль с ромом, клубникой и сливками", "price": "20", "weight": "150ml"},
            {"name": "Помпеи", "description": "Дымный и острый коктейль", "price": "20", "weight": "150ml"},
            {"name": "Убийца Мерри", "description": "Пикантный твист на кровавую мерри", "price": "18", "weight": "200ml"},
            {"name": "Текила Тропикано", "description": "Вариация Маргариты с Драгон фрут", "price": "22", "weight": "200ml"},
        ]
    },
    {
        "category": "Коктейли Зодиака",
        "dishes": [
            {"name": "Овен", "description": "Джин, лемонграс, клюква", "price": "16", "weight": "300ml"},
            {"name": "Телец", "description": "Red Bull, красный вермут, пряный ром", "price": "19", "weight": "400ml"},
            {"name": "Близнецы", "description": "Джин, грейпфрут, кокос", "price": "17", "weight": "400ml"},
            {"name": "Рак", "description": "Джин на помело, яблоко, тоник", "price": "17", "weight": "150ml"},
            {"name": "Лев", "description": "Апероль, грейпфрут, сауэр микс", "price": "16", "weight": "150ml"},
            {"name": "Дева", "description": "Ром, арбуз, сауэр микс", "price": "15", "weight": "150ml"},
            {"name": "Весы", "description": "Ром, бабл гам, персик, сауэр микс", "price": "17", "weight": "300ml"},
            {"name": "Скорпион", "description": "Текила, личи, чили, манго", "price": "17", "weight": "300ml"},
            {"name": "Стрелец", "description": "Апероль, игристое вино, маракуйя", "price": "16", "weight": "400ml"},
            {"name": "Козерог", "description": "Грецкий орех, зубровка, бергамот", "price": "15", "weight": "150ml"},
            {"name": "Водолей", "description": "Джин, яблоко, фалернум, мята", "price": "16", "weight": "300ml"},
            {"name": "Рыбы", "description": "Мята, игристое вино, бузина", "price": "16", "weight": "400ml"},
        ]
    },
    {
        "category": "Фирменные настойки",
        "dishes": [
            {"name": "Кокос", "price": "6", "weight": "40мл"},
            {"name": "Клубника-базилик", "price": "6", "weight": "40мл"},
            {"name": "Цитрусовая", "price": "6", "weight": "40мл"},
            {"name": "Банановая", "price": "6", "weight": "40мл"},
            {"name": "Солёная карамель", "price": "6", "weight": "40мл"},
            {"name": "Томатная", "price": "6", "weight": "40мл"},
            {"name": "Хреновуха", "price": "6", "weight": "40мл"},
            {"name": "Огуречная", "price": "6", "weight": "40мл"},
            {"name": "Копченая вишня", "price": "6", "weight": "40мл"},
            {"name": "Зубровка", "price": "6", "weight": "40мл"},
            {"name": "Сет сладких настоек", "description": "Кокос, солёная карамель, клубника-базилик, цитрусовая, банановая", "price": "30", "weight": "200мл"},
            {"name": "Сет крепких настоек", "description": "Копченая вишня, огуречная, томатная, зубровка, хреновуха", "price": "30", "weight": "200мл"},
            {"name": "Супер сет", "description": "10 шотов на ваш выбор", "price": "60", "weight": "400мл"},
            {"name": "Графин фирменной настойки", "price": "27.5", "weight": "200мл"},
        ]
    },
    {
        "category": "Шоты",
        "dishes": [
            {"name": "B-52", "price": "17", "weight": "50мл"},
            {"name": "Губерт", "price": "17", "weight": "50мл"},
            {"name": "Хай джо", "price": "18", "weight": "50мл"},
            {"name": "Текила бум", "price": "17", "weight": "50мл"},
            {"name": "Слёзы змеи", "price": "18", "weight": "50мл"},
            {"name": "Баскетбол", "price": "12", "weight": "50мл"},
        ]
    },
    {
        "category": "Виски",
        "dishes": [
            {"name": "The Glenlivet Founders Reserve", "description": "Солодовый виски", "price": "19", "weight": "50мл"},
            {"name": "Monkey Shoulder", "description": "Солодовый виски", "price": "20", "weight": "40мл"},
            {"name": "Glenfiddich 12", "description": "Солодовый виски", "price": "21", "weight": "40мл"},
            {"name": "Laphroaig", "description": "Солодовый виски", "price": "25", "weight": "40мл"},
            {"name": "Macallan 12", "description": "Солодовый виски", "price": "24", "weight": "50мл"},
            {"name": "Talisker 10", "description": "Солодовый виски", "price": "21", "weight": "40мл"},
            {"name": "Label 5", "description": "Шотландия", "price": "10", "weight": "40мл"},
            {"name": "Chivas 12", "description": "Шотландия", "price": "16", "weight": "40мл"},
            {"name": "Jameson", "description": "Ирландия", "price": "15", "weight": "50мл"},
            {"name": "Jack Daniel's", "description": "США", "price": "15", "weight": "40мл"},
            {"name": "Jim Beam", "description": "США", "price": "12", "weight": "40мл"},
            {"name": "Nikka Days", "description": "Япония", "price": "19", "weight": "40мл"},
        ]
    },
    {
        "category": "Водка",
        "dishes": [
            {"name": "Platan", "price": "7", "weight": "50мл"},
            {"name": "Bulbash №1", "price": "7", "weight": "40мл"},
            {"name": "Finlandia", "price": "10", "weight": "40мл"},
            {"name": "Finlandia Cranberry", "price": "10", "weight": "40мл"},
            {"name": "Gray Goose", "price": "19", "weight": "40мл"},
        ]
    },
    {
        "category": "Ром",
        "dishes": [
            {"name": "Bacardi Carta Blanca", "price": "12", "weight": "40мл"},
            {"name": "Bacardi Carta Negra", "price": "12", "weight": "40мл"},
            {"name": "Captain Morgan Spiced", "price": "12", "weight": "40мл"},
            {"name": "Angostura Tamboo", "price": "17", "weight": "50мл"},
            {"name": "Plantation Pineapple", "price": "16", "weight": "40мл"},
            {"name": "Matusalem 15", "price": "19", "weight": "50мл"},
        ]
    },
    {
        "category": "Текила",
        "dishes": [
            {"name": "Olmeca Silver", "price": "15", "weight": "40мл"},
            {"name": "Olmeca Gold", "price": "15", "weight": "40мл"},
            {"name": "Jose Cuervo", "price": "15", "weight": "40мл"},
            {"name": "Hacienda De Tepa Reposado", "price": "15", "weight": "40мл"},
            {"name": "Mezcal Escondida", "price": "21", "weight": "40мл"},
        ]
    },
    {
        "category": "Джин",
        "dishes": [
            {"name": "Bickens", "price": "12", "weight": "40мл"},
            {"name": "Bombay", "price": "14", "weight": "40мл"},
            {"name": "Tanqueray", "price": "14", "weight": "40мл"},
            {"name": "MOM", "price": "16", "weight": "40мл"},
        ]
    },
    {
        "category": "Ликёры",
        "dishes": [
            {"name": "Jägermeister", "price": "13", "weight": "40мл"},
            {"name": "Fireball", "price": "13", "weight": "50мл"},
            {"name": "Campari", "price": "12", "weight": "40мл"},
            {"name": "Becherovka", "price": "11", "weight": "40мл"},
            {"name": "Amaretto", "price": "14", "weight": "40мл"},
            {"name": "Kahlua", "price": "10", "weight": "40мл"},
            {"name": "Sambuka", "price": "12", "weight": "40мл"},
            {"name": "Aperol", "price": "10", "weight": "40мл"},
            {"name": "Absinthe", "price": "16", "weight": "50мл"},
        ]
    },
    {
        "category": "Коньяк",
        "dishes": [
            {"name": "Араспел 5", "price": "10", "weight": "40мл"},
            {"name": "Torres 10", "price": "14", "weight": "40мл"},
            {"name": "Courvoisier VS", "price": "22", "weight": "50мл"},
            {"name": "Courvoisier VSOP", "price": "29", "weight": "50мл"},
            {"name": "Remy Martin VSOP", "price": "28", "weight": "40мл"},
            {"name": "Martell Cohiba", "price": "65", "weight": "50мл"},
        ]
    },
    {
        "category": "Вино красное",
        "dishes": [
            {"name": "B&G Merlot Reserve", "description": "Бокал", "price": "16", "weight": "125мл"},
            {"name": "Vivo Amato Tempranillo", "description": "Бокал", "price": "15", "weight": "125мл"},
            {"name": "Campo Viejo", "description": "Бокал", "price": "14", "weight": "125мл"},
            {"name": "Corte Giara Valpolicella", "description": "Бутылка", "price": "162", "weight": "750мл"},
        ]
    },
    {
        "category": "Вино белое",
        "dishes": [
            {"name": "Lorenzo Moscatti Trebbiano", "description": "Бокал, Italy", "price": "12", "weight": "125мл"},
            {"name": "Das Ist Gewurztraminer", "description": "Бокал", "price": "15", "weight": "125мл"},
            {"name": "Bolla Pinot Grigio", "description": "Бокал, Italy", "price": "18", "weight": "125мл"},
            {"name": "Torres Vina Esmeralda", "description": "Бокал", "price": "18", "weight": "125мл"},
            {"name": "Campo Viejo", "description": "Бутылка, Spain", "price": "84", "weight": "750мл"},
            {"name": "Curly Sheep Sauvignon Blanc", "description": "Бутылка", "price": "108", "weight": "750мл"},
        ]
    },
    {
        "category": "Игристые вина",
        "dishes": [
            {"name": "Provetto Brut", "description": "Бокал", "price": "12", "weight": "125мл"},
            {"name": "Provetto Rose", "description": "Бокал, розовое", "price": "12", "weight": "125мл"},
            {"name": "Baron D'arignac", "description": "Бокал, France, п/сух", "price": "10", "weight": "125мл"},
            {"name": "Bellisco Cava", "description": "Бутылка, Spain", "price": "90", "weight": "750мл"},
            {"name": "Prosecco", "description": "Бутылка, Italy, Brut", "price": "96", "weight": "750мл"},
            {"name": "Gancia Asti", "description": "Бутылка", "price": "102", "weight": "750мл"},
        ]
    },
    {
        "category": "Шампанское",
        "dishes": [
            {"name": "Moet & Chandon Brut", "price": "450", "weight": "750мл"},
            {"name": "Mumm Brut", "price": "300", "weight": "750мл"},
        ]
    },
    {
        "category": "Пиво разливное",
        "dishes": [
            {"name": "Tuborg Green 0.3", "price": "5", "weight": "300мл"},
            {"name": "Tuborg Green 0.5", "price": "8", "weight": "500мл"},
            {"name": "Alivaria White Gold 0.3", "price": "5", "weight": "300мл"},
            {"name": "Alivaria White Gold 0.5", "price": "8", "weight": "500мл"},
            {"name": "Old Bobby 0.3", "price": "5", "weight": "300мл"},
            {"name": "Old Bobby 0.5", "price": "8", "weight": "500мл"},
        ]
    },
    {
        "category": "Пиво бутылочное",
        "dishes": [
            {"name": "Corona Extra", "price": "13", "weight": "330мл"},
            {"name": "Kronenbourg 1664 Blanc", "price": "9", "weight": "460мл"},
            {"name": "Лидское Premium светлое", "price": "10", "weight": "450мл"},
            {"name": "Лидское Бархатное тёмное", "price": "10", "weight": "450мл"},
            {"name": "Лидское Пшеничное", "price": "10", "weight": "450мл"},
            {"name": "Лидское Hoppy Lager", "price": "8", "weight": "450мл"},
            {"name": "Лидское 0 (безалкогольное)", "price": "9", "weight": "450мл"},
        ]
    },
    {
        "category": "Чай",
        "dishes": [
            {"name": "Ассам", "description": "Красный чай", "price": "17", "weight": ""},
            {"name": "Дянь хун", "description": "Красный чай", "price": "20", "weight": ""},
            {"name": "Тегуанинь", "description": "Улун", "price": "18", "weight": ""},
            {"name": "Молочный улун", "description": "Улун", "price": "18", "weight": ""},
            {"name": "Да хун пао", "description": "Улун", "price": "20", "weight": ""},
            {"name": "Габа", "description": "Улун", "price": "23", "weight": ""},
            {"name": "Иван чай", "description": "Травяной", "price": "17", "weight": ""},
            {"name": "Ройбосс", "description": "Травяной", "price": "17", "weight": ""},
            {"name": "Каркадэ", "description": "Травяной", "price": "17", "weight": ""},
            {"name": "Шу пуэр", "description": "Пуэр", "price": "20", "weight": ""},
            {"name": "Шен пуэр", "description": "Пуэр", "price": "20", "weight": ""},
            {"name": "Вишневый шу пуэр", "description": "Пуэр", "price": "25", "weight": ""},
            {"name": "Масала", "price": "25", "weight": ""},
        ]
    },
    {
        "category": "Кофе",
        "dishes": [
            {"name": "Espresso", "price": "6", "weight": "30мл"},
            {"name": "Americano", "price": "6", "weight": "90мл"},
            {"name": "Cappuccino", "price": "7", "weight": "150мл"},
            {"name": "Double Cappuccino", "price": "8", "weight": "200мл"},
            {"name": "Latte", "price": "7", "weight": "250мл"},
            {"name": "Flat White", "price": "8", "weight": "200мл"},
            {"name": "Raf", "price": "8", "weight": "250мл"},
            {"name": "Mokko", "price": "7", "weight": "250мл"},
            {"name": "Matcha Cappuccino", "price": "7", "weight": "200мл"},
        ]
    },
    {
        "category": "Безалкогольные напитки",
        "dishes": [
            {"name": "Coca-Cola", "price": "6", "weight": "330мл"},
            {"name": "Sprite", "price": "6", "weight": "330мл"},
            {"name": "Schweppes Tonic", "price": "6", "weight": "330мл"},
            {"name": "Боровая (газ/негаз)", "price": "6", "weight": "330мл"},
            {"name": "Borjomi", "price": "7", "weight": "330мл"},
            {"name": "RedBull", "price": "12", "weight": "250мл"},
            {"name": "Сок Rich (в ассортименте)", "description": "Апельсин, яблоко, вишня, томат, персик", "price": "5", "weight": "250мл"},
            {"name": "Свежевыжатый апельсин", "price": "12", "weight": "200мл"},
            {"name": "Свежевыжатый грейпфрут", "price": "12", "weight": "200мл"},
        ]
    },
]

async def import_bar_menu():
    # Get current max sort order
    last_category = await db.categories.find_one(sort=[("sort_order", -1)])
    start_order = (last_category["sort_order"] + 1) if last_category else 13
    
    print("Importing bar menu data...")
    
    for idx, category_data in enumerate(BAR_MENU):
        category_id = str(uuid.uuid4())
        category = {
            "id": category_id,
            "name": category_data["category"],
            "sort_order": start_order + idx,
            "is_active": True
        }
        await db.categories.insert_one(category)
        print(f"Created category: {category_data['category']}")
        
        for item_order, dish in enumerate(category_data["dishes"], start=1):
            price_str = dish.get("price", "0")
            try:
                price = float(price_str)
            except:
                price = 0.0
            
            menu_item = {
                "id": str(uuid.uuid4()),
                "category_id": category_id,
                "name": dish["name"],
                "description": dish.get("description", ""),
                "price": price,
                "weight": dish.get("weight", ""),
                "image_url": "",
                "is_available": True,
                "is_business_lunch": False,
                "is_promotion": False,
                "is_hit": item_order <= 2,
                "is_new": False,
                "is_spicy": False,
                "sort_order": item_order
            }
            await db.menu_items.insert_one(menu_item)
        
        print(f"  Added {len(category_data['dishes'])} items")
    
    print("\nBar menu import completed!")
    
    categories_count = await db.categories.count_documents({})
    items_count = await db.menu_items.count_documents({})
    print(f"Total categories: {categories_count}")
    print(f"Total menu items: {items_count}")

if __name__ == "__main__":
    asyncio.run(import_bar_menu())
