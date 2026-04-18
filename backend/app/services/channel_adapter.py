"""
services/channel_adapter.py — Xử lý check-in/out đa kênh
"Trái tim" của backend: nhận request thống nhất, route theo channel,
gọi AI Services qua HTTP, lưu gate_event, trả về kết quả.

Channels:
    QR       → verify JWT RS256 trực tiếp (dùng public.pem, không qua HTTP)
    QR_FACE  → verify JWT + gọi AI Services /verify 1:1 qua HTTP
    ID       → HMAC-SHA256 hash CCCD → lookup identities
    BOOKING  → lookup identities theo booking_id
    MANUAL   → lookup tickets theo phone_hash hoặc ticket_id trực tiếp

State machine: OUTSIDE ↔ INSIDE
  IN:  OUTSIDE → INSIDE  (check-in)
  OUT: INSIDE  → OUTSIDE (check-out)
"""
import hashlib
import hmac as _hmac
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.config import settings
from ..models import new_gate_event, new_used_nonce, GateEventResult
from ..schemas.checkin import Channel, Direction

logger = logging.getLogger(__name__)


# ── RSA Public key (lazy load) ────────────────────────────────

_PUBLIC_KEY: Optional[str] = None


def _get_public_key() -> Optional[str]:
    """
    Lazy-load public key lần đầu gọi.
    Tránh lỗi khi file chưa tồn tại lúc import module.
    """
    global _PUBLIC_KEY
    if _PUBLIC_KEY is None:
        path = Path(settings.QR_PUBLIC_KEY_PATH)
        if path.exists():
            _PUBLIC_KEY = path.read_text().strip()
            logger.info("✅ QR public key loaded: %s", path)
        else:
            logger.warning("⚠️  QR public key không tìm thấy: %s", path)
    return _PUBLIC_KEY


# ── Hash helpers (khớp với ai_services/id_service) ────────────

def _hash_id(id_number: str) -> str:
    """HMAC-SHA256 số CCCD/ID — khớp với id_hash_service.py."""
    cleaned = id_number.strip().upper().replace(" ", "").replace("-", "")
    return _hmac.new(
        settings.ID_HASH_PEPPER.encode(),
        cleaned.encode(),
        hashlib.sha256,
    ).hexdigest()


def _hash_phone(phone: str) -> str:
    """HMAC-SHA256 SĐT — khớp với id_hash_service.py."""
    cleaned = re.sub(r"[^0-9]", "", phone)
    if not cleaned:
        raise ValueError("Số điện thoại không hợp lệ.")
    return _hmac.new(
        settings.ID_HASH_PEPPER.encode(),
        cleaned.encode(),
        hashlib.sha256,
    ).hexdigest()


# ── Result dataclass ──────────────────────────────────────────

class CheckinResult:
    """Kết quả xử lý check-in/out — truyền giữa ChannelAdapter và api/checkin.py."""

    __slots__ = ("success", "ticket_id", "ticket_type", "customer_name", "message", "face_score", "_jti")

    def __init__(
        self,
        success:       bool,
        ticket_id:     Optional[str],
        ticket_type:   Optional[str],
        message:       str,
        customer_name: Optional[str] = None,
        face_score:    Optional[float] = None,
        _jti:          Optional[str] = None,   # internal — dùng để đánh dấu nonce sau face
    ):
        self.success       = success
        self.ticket_id     = ticket_id
        self.ticket_type   = ticket_type
        self.customer_name = customer_name
        self.message       = message
        self.face_score    = face_score
        self._jti          = _jti


# ── ChannelAdapter ────────────────────────────────────────────

class ChannelAdapter:
    """
    Route check-in/out theo channel.
    Inject db qua constructor — tạo mới mỗi request (không singleton).
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db   = db
        self._http: Optional[httpx.AsyncClient] = None

    # ── HTTP client (lazy) ────────────────────────────────────

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=settings.AI_SERVICE_URL,
                timeout=settings.AI_SERVICE_TIMEOUT,
            )
        return self._http

    # ── Entry point ───────────────────────────────────────────

    async def process(
        self,
        channel:         Channel,
        direction:       Direction,
        gate_id:         str,
        operator_id:     str,
        qr_token:        Optional[str] = None,
        probe_image_b64: Optional[str] = None,
        id_number:       Optional[str] = None,
        booking_id:      Optional[str] = None,
        phone:           Optional[str] = None,
        ticket_id:       Optional[str] = None,
    ) -> CheckinResult:
        """
        Route theo channel → handler → cập nhật status → lưu gate_event.
        Thứ tự: validate → check ticket → update status → log.
        """
        dir_val = direction.value  # "IN" hoặc "OUT"
        if channel == Channel.QR:
            result = await self._handle_qr(qr_token, dir_val)
        elif channel == Channel.QR_FACE:
            result = await self._handle_qr_face(qr_token, probe_image_b64, dir_val)
        elif channel == Channel.ID:
            result = await self._handle_id(id_number, dir_val)
        elif channel == Channel.BOOKING:
            result = await self._handle_booking(booking_id, dir_val)
        elif channel == Channel.MANUAL:
            result = await self._handle_manual(phone, ticket_id, dir_val)
        else:
            result = CheckinResult(False, None, None, f"Channel không hỗ trợ: {channel}")

        # Cập nhật ticket status theo state machine (cả IN lẫn OUT)
        if result.success and result.ticket_id:
            await self._update_ticket_status(result.ticket_id, direction.value)

        # Lưu gate_event
        await self._save_gate_event(gate_id, direction, channel, result, operator_id)

        return result

    # ── Kênh QR ───────────────────────────────────────────────

    async def _handle_qr(
        self,
        qr_token:   Optional[str],
        direction:  str = "IN",
        mark_nonce: bool = True,   # False khi gọi từ QR_FACE — nonce đánh dấu sau khi face OK
    ) -> CheckinResult:
        """
        Xác thực QR JWT RS256.

        mark_nonce=True  → dùng cho channel QR: đánh dấu nonce ngay khi QR hợp lệ.
        mark_nonce=False → dùng cho channel QR_FACE: KHÔNG đánh dấu nonce tại đây.
                           Nonce chỉ được đánh dấu sau khi face verify THÀNH CÔNG.
                           Nếu face sai → nonce vẫn còn → khách có thể thử lại.
        """
        if not qr_token:
            return CheckinResult(False, None, None, "Thiếu QR token.")

        pub_key = _get_public_key()
        if not pub_key:
            return CheckinResult(False, None, None, "Chưa cấu hình QR public key.")

        # 1. Verify JWT RS256
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(qr_token, pub_key, algorithms=["RS256"])
        except Exception as e:
            logger.warning("QR verify thất bại: %s", e)
            return CheckinResult(False, None, None, f"QR không hợp lệ: {e}")

        jti       = payload.get("jti")
        ticket_id = payload.get("sub")
        tid       = payload.get("tid")

        if not jti:
            return CheckinResult(False, ticket_id, tid, "QR thiếu nonce (jti).")

        # 2. Anti-reuse: kiểm tra nonce (chỉ IN)
        if direction == "IN":
            if await self._db["used_nonces"].find_one({"jti": jti}):
                logger.warning("QR reuse attempt (IN): jti=%s ticket=%s", jti, ticket_id)
                return CheckinResult(False, ticket_id, tid, "QR đã được sử dụng.")

        # 3. Kiểm tra vé + state machine
        ticket = await self._db["tickets"].find_one({"_id": ticket_id})
        if not ticket:
            return CheckinResult(False, ticket_id, tid, "Vé không tồn tại trong hệ thống.")

        status_check = self._validate_ticket_status(ticket, direction)
        if status_check:
            return CheckinResult(False, ticket_id, tid, status_check)

        # 4. Đánh dấu nonce — chỉ khi mark_nonce=True và direction=IN
        if mark_nonce and direction == "IN":
            await self._db["used_nonces"].insert_one(
                new_used_nonce(jti=jti, ticket_id=ticket_id)
            )
            logger.info("Nonce đã đánh dấu: jti=%s", jti)

        action = "Check-in vào" if direction == "IN" else "Check-out ra"
        return CheckinResult(
            success=True,
            ticket_id=ticket_id,
            ticket_type=tid,
            customer_name=ticket.get("customer_name"),
            message=f"QR hợp lệ. {action} thành công.",
            _jti=jti,   # trả về jti để _handle_qr_face dùng sau
        )

    # ── Kênh QR + Face ────────────────────────────────────────

    async def _handle_qr_face(
        self, qr_token: Optional[str], probe_image_b64: Optional[str], direction: str = "IN"
    ) -> CheckinResult:
        """
        Bước 1: Verify QR — KHÔNG đánh dấu nonce (mark_nonce=False).
        Bước 2: Verify face 1:1 qua AI Services.
          - QR sai              → báo sai ngay, nonce KHÔNG bị tiêu thụ
          - QR đúng, face sai   → báo sai, nonce KHÔNG bị tiêu thụ → khách thử lại được
          - QR đúng, face đúng  → đánh dấu nonce → thành công
          - QR đúng, AI down    → fallback QR-only, đánh dấu nonce
          - QR đúng, chưa enroll face → fallback QR-only, đánh dấu nonce
        """
        # Bước 1: verify QR, CHƯA tiêu thụ nonce
        qr_result = await self._handle_qr(qr_token, direction, mark_nonce=False)
        if not qr_result.success:
            return qr_result   # QR sai → dừng, nonce vẫn còn nguyên

        ticket_id = qr_result.ticket_id

        # Bước 2
        if not probe_image_b64:
            return CheckinResult(False, None, None, "Thiếu ảnh khuôn mặt.")

        identity = await self._db["identities"].find_one({"ticket_id": ticket_id})
        if not identity or (not identity.get("face_embeddings") and not identity.get("face_embedding")):
            logger.info("Vé %s chưa đăng ký face → fallback QR-only.", ticket_id)
            await self._mark_nonce(qr_result._jti, ticket_id, direction)
            return CheckinResult(
                success=True,
                ticket_id=ticket_id,
                ticket_type=qr_result.ticket_type,
                customer_name=qr_result.customer_name,
                message="QR hợp lệ (chưa đăng ký face, bỏ qua bước face).",
            )

        try:
            http = await self._get_http()
            # Ưu tiên dùng stored_embeddings (nhiều mẫu) theo góp ý GVHD
            # Fallback về stored_embedding (1 mẫu) nếu dữ liệu cũ
            embs_multi  = identity.get("face_embeddings")   # list[list] — nhiều mẫu
            emb_single  = identity.get("face_embedding")    # list — 1 mẫu (legacy)

            verify_payload: dict = {"probe_image_b64": probe_image_b64}
            if embs_multi:
                verify_payload["stored_embeddings"] = embs_multi
            elif emb_single:
                verify_payload["stored_embedding"] = emb_single
            else:
                logger.info("Vé %s chưa có embedding → fallback QR-only.", ticket_id)
                await self._mark_nonce(qr_result._jti, ticket_id, direction)
                return CheckinResult(
                    success=True, ticket_id=ticket_id,
                    ticket_type=qr_result.ticket_type,
                    customer_name=qr_result.customer_name,
                    message="QR hợp lệ (chưa đăng ký face, bỏ qua bước face).",
                )

            resp = await http.post("/verify", json=verify_payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("AI Services /verify lỗi: %s → fallback QR-only", e)
            # AI down → fallback QR-only, tiêu thụ nonce
            await self._mark_nonce(qr_result._jti, ticket_id, direction)
            return CheckinResult(
                success=True,
                ticket_id=ticket_id,
                ticket_type=qr_result.ticket_type,
                customer_name=qr_result.customer_name,
                message="QR hợp lệ (face service không khả dụng, bỏ qua).",
            )

        is_match   = data.get("is_same_person", False)
        face_score = float(data.get("score", 0.0))

        if is_match:
            # Face đúng → tiêu thụ nonce, thành công
            await self._mark_nonce(qr_result._jti, ticket_id, direction)
            return CheckinResult(
                success=True,
                ticket_id=ticket_id,
                ticket_type=qr_result.ticket_type,
                customer_name=qr_result.customer_name,
                message=f"QR + Face hợp lệ (score={face_score:.3f}).",
                face_score=face_score,
            )

        # Face sai → KHÔNG tiêu thụ nonce → khách có thể thử lại
        logger.warning(
            "Face không khớp, nonce GIỮ NGUYÊN: jti=%s score=%.3f",
            qr_result._jti, face_score,
        )
        return CheckinResult(
            success=False,
            ticket_id=ticket_id,
            ticket_type=qr_result.ticket_type,
            customer_name=qr_result.customer_name,
            message=f"Khuôn mặt không khớp (score={face_score:.3f}). Vui lòng thử lại.",
            face_score=face_score,
        )

    # ── Kênh ID (CCCD) ────────────────────────────────────────

    async def _handle_id(self, id_number: Optional[str], direction: str = "IN") -> CheckinResult:
        if not id_number:
            return CheckinResult(False, None, None, "Thiếu số CCCD/ID.")
        try:
            id_hash = _hash_id(id_number)
        except Exception as e:
            return CheckinResult(False, None, None, f"CCCD/ID không hợp lệ: {e}")

        identity = await self._db["identities"].find_one({"id_hash": id_hash})
        if not identity:
            return CheckinResult(False, None, None, "Không tìm thấy vé với CCCD này.")

        return await self._validate_from_identity(identity, "ID", direction)

    # ── Kênh Booking ID ──────────────────────────────────────

    async def _handle_booking(self, booking_id: Optional[str], direction: str = "IN") -> CheckinResult:
        if not booking_id:
            return CheckinResult(False, None, None, "Thiếu Booking ID.")

        identity = await self._db["identities"].find_one(
            {"booking_id": booking_id.strip().upper()}
        )
        if not identity:
            return CheckinResult(
                False, None, None,
                f"Không tìm thấy vé với booking_id='{booking_id}'.",
            )

        return await self._validate_from_identity(identity, "BOOKING", direction)

    # ── Kênh Manual ──────────────────────────────────────────

    async def _handle_manual(
        self, phone: Optional[str], ticket_id: Optional[str], direction: str = "IN"
    ) -> CheckinResult:
        # Tra cứu trực tiếp theo ticket_id
        if ticket_id:
            ticket = await self._db["tickets"].find_one({"_id": ticket_id.strip()})
            if not ticket:
                return CheckinResult(
                    False, None, None,
                    f"Không tìm thấy ticket_id='{ticket_id}'.",
                )
            return self._build_result_from_ticket(ticket, "MANUAL", direction)

        # Tra cứu theo hash SĐT
        if phone:
            try:
                phone_hash = _hash_phone(phone)
            except ValueError as e:
                return CheckinResult(False, None, None, str(e))

            identity = await self._db["identities"].find_one({"phone_hash": phone_hash})
            if not identity:
                return CheckinResult(False, None, None, "Không tìm thấy vé với SĐT này.")

            return await self._validate_from_identity(identity, "MANUAL", direction)

        return CheckinResult(False, None, None, "Cần cung cấp phone hoặc ticket_id.")

    # ── Helpers ───────────────────────────────────────────────

    async def _validate_from_identity(
        self, identity: dict, label: str, direction: str = "IN"
    ) -> CheckinResult:
        """Lấy ticket từ identity rồi kiểm tra status + direction."""
        ticket_id = identity.get("ticket_id")
        ticket = await self._db["tickets"].find_one({"_id": ticket_id})
        if not ticket:
            return CheckinResult(False, ticket_id, None, "Vé không tồn tại.")
        return self._build_result_from_ticket(ticket, label, direction)

    @staticmethod
    def _validate_ticket_status(ticket: dict, direction: str = "IN") -> Optional[str]:
        """
        State machine OUTSIDE ↔ INSIDE:
          IN:  OUTSIDE → INSIDE   | INSIDE → ❌ đã ở trong
          OUT: INSIDE  → OUTSIDE  | OUTSIDE → ❌ chưa vào
        Trả None nếu OK, trả message lỗi nếu không hợp lệ.
        """
        status = ticket.get("status", "")
        now    = datetime.now(timezone.utc)

        # Kiểm tra thời hạn vé
        valid_until = ticket.get("valid_until")
        if valid_until:
            if valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            if now > valid_until:
                return "Vé đã hết hạn."

        # State machine theo direction
        if direction == "IN":
            if status == "OUTSIDE":
                return None                          # ✅ được vào
            elif status == "INSIDE":
                return "Khách đang ở trong khu — không thể check-in lại."
            elif status == "revoked":
                return "Vé đã bị thu hồi."
            elif status == "expired":
                return "Vé đã hết hạn."
            # Tương thích ngược: vé cũ còn "active"
            elif status == "active":
                return None
            return f"Vé không hợp lệ (status={status})."

        else:  # direction == "OUT"
            if status == "INSIDE":
                return None                          # ✅ được ra
            elif status == "OUTSIDE":
                return "Khách chưa vào khu — không thể check-out."
            elif status == "revoked":
                return "Vé đã bị thu hồi."
            elif status == "expired":
                return "Vé đã hết hạn."
            return f"Vé không hợp lệ (status={status})."

    @staticmethod
    def _build_result_from_ticket(ticket: dict, label: str, direction: str = "IN") -> CheckinResult:
        """Tạo CheckinResult từ ticket document — có direction awareness."""
        tid   = str(ticket["_id"])
        ttype = ticket.get("ticket_type", "unknown")
        cname = ticket.get("customer_name")

        err = ChannelAdapter._validate_ticket_status(ticket, direction)
        if err:
            return CheckinResult(False, tid, ttype, err, customer_name=cname)

        action = "Check-in" if direction == "IN" else "Check-out"
        return CheckinResult(
            success=True,
            ticket_id=tid,
            ticket_type=ttype,
            customer_name=cname,
            message=f"{action} thành công — {label}.",
        )

    async def _mark_nonce(self, jti: Optional[str], ticket_id: Optional[str], direction: str) -> None:
        """Đánh dấu nonce đã dùng — chỉ gọi sau khi toàn bộ flow thành công."""
        if direction == "IN" and jti:
            try:
                await self._db["used_nonces"].insert_one(
                    new_used_nonce(jti=jti, ticket_id=ticket_id)
                )
                logger.info("Nonce đánh dấu: jti=%s ticket=%s", jti, ticket_id)
            except Exception as e:
                logger.error("Không đánh dấu được nonce: %s", e)

    async def _update_ticket_status(self, ticket_id: str, direction: str) -> None:
        """
        State machine: cập nhật status sau khi checkin/out thành công.
          IN  → OUTSIDE → INSIDE
          OUT → INSIDE  → OUTSIDE
        """
        new_status = "INSIDE" if direction == "IN" else "OUTSIDE"
        try:
            await self._db["tickets"].update_one(
                {"_id": ticket_id},
                {"$set": {
                    "status":     new_status,
                    "updated_at": datetime.now(timezone.utc),
                }},
            )
            logger.info("Ticket %s: → %s", ticket_id, new_status)
        except Exception as e:
            logger.error("Không update ticket status: ticket_id=%s err=%s", ticket_id, e)

    async def _save_gate_event(
        self,
        gate_id:     str,
        direction:   Direction,
        channel:     Channel,
        result:      CheckinResult,
        operator_id: str,
    ) -> str:
        """Lưu gate_event vào MongoDB dùng factory từ models."""
        doc = new_gate_event(
            gate_id=gate_id,
            direction=direction.value,
            channel=channel.value,
            result=GateEventResult.SUCCESS if result.success else GateEventResult.FAIL,
            ticket_id=result.ticket_id,
            ticket_type=result.ticket_type,
            fail_reason=None if result.success else result.message,
            operator_id=operator_id,
            face_score=result.face_score,
        )
        try:
            await self._db["gate_events"].insert_one(doc)
        except Exception as e:
            logger.error("Không lưu gate_event: %s", e)
        return doc["_id"]

    async def close(self) -> None:
        """Đóng HTTP client khi không dùng nữa."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
 