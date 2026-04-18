"""
Cấu hình Face Verification Service
Sử dụng InsightFace buffalo_l model pack
"""
import os
from pathlib import Path

BASE_DIR   = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"
BUFFALO_DIR = MODELS_DIR / "buffalo_l"

# ── Model paths (buffalo_l) ───────────────────────────────────
# ArcFace R50 — trích xuất embedding 512-d
ARCFACE_MODEL_PATH: str = os.getenv(
    "ARCFACE_MODEL_PATH",
    str(BUFFALO_DIR / "w600k_r50.onnx"),
)
# RetinaFace det_10g — face detection
DETECTOR_MODEL_PATH: str = os.getenv(
    "DETECTOR_MODEL_PATH",
    str(BUFFALO_DIR / "det_10g.onnx"),
)
# GenderAge — tuổi & giới tính (tận dụng cho Dashboard nhóm tuổi)
GENDERAGE_MODEL_PATH: str = os.getenv(
    "GENDERAGE_MODEL_PATH",
    str(BUFFALO_DIR / "genderage.onnx"),
)
# YuNet — fallback detector nếu det_10g chưa có
YUNET_MODEL_PATH: str = os.getenv(
    "YUNET_MODEL_PATH",
    str(MODELS_DIR / "yunet_face_detect.onnx"),
)

# ── Ngưỡng xác thực (cosine similarity) ──────────────────────
# ArcFace buffalo_l đã L2-norm sẵn → similarity cao hơn FaceNet
# Khuyến nghị: 0.3–0.4 (khác FaceNet là 0.6)
SIMILARITY_THRESHOLD: float = float(os.getenv("FACE_THRESHOLD", "0.28"))

# ── Kích thước ảnh đầu vào ────────────────────────────────────
ARCFACE_INPUT_SIZE: tuple  = (112, 112)   # ArcFace chuẩn: 112x112
DETECTOR_INPUT_SIZE: tuple = (640, 640)   # det_10g RetinaFace

# ── Detector settings ─────────────────────────────────────────
DET_SCORE_THRESHOLD: float = 0.5
DET_NMS_THRESHOLD: float   = 0.4

# ── Privacy ───────────────────────────────────────────────────
STORE_ORIGINAL_IMAGE: bool = False
EMBEDDING_DIMENSION: int   = 512
 