"""
middleware/audit.py — Audit logging cho hệ thống

Gồm 2 phần:
  1. log_action()     — ghi thủ công sau từng action quan trọng (login, issue ticket, ...)
  2. AuditMiddleware  — FastAPI middleware tự động log mọi request write (POST/PUT/DELETE)

Action constants re-export từ models.Action để các api file import 1 chỗ.
"""
import logging
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models import new_audit_log, Action

logger = logging.getLogger(__name__)


# ── Action constants (re-export) ──────────────────────────────
# Các api file chỉ cần import từ middleware.audit, không cần biết models

ACTION_LOGIN           = Action.LOGIN
ACTION_ISSUE_TICKET    = Action.ISSUE_TICKET
ACTION_REVOKE_TICKET   = Action.REVOKE_TICKET
ACTION_FACE_ENROLL     = Action.FACE_ENROLL
ACTION_CHECKIN         = Action.CHECKIN
ACTION_CHECKOUT        = Action.CHECKOUT
ACTION_CREATE_USER     = Action.CREATE_USER
ACTION_CREATE_GATE     = Action.CREATE_GATE
ACTION_DEACTIVATE_GATE = Action.DEACTIVATE_GATE
ACTION_EXPORT_REPORT   = Action.EXPORT_REPORT
ACTION_TICKET_AUTO_EXPIRED = "ticket_auto_expired"


# ── Manual log ────────────────────────────────────────────────

async def log_action(
    db:       AsyncIOMotorDatabase,
    user_id:  str,
    action:   str,
    resource: Optional[str] = None,
    detail:   Optional[dict] = None,
    ip:       Optional[str]  = None,
) -> None:
    """
    Ghi 1 audit log entry vào MongoDB.

    Thiết kế:
    - KHÔNG raise exception — lỗi log không được làm hỏng flow chính
    - Dùng new_audit_log() factory từ models để nhất quán schema
    - Gọi thủ công sau các action quan trọng trong api layer

    Ví dụ:
        await log_action(db, user_id, ACTION_ISSUE_TICKET,
                         resource=ticket_id,
                         detail={"type": "adult", "price": 150000},
                         ip=request.client.host)
    """
    try:
        doc = new_audit_log(
            user_id=user_id,
            action=action,
            resource=resource,
            detail=detail,
            ip=ip,
        )
        await db["audit_logs"].insert_one(doc)
    except Exception as e:
        logger.error("Không ghi được audit log action=%s user=%s: %s", action, user_id, e)


# ── Auto middleware ───────────────────────────────────────────

class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware: tự động ghi audit log cho mọi request write.
    Bổ sung cho log_action() — giúp trace các request không có log thủ công.

    Chỉ log:
    - Method: POST, PUT, DELETE, PATCH
    - Path bắt đầu bằng /api/
    - Bỏ qua: /health, /docs, /ws/

    Thông tin ghi:
    - method, path, status_code, duration_ms
    - user_id (từ JWT nếu đã decode)
    - ip address
    """

    # Path prefix bỏ qua
    _SKIP_PATHS = ("/health", "/docs", "/openapi", "/redoc", "/ws/")
    _LOG_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Bỏ qua method không phải write và path không thuộc /api/
        method = request.method.upper()
        path   = request.url.path

        should_log = (
            method in self._LOG_METHODS
            and path.startswith("/api/")
            and not any(path.startswith(s) for s in self._SKIP_PATHS)
        )

        if not should_log:
            return await call_next(request)

        # Đo thời gian xử lý
        t_start  = time.perf_counter()
        response = await call_next(request)
        duration = round((time.perf_counter() - t_start) * 1000, 1)

        status_code = response.status_code

        # Lấy user_id từ JWT đã decode (nếu có trong request.state)
        user_id = getattr(request.state, "user_id", "anonymous")

        # Lấy IP
        ip = None
        if request.client:
            ip = request.client.host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()

        # Log level: WARNING nếu lỗi 4xx/5xx
        msg = "%s %s → %d (%dms) user=%s ip=%s"
        args = (method, path, status_code, duration, user_id, ip)
        if status_code >= 400:
            logger.warning(msg, *args)
        else:
            logger.info(msg, *args)

        # Ghi vào MongoDB nếu có db trong request.state
        db: Optional[AsyncIOMotorDatabase] = getattr(request.state, "db", None)
        if db is not None:
            try:
                doc = new_audit_log(
                    user_id=user_id,
                    action=f"HTTP_{method}",
                    resource=path,
                    detail={
                        "status_code": status_code,
                        "duration_ms": duration,
                    },
                    ip=ip,
                )
                await db["audit_logs"].insert_one(doc)
            except Exception as e:
                logger.error("AuditMiddleware insert lỗi: %s", e)

        return response


# ── Query helpers ─────────────────────────────────────────────

async def get_audit_logs(
    db:        AsyncIOMotorDatabase,
    user_id:   Optional[str] = None,
    action:    Optional[str] = None,
    resource:  Optional[str] = None,
    limit:     int           = 50,
    skip:      int           = 0,
) -> list[dict]:
    """
    Truy vấn audit log — dùng cho trang lịch sử hành động (admin).

    Ví dụ:
        # Lịch sử của 1 user
        logs = await get_audit_logs(db, user_id="abc", limit=20)

        # Lịch sử revoke vé
        logs = await get_audit_logs(db, action=ACTION_REVOKE_TICKET)
    """
    query: dict = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    if resource:
        query["resource"] = resource

    cursor = (
        db["audit_logs"]
        .find(query, {"_id": 1, "user_id": 1, "action": 1,
                      "resource": 1, "detail": 1, "ip": 1, "created_at": 1})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    rows = await cursor.to_list(limit)

    # Serialize
    for r in rows:
        r["log_id"] = str(r.pop("_id"))
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()

    return rows
 