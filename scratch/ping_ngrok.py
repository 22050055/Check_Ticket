import asyncio
import base64
import sys
import time
import httpx
import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# Tạo dummy face image giống với Android (640x640)
dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
cv2.circle(dummy_img, (320, 320), 100, (255, 255, 255), -1)
cv2.circle(dummy_img, (280, 290), 20, (0, 0, 0), -1)
cv2.circle(dummy_img, (360, 290), 20, (0, 0, 0), -1)
cv2.ellipse(dummy_img, (320, 360), (40, 20), 0, 0, 180, (0, 0, 255), -1)
_, buffer = cv2.imencode('.jpg', dummy_img)
dummy_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

async def check():
    ngrok_url = "https://erasure-happiest-android.ngrok-free.dev"
    print(f"--- ĐẤU NỐI THỬ VỚI NGROK CỦA USER: {ngrok_url} ---")
    
    async with httpx.AsyncClient(base_url=ngrok_url, headers={"ngrok-skip-browser-warning": "69420"}) as client:
        # 1. Health
        start = time.time()
        try:
            r = await client.get("/health", timeout=30.0)
            print(f"Health Check: {r.status_code} ({time.time() - start:.2f}s)")
            if r.status_code == 200:
                print(f"Body: {r.json()}")
        except Exception as e:
            print(f"Health exception: {e}")

        # 2. Enroll
        print("\nSending POST /enroll to Ngrok (AI Service Local)...")
        start = time.time()
        try:
            r = await client.post("/enroll", json={"image_b64": dummy_b64}, timeout=30.0)
            elapsed = time.time() - start
            print(f"Enroll response in {elapsed:.2f}s - Status: {r.status_code}")
            try:
                print(r.json())
            except:
                print(r.text[:500])
        except Exception as e:
            print(f"Enroll exception: {e}")

if __name__ == "__main__":
    asyncio.run(check())
