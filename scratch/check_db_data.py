import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta

MONGO_URI = "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority"

async def check_data():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client["tourism_db"]
    
    # Check total events
    total_events = await db["gate_events"].count_documents({})
    print(f"Total gate events: {total_events}")
    
    # Check today's events (VN time 00:00 is UTC 17:00 yesterday)
    now_vn = datetime.now(timezone(timedelta(hours=7)))
    today_start_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_utc = today_start_vn.astimezone(timezone.utc)
    
    today_events = await db["gate_events"].count_documents({"created_at": {"$gte": today_start_utc}})
    print(f"Today's events (since {today_start_vn} VN / {today_start_utc} UTC): {today_events}")
    
    # Check last 5 events
    print("\nLast 5 events:")
    async for e in db["gate_events"].find().sort("created_at", -1).limit(5):
        print(f"- {e.get('created_at')} | {e.get('direction')} | {e.get('gate_id')} | {e.get('result')}")

    # Check total transactions today
    today_tx = await db["transactions"].count_documents({"timestamp": {"$gte": today_start_utc}})
    print(f"\nToday's transactions: {today_tx}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_data())
