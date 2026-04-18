"""
id_hash_service.py — Hash CCCD/ID số theo SHA-256
Nguyên tắc tối thiểu dữ liệu: không lưu số gốc, chỉ lưu hash
"""
import hashlib
import hmac
import logging
import os
import re

logger = logging.getLogger(__name__)

# Pepper từ env (không hardcode trong code, không lưu trong DB)
_PEPPER = os.getenv("ID_HASH_PEPPER", "tourism_id_pepper_v1_CHANGE_IN_PROD")


def hash_id_number(id_number: str) -> str:
    """
    Hash số CCCD / CMND / Hộ chiếu bằng HMAC-SHA256 với pepper.

    Args:
        id_number: Chuỗi số (9-12 ký tự, chỉ chứa số và chữ hoa).

    Returns:
        Hex string 64 ký tự (256 bit).

    Raises:
        ValueError: Nếu định dạng không hợp lệ.
    """
    cleaned = _clean_id(id_number)
    digest = hmac.new(
        _PEPPER.encode(),
        cleaned.encode(),
        hashlib.sha256,
    ).hexdigest()
    logger.debug("ID hash tạo thành công (không log số gốc).")
    return digest


def verify_id_hash(id_number: str, stored_hash: str) -> bool:
    """
    Kiểm tra số ID có khớp với hash đã lưu.
    Dùng hmac.compare_digest để tránh timing attack.
    """
    computed = hash_id_number(id_number)
    return hmac.compare_digest(computed, stored_hash)


def _clean_id(id_number: str) -> str:
    """Chuẩn hóa ID: bỏ dấu cách, chuyển upper, kiểm tra độ dài."""
    cleaned = id_number.strip().upper().replace(" ", "").replace("-", "")
    # CCCD VN: 12 số | CMND cũ: 9 số | Hộ chiếu: 8-9 ký tự alphanumeric
    if not re.match(r'^[A-Z0-9]{8,20}$', cleaned):
        raise ValueError(
            f"Định dạng ID không hợp lệ (dài {len(cleaned)} ký tự). "
            "Chấp nhận: 8-20 ký tự chữ và số."
        )
    return cleaned


def hash_phone(phone: str) -> str:
    """
    Hash số điện thoại (dùng cho tra cứu thủ công an toàn hơn).
    """
    cleaned = re.sub(r'[^0-9]', '', phone)
    if len(cleaned) < 9:
        raise ValueError("Số điện thoại không hợp lệ.")
    return hmac.new(
        _PEPPER.encode(),
        cleaned.encode(),
        hashlib.sha256,
    ).hexdigest()
 