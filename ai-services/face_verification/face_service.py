"""
face_service.py — FastAPI service nội bộ cho face verification 1:1
Theo góp ý GVHD: đăng ký 3–5 mẫu embedding, verify lấy MAX similarity.
"""
import logging
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .config import SIMILARITY_THRESHOLD
from .detector import FaceDetector, decode_base64_image
from .embedding import FaceEmbedder, embedding_to_list, list_to_embedding
from .similarity import is_same_person, is_same_person_multi, explain_score, explain_multi_score
from .privacy_guard import sanitize_face_payload, assert_no_raw_image

logger = logging.getLogger(__name__)

_detector = FaceDetector()
_embedder = FaceEmbedder()

app = FastAPI(
    title="Face Verification Service",
    description="API nội bộ xác thực khuôn mặt 1:1 cho hệ thống check-in du lịch",
    version="2.0.0",
)


# ── Schemas ──────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    """So sánh ảnh probe với embedding đã lưu (hỗ trợ nhiều mẫu)."""
    stored_embedding:  Optional[list]       = Field(None, description="1 embedding (legacy).")
    stored_embeddings: Optional[list[list]] = Field(None, description="Nhiều embedding mẫu (ưu tiên).")
    stored_image_b64:  Optional[str]        = Field(None, description="Ảnh đã đăng ký (base64). Fallback.")
    probe_image_b64:   str                  = Field(..., description="Ảnh chụp tại cổng (base64).")
    threshold:         Optional[float]      = Field(None, description="Ghi đè ngưỡng mặc định.")


class VerifyResponse(BaseModel):
    is_same_person: bool
    score:          float
    threshold_used: float
    best_sample_idx: Optional[int] = None   # index mẫu embedding cho điểm cao nhất
    n_samples:       int = 1
    message:         str


class EnrollRequest(BaseModel):
    """
    Đăng ký khuôn mặt — nhận 1 hoặc nhiều ảnh.
    Theo góp ý GVHD: nên chụp 3–5 ảnh góc hơi khác nhau.
    """
    image_b64:        Optional[str]       = Field(None, description="1 ảnh base64 (legacy).")
    images_b64:       Optional[list[str]] = Field(None, description="Nhiều ảnh base64 (ưu tiên, 3–5 ảnh).")


class EnrollResponse(BaseModel):
    embeddings:      list[list]   # list of 512-d vectors
    n_embeddings:    int
    face_image_hash: str
    message:         str


# ── Helpers ──────────────────────────────────────────────────

def _extract_embedding(b64_str: str, label: str = "image") -> np.ndarray:
    image_bgr = decode_base64_image(b64_str)
    if image_bgr is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể decode {label}.",
        )
    detection = _detector.detect(image_bgr)
    if detection is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Không phát hiện khuôn mặt trong {label}.",
        )
    return _embedder.get_embedding(detection.face_crop)


# ── Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "face_verification", "version": "2.0.0"}


@app.post("/enroll", response_model=EnrollResponse)
async def enroll_face(req: EnrollRequest):
    """
    Đăng ký khuôn mặt — trích xuất embedding từ 1 hoặc nhiều ảnh.
    Trả về LIST embeddings để lưu vào DB (không lưu ảnh gốc).

    Theo góp ý GVHD: nên gửi 3–5 ảnh ở các góc hơi khác nhau.
    Backend lưu tất cả embeddings → verify sẽ lấy max similarity.
    """
    import base64, hashlib

    # Thu thập danh sách ảnh
    images_b64: list[str] = []
    if req.images_b64:
        images_b64 = req.images_b64[:5]          # Tối đa 5 ảnh
    elif req.image_b64:
        images_b64 = [req.image_b64]             # Legacy: 1 ảnh
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp image_b64 hoặc images_b64.",
        )

    if len(images_b64) == 0:
        raise HTTPException(status_code=400, detail="Danh sách ảnh trống.")

    # Trích xuất embedding cho từng ảnh
    embeddings: list[list] = []
    first_hash = ""

    for i, b64 in enumerate(images_b64):
        # Hash ảnh đầu tiên để audit
        raw = b64.split(",", 1)[1] if "," in b64 else b64
        img_bytes = base64.b64decode(raw)
        if i == 0:
            first_hash = hashlib.sha256(img_bytes).hexdigest()

        emb = _extract_embedding(b64, label=f"ảnh {i+1}")
        payload = sanitize_face_payload(img_bytes, emb)
        assert_no_raw_image(payload)
        embeddings.append(payload["face_embedding"])

    logger.info("Enroll: trích xuất %d embedding thành công.", len(embeddings))

    return EnrollResponse(
        embeddings=embeddings,
        n_embeddings=len(embeddings),
        face_image_hash=first_hash,
        message=f"Đăng ký thành công {len(embeddings)} mẫu khuôn mặt. Ảnh gốc không được lưu.",
    )


@app.post("/verify", response_model=VerifyResponse)
async def verify_face(req: VerifyRequest):
    """
    Xác thực 1:1 — so sánh ảnh tại cổng với embedding đã lưu.
    Nếu có nhiều embedding mẫu → lấy MAX similarity (theo góp ý GVHD).
    """
    threshold = req.threshold if req.threshold is not None else SIMILARITY_THRESHOLD

    probe_emb = _extract_embedding(req.probe_image_b64, "probe image")

    # ── Nhiều embedding mẫu (ưu tiên) ──────────────────────
    if req.stored_embeddings:
        stored_embs = [list_to_embedding(e) for e in req.stored_embeddings]
        matched, best_score, best_idx = is_same_person_multi(stored_embs, probe_emb, threshold)
        log_msg = explain_multi_score(best_score, best_idx, len(stored_embs), threshold)
        logger.info("Face verify (multi): %s", log_msg)
        return VerifyResponse(
            is_same_person=matched,
            score=round(best_score, 6),
            threshold_used=threshold,
            best_sample_idx=best_idx,
            n_samples=len(stored_embs),
            message="Xác thực thành công." if matched else "Khuôn mặt không khớp.",
        )

    # ── 1 embedding (legacy / fallback) ────────────────────
    if req.stored_embedding is not None:
        stored_emb = list_to_embedding(req.stored_embedding)
        matched, score = is_same_person(stored_emb, probe_emb, threshold)
        logger.info("Face verify (single): %s", explain_score(score, threshold))
        return VerifyResponse(
            is_same_person=matched,
            score=round(score, 6),
            threshold_used=threshold,
            n_samples=1,
            message="Xác thực thành công." if matched else "Khuôn mặt không khớp.",
        )

    # ── Fallback: ảnh gốc → extract embedding ──────────────
    if req.stored_image_b64:
        stored_emb = _extract_embedding(req.stored_image_b64, "stored image")
        matched, score = is_same_person(stored_emb, probe_emb, threshold)
        return VerifyResponse(
            is_same_person=matched,
            score=round(score, 6),
            threshold_used=threshold,
            n_samples=1,
            message="Xác thực thành công." if matched else "Khuôn mặt không khớp.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cần cung cấp stored_embeddings, stored_embedding, hoặc stored_image_b64.",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("face_service:app", host="0.0.0.0", port=8001, reload=True)
 