import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority")
DB_NAME = "tourism_db"

async def check():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Lấy thử 1 operator/admin user
    staff = await db["staff"].find_one()
    if staff:
        print(f"STAFF FOUND: username={staff.get('username')}, role={staff.get('role')}")
    else:
        # Lấy customer
        customer = await db["customers"].find_one()
        if customer:
            print(f"CUSTOMER FOUND: phone={customer.get('phone_number')}")
        else:
            print("NO USERS FOUND")

if __name__ == "__main__":
    asyncio.run(check())
