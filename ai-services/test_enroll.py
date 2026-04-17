import requests, base64
import cv2, numpy as np

# Ảnh giả 100x100
img = np.zeros((100, 100, 3), dtype=np.uint8)
_, buf = cv2.imencode('.jpg', img)
b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

r = requests.post("http://localhost:8001/enroll", json={"image_b64": b64})
print("Status:", r.status_code)
print("Response text:", r.text)
 