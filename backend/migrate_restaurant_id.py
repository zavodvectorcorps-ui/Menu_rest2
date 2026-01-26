#!/usr/bin/env python3
"""
Migration script to add restaurant_id to existing data
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]

async def migrate():
    print("Starting migration...")
    
    # Get or create first restaurant
    restaurant = await db.restaurants.find_one({}, {"_id": 0})
    if not restaurant:
        print("No restaurant found, skipping migration")
        return
    
    restaurant_id = restaurant['id']
    print(f"Using restaurant: {restaurant['name']} ({restaurant_id})")
    
    # Collections to migrate
    collections = [
        'menu_sections',
        'categories', 
        'menu_items',
        'tables',
        'orders',
        'staff_calls',
        'call_types',
        'employees',
        'settings',
        'menu_views'
    ]
    
    for coll_name in collections:
        # Update documents without restaurant_id
        result = await db[coll_name].update_many(
            {"restaurant_id": {"$exists": False}},
            {"$set": {"restaurant_id": restaurant_id}}
        )
        print(f"  {coll_name}: updated {result.modified_count} documents")
    
    print("\nMigration completed!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
