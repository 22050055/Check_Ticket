import cv2
import numpy as np
import os

# Đường dẫn tới model đã download
model_path = r'e:\Learn\Do_an_nganh\Check_ticket\ai_services\face_verification\models\sface.onnx'

if not os.path.exists(model_path):
    print(f"FAILED: Model not found at {model_path}")
    exit(1)

try:
    # Thử load bằng OpenCV FaceRecognizerSF
    recognizer = cv2.FaceRecognizerSF.create(
        model=model_path,
        config="",
        backend_id=cv2.dnn.DNN_BACKEND_DEFAULT,
        target_id=cv2.dnn.DNN_TARGET_CPU
    )
    
    # Giả lập 1 khuôn mặt 112x112
    dummy_face = np.zeros((112, 112, 3), dtype=np.uint8)
    feature = recognizer.feature(dummy_face)
    
    print(f"SUCCESS: SFace loaded.")
    print(f"Output dimension: {feature.shape[1]}")
except Exception as e:
    print(f"FAILED: {str(e)}")
