"""
embedding.py — Trích xuất vector embedding 128-d dùng SFace.onnx (OpenCV Zoo)
Model tối ưu cho khuôn mặt Châu Á.
"""
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .config import SFACE_MODEL_PATH, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class FaceEmbedder:
    """
    Wrapper cho OpenCV SFace (face_recognition_sface_2021dec.onnx).
    Dùng cv2.FaceRecognizerSF tích hợp sẵn trong OpenCV.
    """

    def __init__(self):
        self._model = None
        self._load_model()

    def _load_model(self):
        if not Path(SFACE_MODEL_PATH).exists():
            logger.warning(
                "⚠️  SFace model không tìm thấy tại: %s. "
                "Dùng random embedding (chỉ dành cho môi trường dev).",
                SFACE_MODEL_PATH,
            )
            return
        try:
            # SFace trong OpenCV không yêu cầu config file, chỉ cần .onnx
            self._model = cv2.FaceRecognizerSF.create(
                model=SFACE_MODEL_PATH,
                config="",
                backend_id=cv2.dnn.DNN_BACKEND_DEFAULT,
                target_id=cv2.dnn.DNN_TARGET_CPU,
            )
            logger.info("✅ SFace model loaded (OpenCV FaceRecognizerSF). Dim: 128")
        except Exception as e:
            logger.error("❌ Load SFace thất bại: %s", e)
            self._model = None

    def get_embedding(self, face_rgb_112: np.ndarray) -> np.ndarray:
        """
        Nhận ảnh 112×112 RGB → vector embedding 128-d (L2-normalized).
        """
        if self._model is None:
            logger.warning("Dùng random embedding (model SFace chưa load).")
            vec = np.random.randn(EMBEDDING_DIMENSION).astype(np.float32)
            return _l2_normalize(vec)

        # Note: FaceRecognizerSF.feature() xử lý tốt nhất khi nhận ảnh aligned BGR
        face_bgr = cv2.cvtColor(face_rgb_112, cv2.COLOR_RGB2BGR)
        
        # SF.feature() trả về (1, 128) float32
        embedding = self._model.feature(face_bgr)
        
        # OpenCV SFace đã L2-normalize nhưng ta làm lại cho chắc chắn
        return _l2_normalize(embedding[0])


# ── GenderAge (buffalo_l bonus) ───────────────────────────────

class GenderAgeEstimator:
    """
    Ước lượng giới tính và tuổi dùng genderage.onnx (buffalo_l).
    Tận dụng cho Dashboard phân tích cơ cấu nhóm tuổi (mục 3.6).
    """

    # Nhóm tuổi cho Dashboard
    AGE_GROUPS = {
        "0-12":  (0,  12),
        "13-17": (13, 17),
        "18-35": (18, 35),
        "36-55": (36, 55),
        "56+":   (56, 150),
    }

    def __init__(self):
        self._session   = None
        self._input_name: Optional[str] = None
        self._load_model()

    def _load_model(self):
        from .config import GENDERAGE_MODEL_PATH
        if not Path(GENDERAGE_MODEL_PATH).exists():
            logger.info("genderage.onnx không tìm thấy — tính năng nhóm tuổi bị tắt.")
            return
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(
                GENDERAGE_MODEL_PATH,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._input_name = self._session.get_inputs()[0].name
            logger.info("✅ genderage.onnx loaded.")
        except Exception as e:
            logger.error("Load genderage thất bại: %s", e)

    def predict(self, face_rgb_112: np.ndarray) -> Optional[dict]:
        """
        Dự đoán giới tính và tuổi.

        Returns:
            {"gender": "male"/"female", "age": 25, "age_group": "18-35"} hoặc None.
        """
        if self._session is None:
            return None

        img = face_rgb_112.astype(np.float32)
        img = (img - 127.5) / 127.5
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0)

        output = self._session.run(None, {self._input_name: img})[0][0]
        # output: [gender_score, age] theo InsightFace convention
        gender = "female" if output[0] > 0.5 else "male"
        age    = int(output[1] * 100)   # normalize về [0, 100]

        return {
            "gender":    gender,
            "age":       age,
            "age_group": self._to_group(age),
        }

    def _to_group(self, age: int) -> str:
        for label, (lo, hi) in self.AGE_GROUPS.items():
            if lo <= age <= hi:
                return label
        return "56+"


# ── Utils ─────────────────────────────────────────────────────

def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return (vec / norm).astype(np.float32) if norm > 1e-10 else vec


def embedding_to_list(embedding: np.ndarray) -> list:
    """Chuyển numpy array → Python list để lưu MongoDB."""
    return embedding.tolist()


def list_to_embedding(lst: list) -> np.ndarray:
    """Chuyển Python list từ MongoDB → numpy array."""
    return np.array(lst, dtype=np.float32)
 