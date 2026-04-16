"""
models/__init__.py — MongoDB document schemas
Dùng TypedDict để type hint + IDE support.
Backend dùng Motor (raw dict), không dùng Beanie ODM.

Collections:
    users         — tài khoản nhân viên/admin
    customers     — thông tin khách (tối thiểu)
    identities    — mapping ticket ↔ kênh xác thực
    tickets       — vé điện tử
    transactions  — giao dịch doanh thu
    gates         — cổng ra/vào
    gate_events   — sự kiện check-in/out (IN/OUT log)
    audit_logs    — log hành động người dùng
    used_nonces   — nonce QR đã dùng (TTL index, anti-reuse)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from typing_extensions import TypedDict, NotRequired


# ══════════════════════════════════════════════════════════════
#  TypedDict Schemas
# ══════════════════════════════════════════════════════════════

class UserDoc(TypedDict):
    """
    Collection: users
    Indexes: username (unique)
    """
    _id:           str          # UUID
    username:      str          # unique
    password_hash: str          # bcrypt hash
    full_name:     str
    role:          str          # admin | manager | operator | cashier
    gate_id:       Optional[str]  # cổng mặc định cho operator
    is_active:     bool
    created_at:    datetime


class CustomerDoc(TypedDict):
    """
    Collection: customers
    Indexes: phone (unique sparse), email (sparse)
    Nguyên tắc tối thiểu dữ liệu: chỉ lưu những gì cần thiết.
    """
    _id:        str
    name:       str
    phone:      NotRequired[Optional[str]]
    email:      NotRequired[Optional[str]]
    created_at: datetime


class IdentityDoc(TypedDict):
    """
    Collection: identities
    Indexes: ticket_id (unique), booking_id (sparse), id_hash (sparse), phone_hash (sparse)

    Mapping 1 vé ↔ tất cả kênh xác thực:
      - QR:       qr_token (JWT RS256)
      - Face:     face_embedding (ArcFace 512-d) + face_image_hash (SHA-256)
      - CCCD/ID:  id_hash (HMAC-SHA256 với pepper, không lưu số gốc)
      - Booking:  booking_id
      - Manual:   phone_hash (HMAC-SHA256)
    """
    _id:             str
    ticket_id:       str            # FK → tickets._id (unique)
    booking_id:      NotRequired[Optional[str]]
    phone_hash:      NotRequired[Optional[str]]   # HMAC-SHA256 của SĐT
    id_hash:         NotRequired[Optional[str]]   # HMAC-SHA256 của CCCD/ID
    face_embedding:  NotRequired[Optional[list]]  # ArcFace 512-d float list
    face_image_hash: NotRequired[Optional[str]]   # SHA-256 ảnh (audit, không lưu ảnh gốc)
    has_face:        bool
    created_at:      datetime


class TicketDoc(TypedDict):
    """
    Collection: tickets
    Indexes: booking_id (sparse), customer_id, status, valid_from+valid_until
    """
    _id:         str            # UUID = ticket_id
    booking_id:  NotRequired[Optional[str]]
    customer_id: NotRequired[Optional[str]]   # FK → customers._id
    ticket_type: str            # adult | child | student | group
    price:       float
    valid_from:  datetime
    valid_until: datetime
    status:      str            # active | used | revoked | expired
    venue_id:    str
    created_at:  datetime
    updated_at:  datetime


class TransactionDoc(TypedDict):
    """
    Collection: transactions
    Indexes: ticket_id, created_at (descending)
    Dùng cho Dashboard doanh thu (aggregation pipeline).
    """
    _id:            str
    ticket_id:      str         # FK → tickets._id
    ticket_type:    str         # copy để query nhanh, không cần join
    amount:         float
    payment_method: str         # cash | card | qr_pay | demo
    created_at:     datetime


class GateDoc(TypedDict):
    """
    Collection: gates
    Indexes: gate_code (unique)
    """
    _id:        str
    gate_code:  str             # GATE_A1 (unique, uppercase)
    name:       str
    location:   NotRequired[Optional[str]]
    is_active:  bool
    created_at: datetime


class GateEventDoc(TypedDict):
    """
    Collection: gate_events
    Indexes: (gate_id, created_at desc), ticket_id, created_at desc,
             channel, result, direction
    Bảng trung tâm cho Dashboard realtime và đối soát.
    """
    _id:         str
    ticket_id:   NotRequired[Optional[str]]
    ticket_type: NotRequired[Optional[str]]   # copy để query nhanh
    gate_id:     str
    direction:   str            # IN | OUT
    channel:     str            # QR | QR_FACE | ID | BOOKING | MANUAL
    result:      str            # SUCCESS | FAIL
    fail_reason: NotRequired[Optional[str]]
    operator_id: NotRequired[Optional[str]]   # FK → users._id
    face_score:  NotRequired[Optional[float]] # cosine similarity nếu dùng QR_FACE
    created_at:  datetime


class AuditLogDoc(TypedDict):
    """
    Collection: audit_logs
    Indexes: created_at (descending), user_id
    """
    _id:       str
    user_id:   str              # FK → users._id
    action:    str              # LOGIN | ISSUE_TICKET | REVOKE_TICKET | FACE_ENROLL | ...
    resource:  NotRequired[Optional[str]]   # ID tài nguyên bị tác động
    detail:    NotRequired[Optional[dict]]
    ip:        NotRequired[Optional[str]]
    created_at: datetime


class UsedNonceDoc(TypedDict):
    """
    Collection: used_nonces
    Indexes: jti (unique), used_at (TTL — tự xóa sau NONCE_TTL_HOURS)
    Anti-reuse QR: mỗi JWT chỉ được quét 1 lần.
    """
    _id:       str
    jti:       str              # JWT ID từ QR payload
    ticket_id: NotRequired[Optional[str]]
    used_at:   datetime         # TTL index field


# ══════════════════════════════════════════════════════════════
#  Factory helpers — tạo document dict sẵn sàng insert_one()
# ══════════════════════════════════════════════════════════════

def new_user(
    username: str,
    password_hash: str,
    full_name: str,
    role: str,
    gate_id: Optional[str] = None,
) -> UserDoc:
    return {
        "_id":           str(uuid.uuid4()),
        "username":      username,
        "password_hash": password_hash,
        "full_name":     full_name,
        "role":          role,
        "gate_id":       gate_id,
        "is_active":     True,
        "created_at":    datetime.now(timezone.utc),
    }


def new_customer(
    name: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> CustomerDoc:
    return {
        "_id":        str(uuid.uuid4()),
        "name":       name,
        "phone":      phone,
        "email":      email,
        "created_at": datetime.now(timezone.utc),
    }


def new_identity(
    ticket_id: str,
    booking_id: Optional[str] = None,
    id_hash: Optional[str] = None,
    phone_hash: Optional[str] = None,
) -> IdentityDoc:
    return {
        "_id":             str(uuid.uuid4()),
        "ticket_id":       ticket_id,
        "booking_id":      booking_id,
        "phone_hash":      phone_hash,
        "id_hash":         id_hash,
        "face_embedding":  None,
        "face_image_hash": None,
        "has_face":        False,
        "created_at":      datetime.now(timezone.utc),
    }


def new_ticket(
    ticket_type: str,
    price: float,
    valid_from: datetime,
    valid_until: datetime,
    booking_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    venue_id: str = "tourism_default",
) -> TicketDoc:
    now = datetime.now(timezone.utc)
    return {
        "_id":         str(uuid.uuid4()),
        "booking_id":  booking_id,
        "customer_id": customer_id,
        "ticket_type": ticket_type,
        "price":       price,
        "valid_from":  valid_from,
        "valid_until": valid_until,
        "status":      "OUTSIDE",  # Mặc định: khách ở ngoài
        "venue_id":    venue_id,
        "created_at":  now,
        "updated_at":  now,
    }


def new_transaction(
    ticket_id: str,
    ticket_type: str,
    amount: float,
    payment_method: str = "cash",
) -> TransactionDoc:
    return {
        "_id":            str(uuid.uuid4()),
        "ticket_id":      ticket_id,
        "ticket_type":    ticket_type,
        "amount":         amount,
        "payment_method": payment_method,
        "created_at":     datetime.now(timezone.utc),
    }


def new_gate(
    gate_code: str,
    name: str,
    location: Optional[str] = None,
) -> GateDoc:
    return {
        "_id":        str(uuid.uuid4()),
        "gate_code":  gate_code.upper(),
        "name":       name,
        "location":   location,
        "is_active":  True,
        "created_at": datetime.now(timezone.utc),
    }


def new_gate_event(
    gate_id: str,
    direction: str,
    channel: str,
    result: str,
    ticket_id: Optional[str] = None,
    ticket_type: Optional[str] = None,
    fail_reason: Optional[str] = None,
    operator_id: Optional[str] = None,
    face_score: Optional[float] = None,
) -> GateEventDoc:
    return {
        "_id":         str(uuid.uuid4()),
        "ticket_id":   ticket_id,
        "ticket_type": ticket_type,
        "gate_id":     gate_id,
        "direction":   direction,
        "channel":     channel,
        "result":      result,
        "fail_reason": fail_reason,
        "operator_id": operator_id,
        "face_score":  face_score,
        "created_at":  datetime.now(timezone.utc),
    }


def new_audit_log(
    user_id: str,
    action: str,
    resource: Optional[str] = None,
    detail: Optional[dict] = None,
    ip: Optional[str] = None,
) -> AuditLogDoc:
    return {
        "_id":        str(uuid.uuid4()),
        "user_id":    user_id,
        "action":     action,
        "resource":   resource,
        "detail":     detail,
        "ip":         ip,
        "created_at": datetime.now(timezone.utc),
    }


def new_used_nonce(
    jti: str,
    ticket_id: Optional[str] = None,
) -> UsedNonceDoc:
    return {
        "_id":       str(uuid.uuid4()),
        "jti":       jti,
        "ticket_id": ticket_id,
        "used_at":   datetime.now(timezone.utc),
    }


# ══════════════════════════════════════════════════════════════
#  Constants
# ══════════════════════════════════════════════════════════════

class TicketStatus:
    OUTSIDE = "OUTSIDE"   # Khách đang ở ngoài (trạng thái ban đầu)
    INSIDE  = "INSIDE"    # Khách đang ở trong khu
    REVOKED = "revoked"   # Vé bị thu hồi
    EXPIRED = "expired"   # Vé hết hạn
    # Tương thích ngược
    ACTIVE  = "OUTSIDE"   # alias


class GateEventResult:
    SUCCESS = "SUCCESS"
    FAIL    = "FAIL"


class Direction:
    IN  = "IN"
    OUT = "OUT"


class Channel:
    QR       = "QR"
    QR_FACE  = "QR_FACE"
    ID       = "ID"
    BOOKING  = "BOOKING"
    MANUAL   = "MANUAL"


class Role:
    ADMIN    = "admin"
    MANAGER  = "manager"
    OPERATOR = "operator"
    CASHIER  = "cashier"


class Action:
    """Audit log action constants."""
    LOGIN          = "LOGIN"
    ISSUE_TICKET   = "ISSUE_TICKET"
    REVOKE_TICKET  = "REVOKE_TICKET"
    FACE_ENROLL    = "FACE_ENROLL"
    CHECKIN        = "CHECKIN"
    CHECKOUT       = "CHECKOUT"
    CREATE_USER    = "CREATE_USER"
    CREATE_GATE    = "CREATE_GATE"
    DEACTIVATE_GATE = "DEACTIVATE_GATE"
    EXPORT_REPORT  = "EXPORT_REPORT"
