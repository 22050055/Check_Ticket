"""
main.py — FastAPI Backend entry point
Tourism Access Control System
"""
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import connect_db, close_db, get_db
from .core.security import hash_password
from .models import new_user, new_gate
from .api import auth, tickets, checkin, gates, reports, websocket, face_enroll, customer
from .middleware.audit import AuditMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: kết nối Atlas, seed data. Shutdown: đóng kết nối."""
    await connect_db()
    await _seed_default_data()
    logger.info("🚀 Backend ready — Docs: http://localhost:8000/docs")
    yield
    await close_db()


async def _seed_default_data():
    """
    Tạo dữ liệu mặc định khi khởi động lần đầu:
    - 1 tài khoản admin
    - 2 cổng demo
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    # Admin
    if not await db["users"].find_one({"username": "admin"}):
        await db["users"].insert_one(
            new_user("admin", hash_password("admin123"), "Administrator", "admin")
        )
        logger.warning("✅ Tạo tài khoản admin (password: admin123) — ĐỔI NGAY!")

    # ── Tài khoản demo ───────────────────────────────────────────
    demo_users = [
        ("manager1",  "manager123",  "Quản lý 1",           "manager",  None),
        ("operator1", "operator123", "Nhân viên cổng A1",   "operator", "GATE_A1"),
        ("operator2", "operator123", "Nhân viên cổng A2",   "operator", "GATE_A2"),
        ("cashier1",  "cashier123",  "Thu ngân 1",          "cashier",  None),
    ]
    for username, password, full_name, role, gate_id in demo_users:
        if not await db["users"].find_one({"username": username}):
            await db["users"].insert_one(
                new_user(username, hash_password(password), full_name, role, gate_id)
            )
            logger.info("✅ Tạo tài khoản demo: %s (%s)", username, role)

    # Cổng demo
    if not await db["gates"].find_one({"gate_code": "GATE_A1"}):
        gates_data = [
            ("GATE_A1", "Cổng A1 — Vào chính",  "Khu vực A"),
            ("GATE_A2", "Cổng A2 — Ra chính",   "Khu vực A"),
        ]
        for code, name, location in gates_data:
            await db["gates"].insert_one(new_gate(code, name, location))
        logger.info("✅ Tạo 2 cổng demo: GATE_A1, GATE_A2")


# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Tourism Access Control — Backend API

Hệ thống kiểm soát ra/vào khu du lịch đa kênh:
- **QR** e-ticket (JWT RS256, anti-reuse nonce)
- **QR + Face** verification 1:1 (ArcFace buffalo_l, opt-in)
- **CCCD/ID** HMAC-SHA256 hash lookup
- **Booking ID** lookup
- **Manual** (SĐT / ticket_id)

### Roles
| Role | Quyền |
|------|-------|
| `admin` | Toàn quyền |
| `manager` | Báo cáo, quản lý vé, tạo user |
| `operator` | Check-in/out tại cổng, phát vé |
| `cashier` | Phát vé, xem doanh thu |
    """,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)

# ── Routers ───────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(checkin.router)
app.include_router(gates.router)
app.include_router(reports.router)
app.include_router(websocket.router)
app.include_router(face_enroll.router)
app.include_router(customer.router)
app.include_router(review.router)


# ── Health check ──────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status":  "ok",
        "service": "tourism-backend",
        "version": settings.APP_VERSION,
    }
 