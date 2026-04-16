"""
privacy_guard.py — Đảm bảo nguyên tắc tối thiểu dữ liệu (data minimization)
Theo ghi chú pháp lý đề cương: chỉ lưu embedding, không lưu ảnh gốc
"""
import hashlib
import logging
from typing import Optional
import numpy as np

from .config import STORE_ORIGINAL_IMAGE

logger = logging.getLogger(__name__)


def sanitize_face_payload(
    image_bytes: Optional[bytes],
    embedding: np.ndarray,
) -> dict:
    """
    Chuẩn bị payload lưu vào DB.
    - KHÔNG lưu ảnh gốc (trừ khi STORE_ORIGINAL_IMAGE = True trong dev).
    - Lưu embedding + hash của ảnh để audit.

    Returns:
        dict sẵn để lưu vào collection identities.
    """
    payload = {
        "face_embedding": embedding.tolist(),
        "embedding_dim": len(embedding),
    }

    if image_bytes is not None:
        # Chỉ lưu hash SHA-256 của ảnh để audit trail, không lưu ảnh gốc
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        payload["face_image_hash"] = image_hash

        if STORE_ORIGINAL_IMAGE:
            # Chỉ bật trong môi trường dev khi cần debug
            import base64
            payload["face_image_b64"] = base64.b64encode(image_bytes).decode()
            logger.warning(
                "⚠️  STORE_ORIGINAL_IMAGE=True — không dùng trong production!"
            )
        else:
            logger.debug("Privacy guard: ảnh gốc không lưu, chỉ lưu hash + embedding.")

    return payload


def sanitize_cccd_payload(cccd_number: str) -> dict:
    """
    Hash CCCD number trước khi lưu DB.
    Không bao giờ lưu số CCCD gốc.

    Returns:
        dict với id_hash (SHA-256 của số CCCD).
    """
    if not cccd_number or len(cccd_number) < 9:
        raise ValueError("Số CCCD/ID không hợp lệ.")

    # SHA-256 với salt cố định (trong thực tế dùng pepper từ env)
    salt = "tourism_system_v1"
    id_hash = hashlib.sha256(f"{salt}:{cccd_number}".encode()).hexdigest()

    return {
        "id_hash": id_hash,
        # Không có trường id_number trong payload
    }


def assert_no_raw_image(payload: dict) -> None:
    """
    Kiểm tra payload không chứa ảnh gốc trước khi lưu DB.
    Gọi trước mọi insert/update collection identities.
    """
    forbidden_keys = {"face_image_b64", "face_image_base64", "image", "photo"}
    found = forbidden_keys.intersection(payload.keys())
    if found and not STORE_ORIGINAL_IMAGE:
        raise PrivacyViolationError(
            f"Payload chứa dữ liệu ảnh gốc: {found}. "
            "Không được lưu ảnh khuôn mặt vào DB theo chính sách bảo mật."
        )


class PrivacyViolationError(Exception):
    """Raise khi cố lưu dữ liệu vi phạm chính sách tối thiểu."""
    pass
