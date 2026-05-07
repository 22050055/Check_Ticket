import asyncio
import os
import base64
import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')

# Sử dụng ảnh thật có khuôn mặt mà Sên đã lưu trữ trong artifact trước đó
# Tớ sẽ đọc tĩnh 1 file demo hoặc dùng 1 ảnh đen để test phản hồi. Đoạn này tớ sẽ tạo ảnh ngẫu nhiên có form mặt hoặc dùng dummy
import cv2
import numpy as np

# Tạo một ảnh dummy dạng nhiễu có thể không ra mặt, ta chủ yếu test Code 200/422 không bị 500
dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
cv2.circle(dummy_img, (320, 320), 100, (255, 255, 255), -1)  # Giả lập đầu
cv2.circle(dummy_img, (280, 290), 20, (0, 0, 0), -1)        # Mắt trái
cv2.circle(dummy_img, (360, 290), 20, (0, 0, 0), -1)        # Mắt phải
cv2.ellipse(dummy_img, (320, 360), (40, 20), 0, 0, 180, (0, 0, 255), -1) # Miệng

_, buffer = cv2.imencode('.jpg', dummy_img)
dummy_b64 = base64.b64encode(buffer).decode('utf-8')

async def check_api():
    base_url = "http://127.0.0.1:8001"
    
    print("--- BẮT ĐẦU TEST TÍCH HỢP AI SERVICE (PORT 8001) ---")
    async with httpx.AsyncClient(base_url=base_url) as client:
        try:
            # 1. Test Health Check
            print("\n1. Test Health Endpoint...")
            resp = await client.get("/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Thành công! Phản hồi: {data}")
                if data.get("model") == "SFace-128d":
                    print("✅ CHÍNH XÁC: Đang chạy phiên bản SFace (128-d).")
                else:
                    print("❌ LỖI: Phiên bản không khớp SFace. Hãy kiểm tra lại.")
            else:
                print(f"❌ Failed Health Check: {resp.status_code}")

            # 2. Test Enroll Endpoint
            print("\n2. Test Enroll Endpoint (Gửi ảnh Dummy)...")
            payload = {"image_b64": dummy_b64}
            resp_enroll = await client.post("/enroll", json=payload)
            if resp_enroll.status_code == 422:
                print(f"✅ AI Service đang bảo mật tốt: Đã chặn nhận ảnh giả. (Cần mặt thật)")
            elif resp_enroll.status_code == 200:
                res_data = resp_enroll.json()
                embeddings = res_data.get("embeddings", [])
                if embeddings and len(embeddings[0]) == 128:
                    print(f"✅ Đăng ký thành công mặt giả lập! Kích thước Vector đạt chuẩn: {len(embeddings[0])}-d.")
                else:
                    print(f"❌ Vector kích thước bị sai lệch! Kích thước là: {len(embeddings[0]) if embeddings else 'None'}")
            else:
                print(f"⚠️ Trạng thái không xác định: {resp_enroll.status_code} - {resp_enroll.text}")

        except httpx.ConnectError:
            print("❌ Không thể kết nối tới Server AI. Vui lòng đảm bảo Port 8001 đang mở.")
        except Exception as e:
            print(f"❌ Lỗi ngoài ý muốn: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_api())
