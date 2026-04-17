"""
core/database.py — Kết nối MongoDB Atlas async dùng Motor
Collections:
    users           — tài khoản nhân viên/admin
    customers       — thông tin khách (tối thiểu)
    identities      — mapping ticket ↔ kênh xác thực
    tickets         — vé điện tử
    transactions    — giao dịch doanh thu
    gates           — cổng ra/vào
    gate_events     — sự kiện check-in/out (IN/OUT log)
    audit_logs      — log hành động người dùng
    used_nonces     — nonce QR đã dùng (TTL index, anti-reuse)
"""
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.server_api import ServerApi

from .config import settings

logger = logging.getLogger(__name__)

# ── Singleton ─────────────────────────────────────────────────
_client: AsyncIOMotorClient | None = None
_db:     AsyncIOMotorDatabase | None = None


# ── Startup / Shutdown ────────────────────────────────────────

async def connect_db() -> None:
    """
    Khởi tạo Motor client kết nối MongoDB Atlas.
    Gọi trong lifespan FastAPI (startup).
    """
    global _client, _db

    uri = settings.mongo_uri_with_password

    # ServerApi(1): dùng MongoDB Stable API — bắt buộc với Atlas
    _client = AsyncIOMotorClient(
        uri,
        server_api=ServerApi("1"),
        # Atlas dùng TLS mặc định qua SRV, không cần khai báo thêm
        connectTimeoutMS=10_000,
        socketTimeoutMS=30_000,
        serverSelectionTimeoutMS=10_000,
    )
    _db = _client[settings.MONGO_DB]

    # Ping để xác nhận kết nối thành công ngay khi startup
    await _client.admin.command("ping")
    logger.info(
        "✅ MongoDB Atlas connected — cluster: khang1402 / db: %s",
        settings.MONGO_DB,
    )

    await _create_indexes()


async def close_db() -> None:
    """Đóng kết nối. Gọi trong lifespan FastAPI (shutdown)."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


# ── Dependency Injection ──────────────────────────────────────

def get_db() -> AsyncIOMotorDatabase:
    """
    FastAPI Depends — inject db vào endpoint.

    Dùng:
        @router.get("/")
        async def endpoint(db = Depends(get_db)):
            ...
    """
    if _db is None:
        raise RuntimeError("DB chưa được khởi tạo. connect_db() phải chạy trước.")
    return _db


# ── Indexes ───────────────────────────────────────────────────

async def _create_indexes() -> None:
    """
    Tạo indexes khi startup.
    - unique=True: đảm bảo tính toàn vẹn dữ liệu
    - sparse=True: chỉ index document có trường đó (field optional)
    - TTL index: MongoDB Atlas tự xóa used_nonces sau NONCE_TTL_HOURS
    """
    db = _db

    # ── users ─────────────────────────────────────────────────
    await db["users"].create_index(
        [("username", ASCENDING)],
        unique=True,
        name="idx_users_username",
    )

    # ── customers ─────────────────────────────────────────────
    await db["customers"].create_index(
        [("phone", ASCENDING)],
        unique=True, sparse=True,
        name="idx_customers_phone",
    )
    await db["customers"].create_index(
        [("email", ASCENDING)],
        sparse=True,
        name="idx_customers_email",
    )

    # ── identities — lookup nhanh theo từng kênh xác thực ─────
    await db["identities"].create_index(
        [("ticket_id", ASCENDING)],
        unique=True,
        name="idx_identities_ticket_id",
    )
    await db["identities"].create_index(
        [("booking_id", ASCENDING)],
        sparse=True,
        name="idx_identities_booking_id",
    )
    await db["identities"].create_index(
        [("id_hash", ASCENDING)],
        sparse=True,
        name="idx_identities_id_hash",
    )
    await db["identities"].create_index(
        [("phone_hash", ASCENDING)],
        sparse=True,
        name="idx_identities_phone_hash",
    )

    # ── tickets ───────────────────────────────────────────────
    await db["tickets"].create_index(
        [("booking_id", ASCENDING)],
        sparse=True,
        name="idx_tickets_booking_id",
    )
    await db["tickets"].create_index(
        [("customer_id", ASCENDING)],
        name="idx_tickets_customer_id",
    )
    await db["tickets"].create_index(
        [("status", ASCENDING)],
        name="idx_tickets_status",
    )
    await db["tickets"].create_index(
        [("valid_from", ASCENDING), ("valid_until", ASCENDING)],
        name="idx_tickets_validity",
    )

    # ── transactions ──────────────────────────────────────────
    await db["transactions"].create_index(
        [("ticket_id", ASCENDING)],
        name="idx_transactions_ticket_id",
    )
    await db["transactions"].create_index(
        [("created_at", DESCENDING)],
        name="idx_transactions_created_at",
    )

    # ── gates ─────────────────────────────────────────────────
    await db["gates"].create_index(
        [("gate_code", ASCENDING)],
        unique=True,
        name="idx_gates_gate_code",
    )

    # ── gate_events — query Dashboard realtime & báo cáo ──────
    await db["gate_events"].create_index(
        [("gate_id", ASCENDING), ("created_at", DESCENDING)],
        name="idx_gate_events_gate_time",
    )
    await db["gate_events"].create_index(
        [("ticket_id", ASCENDING)],
        name="idx_gate_events_ticket_id",
    )
    await db["gate_events"].create_index(
        [("created_at", DESCENDING)],
        name="idx_gate_events_created_at",
    )
    await db["gate_events"].create_index(
        [("channel", ASCENDING)],
        name="idx_gate_events_channel",
    )
    await db["gate_events"].create_index(
        [("result", ASCENDING)],
        name="idx_gate_events_result",
    )
    await db["gate_events"].create_index(
        [("direction", ASCENDING)],
        name="idx_gate_events_direction",
    )

    # ── audit_logs ────────────────────────────────────────────
    await db["audit_logs"].create_index(
        [("created_at", DESCENDING)],
        name="idx_audit_logs_created_at",
    )
    await db["audit_logs"].create_index(
        [("user_id", ASCENDING)],
        name="idx_audit_logs_user_id",
    )

    # ── used_nonces — TTL index (Atlas tự xóa sau N giờ) ──────
    await db["used_nonces"].create_index(
        [("used_at", ASCENDING)],
        expireAfterSeconds=settings.NONCE_TTL_HOURS * 3600,
        background=True,
        name="idx_used_nonces_ttl",
    )
    await db["used_nonces"].create_index(
        [("jti", ASCENDING)],
        unique=True,
        name="idx_used_nonces_jti",
    )

    logger.info("✅ MongoDB indexes ready.")
 