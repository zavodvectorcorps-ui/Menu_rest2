import os
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
RID = "aa25189d-d668-4838-915a-c5d936547f3f"


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    # Fixed known UTC instants (naive-in-UTC as Motor stores them)
    synced = datetime(2026, 7, 15, 19, 11, 0, tzinfo=timezone.utc)
    polled = datetime(2026, 7, 15, 19, 25, 0, tzinfo=timezone.utc)
    res = await db.loyalty_config.update_one(
        {"restaurant_id": RID},
        {"$set": {"last_synced_at": synced, "last_polled_at": polled}},
    )
    print("matched", res.matched_count, "modified", res.modified_count)
    doc = await db.loyalty_config.find_one({"restaurant_id": RID}, {"_id": 0, "last_synced_at": 1, "last_polled_at": 1})
    print(doc)
    client.close()


asyncio.run(main())
