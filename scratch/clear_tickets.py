import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Cấu hình UTF-8 cho console
sys.stdout.reconfigure(encoding='utf-8')

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority")
DB_NAME = "tourism_db"


async def clear_all_tickets():
    print("--- 🗑️ ĐANG DỌN DẸP TOÀN BỘ VÉ VÀ DỮ LIỆU LIÊN QUAN ---")
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Xóa toàn bộ Tickets
        tickets_col = db["tickets"]
        result_tickets = await tickets_col.delete_many({})
        print(f"✅ Đã xóa {result_tickets.deleted_count} vé (tickets) khỏi cơ sở dữ liệu.")
        
        # 2. Xóa toàn bộ Identities (Dữ liệu khuôn mặt bị mồ côi do xóa vé)
        identities_col = db["identities"]
        result_identities = await identities_col.delete_many({})
        print(f"✅ Đã xóa {result_identities.deleted_count} dữ liệu danh tính khuôn mặt (identities).")
        
        print("\n🎉 Dọn dẹp thành công! Hệ thống của bạn đã ở trạng thái trống và sẵn sàng Demo vòng mới.")
    except Exception as e:
        print(f"❌ Lỗi khi dọn dẹp Database: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(clear_all_tickets())
