import asyncio
import os
import sys
import base64
import httpx
import cv2
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


sys.stdout.reconfigure(encoding='utf-8')

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority")
DB_NAME = "tourism_db"

# Khởi tạo ảnh ảo (mặt ảo)
dummy_img = np.zeros((320, 320, 3), dtype=np.uint8)
cv2.circle(dummy_img, (160, 160), 80, (255, 255, 255), -1)
cv2.circle(dummy_img, (130, 140), 10, (0, 0, 0), -1)
cv2.circle(dummy_img, (190, 140), 10, (0, 0, 0), -1)
cv2.ellipse(dummy_img, (160, 200), (30, 10), 0, 0, 180, (0, 0, 255), -1)
_, buffer = cv2.imencode('.jpg', dummy_img)
dummy_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

async def simulate_e2e():
    print("--- 🤖 CHẠY KỊCH BẢN SIMULATOR E2E ---")
    
    # 1. Đảm bảo có User Admin trong DB (để login HTTPS)
    print("\n1. Injecting Test Admin to MongoDB...")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DB_NAME]
    
    await db["users"].delete_many({"username": "admin_test"})
    import uuid
    admin_id = str(uuid.uuid4())
    await db["users"].insert_one({
        "_id": admin_id,
        "username": "admin_test",
        "password_hash": hash_password("123456"),
        "full_name": "Admin Tester",
        "role": "admin",
        "is_active": True
    })
    print("-> Đã (tái) tạo Admin Test account chuẩn String ID.")

    # Đảm bảo có 1 vé có mã TICKET-TEST
    ticket_id = "TICKET-TEST"
    await db["tickets"].update_one(
        {"_id": ticket_id},
        {"$set": {"status": "active", "customer_id": "test_cus"}},
        upsert=True
    )
    
    # 2. Login vào Render API để lấy Token
    print("\n2. Logging in to Render API...")
    render_url = "https://check-ticket-1hyd.onrender.com"
    token = ""
    async with httpx.AsyncClient(base_url=render_url, timeout=120.0) as httpx_cli:
        try:
            resp = await httpx_cli.post("/api/auth/login", json={"username": "admin_test", "password": "123456"})

            if resp.status_code == 200:
                token = resp.json().get("access_token")
                print("-> Đăng nhập Render Cloud THÀNH CÔNG! Đã lấy JWT Token.")
            else:
                print(f"-> Đăng nhập THẤT BẠI: {resp.status_code} - {resp.text}")
                return
        except Exception as e:
            print(f"Lỗi: {e}")
            return
            
        print("\n3. Testing POST /api/face/enroll on Render Cloud...")
        print("   (Gửi giả lập App Android -> Render -> Ngrok -> Máy bạn -> Ai Service)")
        
        enroll_payload = {
            "ticket_id": ticket_id,
            "face_image_b64": dummy_b64
        }
        
        import time
        start = time.time()
        try:
            resp_enroll = await httpx_cli.post(
                "/api/face/enroll", 
                json=enroll_payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            ) # Phải lớn hơn 25s để thử thách Timeout
            
            elapsed = time.time() - start
            print(f"-> [THỜI GIAN PHẢN HỒI]: {elapsed:.2f} giây")
            print(f"-> [MÃ TRẠNG THÁI]: {resp_enroll.status_code}")
            
            if resp_enroll.status_code == 200:
                print(f"-> [KẾT QUẢ OK]: {resp_enroll.json()}")
                print("🎉 QUY TRÌNH HỆ THỐNG ĐÃ XUYÊN SUỐT 100%! BẠN CÓ THỂ YÊN TÂM!")
            else:
                print(f"-> [LỖI]: {resp_enroll.text[:300]}")
                print("\n⚠️ NẾU BẠN VẪN THẤY LỖI 503:");
                print("1. Hãy chắc chắn Terminal uvicorn trên máy bạn ĐANG CHẠY KHÔNG BỊ TREO (Nhấn Enter vài cái).")
                print("2. Link Ngrok của bạn PHẢI ĐƯỢC CHẤP NHẬN trên biến Environment của Render (AI_SERVICE_URL).")
        except httpx.ReadTimeout:
            print(f"-> [LỖI]: TIMEOUT sau {time.time() - start:.2f}s. Server bị treo! Hãy làm theo bước 'Enter Terminal'")
        except Exception as e:
            print(f"Lỗi Enroll: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_e2e())
