"""
Cấu hình Face Verification Service
Sử dụng InsightFace buffalo_l model pack
"""
import os
from pathlib import Path

# Load file .env nếu có
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

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

# SFace — model trích xuất đặc trưng (128-d) tối ưu cho Châu Á
SFACE_MODEL_PATH: str = os.getenv(
    "SFACE_MODEL_PATH",
    str(MODELS_DIR / "sface.onnx"),
)

# ── Ngưỡng xác thực (cosine similarity) ──────────────────────
# SFace khuyên dùng ngưỡng ~0.36-0.37 cho Cosine Similarity.
SIMILARITY_THRESHOLD: float = float(os.getenv("FACE_THRESHOLD", "0.37"))

# ── Kích thước ảnh đầu vào ────────────────────────────────────
ARCFACE_INPUT_SIZE: tuple  = (112, 112)   # SFace & ArcFace dùng chung 112x112
DETECTOR_INPUT_SIZE: tuple = (640, 640)   # det_10g RetinaFace

# ── Detector settings ─────────────────────────────────────────
DET_SCORE_THRESHOLD: float = 0.5
DET_NMS_THRESHOLD: float   = 0.4

# ── Privacy ───────────────────────────────────────────────────
STORE_ORIGINAL_IMAGE: bool = False
EMBEDDING_DIMENSION: int   = 128          # SFace trả về 128-d vector
 