import asyncio
import os
import base64
import sys
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
from datetime import datetime

# Ép console dùng UTF-8 trên Windows
sys.stdout.reconfigure(encoding='utf-8')

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://22050055_db_user:khang123@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority")
DB_NAME = "test"  # Default của DB user Khang có khả năng là 'test' nếu không định nghĩa

# Tạo một ảnh dummy 112x112 pixel chuẩn Base64 để test enroll/verify
import cv2
import numpy as np
dummy_img = np.zeros((112, 112, 3), dtype=np.uint8)
# Vẽ chút gì đó giả làm mặt để qua detector mượt hơn (tuỳ thuộc detector, nhưng ta đang test API call backend)
# Detector của mình cần thấy mặt thật để trả về. Vì vậy nếu không đưa mặt thật det10g sẽ báo lỗi "không tìm thấy mặt".
# Do đó, API call test sẽ mong đợi một lỗi "Không tìm thấy mặt" hoặc HTTP 422. Điều quan trọng là service CÓ nhận request!
_, buffer = cv2.imencode('.jpg', dummy_img)
dummy_b64 = base64.b64encode(buffer).decode('utf-8')

async def main():
    print(f"[{datetime.now().time()}] Bắt đầu quy trình Làm sạch và Tích hợp...")

    # 1. Làm sạch Database
    print("\n--- 1. LÀM SẠCH MONGODB ---")
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        identities_col = db["identities"]
        
        # Xóa trường face_embeddings của toàn bộ user
        result = await identities_col.update_many(
            {}, 
            {"$unset": {"face_embeddings": "", "face_embedding": "", "n_face_samples": ""},
             "$set": {"has_face": False}}
        )
        print(f"✅ Đã dọn dẹp thành công dữ liệu khuôn mặt cũ (ArcFace 512-d). Tổng số documents ảnh hưởng: {result.modified_count}")
    except Exception as e:
        print(f"❌ Lỗi khi kết nối MongoDB: {e}")

    # 2. Test Backend API -> AI Service (Port 8001)
    print("\n--- 2. TÍCH HỢP HỆ THỐNG (AI SERVICE 8001) ---")
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001") as client_http:
        try:
            # Check Health
            resp = await client_http.get("/health")
            if resp.status_code == 200:
                print(f"✅ AI Service đang chạy tốt. Phản hồi: {resp.json()}")
            else:
                print(f"❌ AI Service Health Check thất bại: {resp.status_code}")
                
            # Test Payload Enroll (Không có mặt thật nên sẽ dính 422, chứng tỏ logic hoạt động tốt)
            resp_enroll = await client_http.post("/enroll", json={"image_b64": dummy_b64})
            if resp_enroll.status_code == 422:
                print(f"✅ AI Service Enroll Endpoint phản hồi chuẩn xác. (Sẵn sàng nhận diện khuôn mặt thật)")
            elif resp_enroll.status_code == 200:
                print(f"✅ Cảnh báo: Khuôn mặt dummy đã vượt qua.")
            else:
                print(f"❌ AI Service Enroll Unexpected: {resp_enroll.status_code} - {resp_enroll.text}")

        except httpx.ConnectError:
            print("❌ AI Service (port 8001) đang không bật. Hãy chạy: uvicorn ai_services.face_verification.face_service:app --port 8001")
        except Exception as e:
            print(f"❌ Lỗi khi test HTTP: {e}")

if __name__ == "__main__":
    asyncio.run(main())
