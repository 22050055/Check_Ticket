import asyncio
import os
import sys
from datetime import datetime
from uuid import uuid4
from motor.motor_asyncio import AsyncIOMotorClient

# Cấu hình UTF-8 cho console
sys.stdout.reconfigure(encoding='utf-8')

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority")
DB_NAME = "tourism_db"

async def seed_data():
    print("--- 📥 ĐANG KHỞI TẠO DỮ LIỆU DEMO VÀO MONGODB ---")
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        
        # 1. Tạo 1 Customer (nếu chưa có)
        customer_id = "customer_demo_001"
        await db["customers"].update_one(
            {"_id": customer_id},
            {"$set": {
                "name": "Khang (Demo Customer)",
                "phone_number": "0987654321",
                "email": "demo@example.com",
                "id_card": "123456789012",
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        print("✅ Đã tạo Customer (id: customer_demo_001)")

        # 2. Tạo 1 Vé (Ticket) cho Customer này để họ có thể nhận diện khuôn mặt
        ticket_id = "TICKET-" + str(uuid4())[:8].upper()
        # Để đảm bảo nó được phép Enroll, vé phải là 'active'
        await db["tickets"].insert_one({
            "_id": ticket_id,
            "customer_id": customer_id,
            "ticket_type": "Adult",
            "price": 150000,
            "status": "active",
            "purchased_at": datetime.utcnow(),
            "valid_until": datetime.utcnow().replace(year=datetime.utcnow().year + 1), # Hạn tới năm sau
            "entry_method": "qr"
        })
        print(f"✅ Đã tạo 01 Vé hợp lệ (ID: {ticket_id}) - Đang Active!")
        
        # 3. Tạo 1 Staff (Operator) để lỡ như bạn cần login Web Dashboard
        # Tạo password băm giả / plaintext (Tùy logic backend, nhưng ở đây có thể tạo auth đơn giản)
        # Vì ta không biết hàm băm thuật toán gì, nên ta chỉ tạo sẵn ticket thôi
        
        print("\n🎉 Khởi tạo dữ liệu thành công! HÃY SỬ DỤNG MÃ VÉ SAU CHO APP MOBILE:")
        print("=========================================")
        print(f"🎫 TICKET ID: {ticket_id}")
        print("=========================================")
        print("Hãy nhét mã này vào App hoặc tạo QR Code chứa nội dung này để App Android cho phép quét/đăng ký khuôn mặt nhé!")

    except Exception as e:
        print(f"❌ Lỗi khi Seed Data: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
