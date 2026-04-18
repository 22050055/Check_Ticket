"""
qr_service.py — Tạo QR e-ticket ký số RS256 và xác thực chữ ký
Chống giả mạo + chống dùng lại (kết hợp nonce_store & time_window)
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import qrcode
from io import BytesIO
import base64

from .nonce_store import NonceStore
from .time_window import is_within_time_window, TimeWindowError

logger = logging.getLogger(__name__)

# ── Đọc keys từ file ─────────────────────────────────────────
BASE_DIR = Path(__file__).parent

def _read_key(path: Path) -> Optional[str]:
    if path.exists():
        return path.read_text().strip()
    logger.warning("⚠️  Key không tìm thấy: %s", path)
    return None

PRIVATE_KEY = _read_key(BASE_DIR / "keys" / "private.pem")
PUBLIC_KEY  = _read_key(BASE_DIR / "keys" / "public.pem")


# ── QR Payload Schema ────────────────────────────────────────
# Payload được ký số → encode thành JWT → in thành QR
# {
#   "jti": "<uuid nonce>",       # JWT ID - dùng chống reuse
#   "sub": "<ticket_id>",        # Subject = ticket ID trong DB
#   "tid": "<ticket_type>",      # Loại vé: adult/child/group
#   "iat": <unix timestamp>,     # Issued at
#   "exp": <unix timestamp>,     # Expiry (thường = ngày hiệu lực vé)
#   "vid": "<venue_id>",         # Khu du lịch
# }


class QRService:
    """Tạo và xác thực QR e-ticket có chữ ký RS256."""

    def __init__(self):
        self._nonce_store = NonceStore()

    # ── Tạo QR ───────────────────────────────────────────────

    def create_ticket_jwt(
        self,
        ticket_id: str,
        ticket_type: str,
        valid_until: datetime,
        venue_id: str = "tourism_default",
    ) -> str:
        """
        Tạo JWT ký RS256 cho 1 vé.

        Returns:
            JWT string (3 phần: header.payload.signature)
        """
        if PRIVATE_KEY is None:
            raise RuntimeError("Private key chưa được cấu hình. Chạy keygen trước.")

        from jose import jwt as jose_jwt

        now = datetime.now(timezone.utc)
        payload = {
            "jti": str(uuid.uuid4()),           # Nonce duy nhất
            "sub": ticket_id,
            "tid": ticket_type,
            "vid": venue_id,
            "iat": int(now.timestamp()),
            "exp": int(valid_until.timestamp()),
        }

        token = jose_jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
        logger.info("QR tạo cho ticket=%s jti=%s", ticket_id, payload["jti"])
        return token

    def create_qr_image_b64(self, jwt_token: str) -> str:
        """
        Chuyển JWT string thành ảnh QR PNG → base64.
        Dùng để trả về cho client hoặc gửi email.
        """
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(jwt_token)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"

    # ── Xác thực QR ──────────────────────────────────────────

    def verify_ticket_jwt(self, token: str) -> dict:
        """
        Xác thực JWT: chữ ký → time window → chống reuse.

        Returns:
            dict payload nếu hợp lệ.

        Raises:
            QRInvalidError: nếu chữ ký sai, hết hạn, hoặc đã dùng.
        """
        if PUBLIC_KEY is None:
            raise RuntimeError("Public key chưa được cấu hình.")

        from jose import jwt as jose_jwt, JWTError

        # 1. Xác thực chữ ký + expiry
        try:
            payload = jose_jwt.decode(
                token,
                PUBLIC_KEY,
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
        except JWTError as exc:
            logger.warning("QR signature invalid: %s", exc)
            raise QRInvalidError(f"Chữ ký QR không hợp lệ: {exc}") from exc

        # 2. Kiểm tra time window (optional — thêm lớp bảo vệ)
        try:
            is_within_time_window(payload)
        except TimeWindowError as exc:
            raise QRInvalidError(str(exc)) from exc

        # 3. Kiểm tra nonce chống dùng lại
        jti = payload.get("jti")
        if not jti:
            raise QRInvalidError("QR thiếu nonce (jti).")

        if self._nonce_store.is_used(jti):
            logger.warning("QR reuse attempt: jti=%s ticket=%s", jti, payload.get("sub"))
            raise QRInvalidError("QR đã được sử dụng. Không thể dùng lại.")

        # 4. Đánh dấu đã dùng
        self._nonce_store.mark_used(jti, ticket_id=payload.get("sub"))

        logger.info(
            "QR hợp lệ: ticket=%s jti=%s type=%s",
            payload.get("sub"), jti, payload.get("tid")
        )
        return payload


class QRInvalidError(Exception):
    """QR không hợp lệ: chữ ký sai / hết hạn / đã dùng."""
    pass


# ── Singleton ────────────────────────────────────────────────
_qr_service: Optional[QRService] = None

def get_qr_service() -> QRService:
    global _qr_service
    if _qr_service is None:
        _qr_service = QRService()
    return _qr_service
 