"""
schemas/checkin.py — Request/Response cho check-in/out đa kênh

Channel routing:
    QR       → qr_token bắt buộc
    QR_FACE  → qr_token + probe_image_b64 bắt buộc
    ID       → id_number bắt buộc
    BOOKING  → booking_id bắt buộc
    MANUAL   → phone hoặc ticket_id bắt buộc (ít nhất 1)
"""
from pydantic import BaseModel, Field, model_validator
from typing import Optional, Self
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────

class Channel(str, Enum):
    QR      = "QR"       # QR-only (JWT RS256)
    QR_FACE = "QR_FACE"  # QR + Face verification 1:1 (opt-in)
    ID      = "ID"       # CCCD/ID hash lookup
    BOOKING = "BOOKING"  # Booking ID lookup
    MANUAL  = "MANUAL"   # Tra cứu thủ công (SĐT / ticket_id)


class Direction(str, Enum):
    IN  = "IN"
    OUT = "OUT"


# ── Request ───────────────────────────────────────────────────

class CheckinRequest(BaseModel):
    """
    Endpoint thống nhất cho tất cả kênh check-in/out.
    Gate App gửi request này, backend route qua ChannelAdapter.

    Validation: field bắt buộc theo channel được kiểm tra qua model_validator.
    """
    gate_id:   str       = Field(..., description="ID cổng check-in/out")
    direction: Direction = Field(..., description="IN hoặc OUT")
    channel:   Channel   = Field(..., description="Kênh xác thực")

    # ── Kênh QR ──────────────────────────────────────────────
    qr_token: Optional[str] = Field(
        None, description="JWT RS256 token từ mã QR — bắt buộc với QR, QR_FACE"
    )

    # ── Kênh QR + Face ────────────────────────────────────────
    probe_image_b64: Optional[str] = Field(
        None, description="Ảnh chụp khuôn mặt tại cổng (base64) — bắt buộc với QR_FACE"
    )

    # ── Kênh CCCD/ID ─────────────────────────────────────────
    id_number: Optional[str] = Field(
        None, description="Số CCCD/ID thô — backend sẽ hash trước khi tra cứu"
    )

    # ── Kênh Booking ─────────────────────────────────────────
    booking_id: Optional[str] = Field(
        None, description="Mã booking — bắt buộc với BOOKING"
    )

    # ── Kênh Manual ──────────────────────────────────────────
    phone:     Optional[str] = Field(None, description="SĐT tra cứu thủ công")
    ticket_id: Optional[str] = Field(None, description="Ticket ID tra cứu trực tiếp")

    @model_validator(mode="after")
    def validate_channel_fields(self) -> Self:
        """Kiểm tra field bắt buộc theo từng channel."""
        ch = self.channel
        if ch == Channel.QR and not self.qr_token:
            raise ValueError("Kênh QR: qr_token là bắt buộc.")
        if ch == Channel.QR_FACE:
            if not self.qr_token:
                raise ValueError("Kênh QR_FACE: qr_token là bắt buộc.")
            if not self.probe_image_b64:
                raise ValueError("Kênh QR_FACE: probe_image_b64 là bắt buộc.")
        if ch == Channel.ID and not self.id_number:
            raise ValueError("Kênh ID: id_number (số CCCD) là bắt buộc.")
        if ch == Channel.BOOKING and not self.booking_id:
            raise ValueError("Kênh BOOKING: booking_id là bắt buộc.")
        if ch == Channel.MANUAL and not self.phone and not self.ticket_id:
            raise ValueError("Kênh MANUAL: cần cung cấp phone hoặc ticket_id.")
        return self


# ── Response ──────────────────────────────────────────────────

class CheckinResponse(BaseModel):
    """Kết quả check-in/out trả về cho Gate App."""
    success:      bool
    direction:    str
    channel:      str
    ticket_id:    Optional[str]   = None
    ticket_type:  Optional[str]   = None
    customer_name: Optional[str]  = None
    face_score:   Optional[float] = None   # Cosine similarity — chỉ có khi QR_FACE
    message:      str
    event_id:     Optional[str]   = None   # GateEvent._id để audit
