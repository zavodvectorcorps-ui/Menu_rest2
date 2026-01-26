#!/usr/bin/env python3
"""
Migration script to update menu sections names and assign categories to sections.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Categories that should be in each section
FOOD_CATEGORIES = [
    "Завтраки до 16.00",
    "Сезонное меню",
    "Суши и роллы", 
    "Салаты",
    "Закуски",
    "Бургеры и Сэндвичи",
    "Супы",
    "Паста",
    "Горячие блюда",
    "Десерты",
    "Гриль",
    "Хиты продаж",
    "Детское меню",
    "Пицца",
    "WOK"
]

DRINKS_CATEGORIES = [
    "Вино",
    "Коктейли",
    "Пиво",
    "Шоты",
    "Крепкое",
    "Безалкогольные напитки",
    "Чай",
    "Кофе",
    "Лимонады",
    "Смузи",
    "Игристое",
    "Виски",
    "Ликёры",
    "Настойки"
]

HOOKAH_CATEGORIES = [
    "Кальяны",
    "Табак",
    "Дополнения к кальяну"
]

async def migrate():
    print("Starting migration...")
    
    # 1. Update existing menu sections or create new ones
    sections_data = [
        {"id": "food", "name": "Еда", "sort_order": 1, "is_active": True},
        {"id": "drinks", "name": "Напитки", "sort_order": 2, "is_active": True},
        {"id": "hookah", "name": "Кальяны", "sort_order": 3, "is_active": True},
    ]
    
    # Delete old sections
    await db.menu_sections.delete_many({})
    print("Deleted old menu sections")
    
    # Insert new sections
    for section in sections_data:
        await db.menu_sections.insert_one(section)
        print(f"Created section: {section['name']}")
    
    # 2. Get all categories
    categories = await db.categories.find({}).to_list(100)
    print(f"\nFound {len(categories)} categories")
    
    # 3. Assign categories to sections
    for cat in categories:
        cat_name = cat.get('name', '')
        new_section_id = None
        
        # Check which section this category belongs to
        for name in FOOD_CATEGORIES:
            if name.lower() in cat_name.lower() or cat_name.lower() in name.lower():
                new_section_id = "food"
                break
        
        if not new_section_id:
            for name in DRINKS_CATEGORIES:
                if name.lower() in cat_name.lower() or cat_name.lower() in name.lower():
                    new_section_id = "drinks"
                    break
        
        if not new_section_id:
            for name in HOOKAH_CATEGORIES:
                if name.lower() in cat_name.lower() or cat_name.lower() in name.lower():
                    new_section_id = "hookah"
                    break
        
        # Default to food if not matched
        if not new_section_id:
            # Check current section_id
            current = cat.get('section_id', '')
            if current == 'bar':
                new_section_id = "drinks"
            elif current == 'hookah':
                new_section_id = "hookah"
            elif current == 'gastro':
                new_section_id = "food"
            else:
                new_section_id = "food"
        
        # Update the category
        await db.categories.update_one(
            {"id": cat['id']},
            {"$set": {"section_id": new_section_id}}
        )
        print(f"  {cat_name} -> {new_section_id}")
    
    # 4. Verify
    print("\n=== Migration complete ===")
    
    sections = await db.menu_sections.find({}).to_list(10)
    for section in sections:
        count = await db.categories.count_documents({"section_id": section['id']})
        print(f"{section['name']}: {count} categories")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
