import requests, base64
import cv2, numpy as np

print("=== Test 1: Health check ===")
r = requests.get("http://localhost:8001/health")
print("Status:", r.status_code, "→", r.text)

print("\n=== Test 2: Enroll ảnh đen (không có mặt) ===")
img = np.zeros((200, 200, 3), dtype=np.uint8)
_, buf = cv2.imencode('.jpg', img)
b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()
r = requests.post("http://localhost:8001/enroll", json={"image_b64": b64})
print("Status:", r.status_code, "→", r.text[:300])

print("\n=== Test 3: Enroll ảnh có vẽ hình tròn giả mặt ===")
img2 = np.ones((300, 300, 3), dtype=np.uint8) * 200
cv2.circle(img2, (150, 130), 80, (50, 50, 50), -1)   # đầu
cv2.circle(img2, (120, 110), 15, (255, 255, 255), -1) # mắt trái
cv2.circle(img2, (180, 110), 15, (255, 255, 255), -1) # mắt phải
_, buf2 = cv2.imencode('.jpg', img2)
b64_2 = "data:image/jpeg;base64," + base64.b64encode(buf2).decode()
r2 = requests.post("http://localhost:8001/enroll", json={"image_b64": b64_2})
print("Status:", r2.status_code, "→", r2.text[:300])

print("\n=== Test 4: Kiểm tra model đã load chưa ===")
r3 = requests.get("http://localhost:8001/docs")
print("Docs status:", r3.status_code)
