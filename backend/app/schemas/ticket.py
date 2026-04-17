"""
schemas/ticket.py — Request/Response cho Ticket management
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Self
from datetime import datetime, timezone


# ── Issue ─────────────────────────────────────────────────────

class TicketIssueRequest(BaseModel):
    """Phát hành vé mới — operator/cashier gọi."""
    customer_name:  str
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None

    ticket_type: str = Field(
        ...,
        pattern="^(adult|child|student|group)$",
        description="Loại vé: adult | child | student | group",
    )
    price:       float = Field(..., ge=0, description="Giá vé (VND)")
    valid_from:  datetime
    valid_until: datetime

    payment_method: str = Field(
        "cash",
        pattern="^(cash|card|qr_pay|demo)$",
        description="Phương thức thanh toán",
    )
    venue_id: str = "tourism_default"

    # ── Thông tin định danh tùy chọn (opt-in) ────────────────
    id_number:      Optional[str] = Field(
        None, description="CCCD/ID — backend hash trước khi lưu, không lưu số gốc"
    )
    phone_for_hash: Optional[str] = Field(
        None, description="SĐT dùng cho kênh MANUAL — sẽ hash trước khi lưu"
    )
    booking_id: Optional[str] = Field(
        None, description="Mã booking từ hệ thống bán vé ngoài"
    )

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until phải sau valid_from.")
        return self

    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        cleaned = re.sub(r"[^0-9]", "", v)
        if len(cleaned) < 9:
            raise ValueError("Số điện thoại không hợp lệ.")
        return cleaned


# ── Enroll face ───────────────────────────────────────────────

class TicketEnrollFaceRequest(BaseModel):
    """Đăng ký khuôn mặt opt-in cho vé."""
    face_image_b64: str = Field(..., description="Ảnh khuôn mặt base64 — không được lưu lại")


# ── Response ──────────────────────────────────────────────────

class TicketResponse(BaseModel):
    """Thông tin vé trả về (dùng cho issue + get)."""
    ticket_id:    str
    booking_id:   Optional[str] = None
    ticket_type:  str
    price:        float
    valid_from:   datetime
    valid_until:  datetime
    status:       str                       # active | used | revoked | expired
    has_face:     bool = False              # Đã đăng ký face hay chưa
    qr_image_b64: Optional[str] = None     # PNG base64 — chỉ trả về khi issue
    created_at:   datetime


class TicketRevokeRequest(BaseModel):
    """Thu hồi vé — admin/manager gọi."""
    reason: Optional[str] = Field(
        "manual_revoke",
        description="Lý do thu hồi — ghi vào audit log",
    )


class TicketListResponse(BaseModel):
    """Danh sách vé (dùng cho trang quản lý)."""
    total:   int
    tickets: list[TicketResponse]
 