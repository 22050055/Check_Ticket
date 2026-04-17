"""
embedding.py — Trích xuất vector embedding 512-d dùng ArcFace w600k_r50.onnx (buffalo_l)
Input: ảnh 112×112 RGB → Output: vector 512-d đã L2-normalize
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from .config import ARCFACE_MODEL_PATH, ARCFACE_INPUT_SIZE, EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class FaceEmbedder:
    """
    Wrapper cho ArcFace w600k_r50.onnx.
    Dùng ONNX Runtime để inference, không cần cài insightface.
    """

    def __init__(self):
        self._session   = None
        self._input_name: Optional[str] = None
        self._load_model()

    def _load_model(self):
        if not Path(ARCFACE_MODEL_PATH).exists():
            logger.warning(
                "⚠️  ArcFace model không tìm thấy: %s. "
                "Dùng random embedding (chỉ cho dev).",
                ARCFACE_MODEL_PATH,
            )
            return
        try:
            import onnxruntime as ort
            self._session = ort.InferenceSession(
                ARCFACE_MODEL_PATH,
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._input_name = self._session.get_inputs()[0].name
            # Log input shape để xác nhận model đúng
            input_shape = self._session.get_inputs()[0].shape
            logger.info(
                "✅ ArcFace w600k_r50.onnx loaded. Input shape: %s", input_shape
            )
        except Exception as e:
            logger.error("❌ Load ArcFace thất bại: %s", e)
            self._session = None

    def get_embedding(self, face_rgb_112: np.ndarray) -> np.ndarray:
        """
        Nhận ảnh 112×112 RGB → vector embedding 512-d (L2-normalized).

        Args:
            face_rgb_112: numpy array shape (112, 112, 3) uint8 hoặc float32.

        Returns:
            numpy array shape (512,) float32, đã L2-normalize.
        """
        if self._session is None:
            logger.warning("Dùng random embedding (model chưa load).")
            vec = np.random.randn(EMBEDDING_DIMENSION).astype(np.float32)
            return _l2_normalize(vec)

        # Tiền xử lý ArcFace: chuẩn hóa về [-1, 1]
        img = face_rgb_112.astype(np.float32)
        img = (img - 127.5) / 127.5               # scale [-1, 1]
        img = img.transpose(2, 0, 1)              # HWC → CHW (3, 112, 112)
        img = np.expand_dims(img, axis=0)         # (1, 3, 112, 112)

        output = self._session.run(None, {self._input_name: img})
        embedding = output[0][0]                  # (512,)
        return _l2_normalize(embedding)


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
 