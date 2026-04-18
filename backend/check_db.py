import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient('mongodb+srv://admin:admin123@cluster0.vpkli.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
    db = client['test']
    review = await db['reviews'].find_one({"ticket_id": "c54d07e7-f3dd-4a9e-bd25-90fe5e61f37b"})
    print("REVIEW EXISTS:", review is not None)
    if review:
        print("REVIEW DATA:", review)
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
