"""
api/reports.py — Dashboard reports
GET /api/reports/revenue        — doanh thu theo ngày / loại vé
GET /api/reports/visitors       — lượt vào/ra, peak hours, channel usage
GET /api/reports/errors         — tỷ lệ lỗi check-in/out theo kênh
GET /api/reports/realtime       — snapshot realtime (fallback khi không có WS)
GET /api/reports/export/gate-events — export CSV
"""
import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import require_min_role, require_role, Role
from ..services.report_service import ReportService
from ..middleware.audit import log_action, get_audit_logs, ACTION_EXPORT_REPORT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _parse_date(s: Optional[str], default: datetime) -> datetime:
    """Parse ISO date string, fallback về default nếu lỗi."""
    if not s:
        return default
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return default


# ── GET /api/reports/revenue ──────────────────────────────────

@router.get("/revenue")
async def get_revenue(
    date_from: Optional[str] = Query(None, description="ISO datetime, mặc định 30 ngày trước"),
    date_to:   Optional[str] = Query(None, description="ISO datetime, mặc định hiện tại"),
    current_user: dict = Depends(require_min_role(Role.CASHIER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Doanh thu theo ngày và loại vé.
    Phân quyền: cashier, manager, admin.
    """
    now    = datetime.now(timezone.utc)
    d_from = _parse_date(date_from, now - timedelta(days=30))
    d_to   = _parse_date(date_to, now)
    return await ReportService(db).get_revenue(d_from, d_to)


# ── GET /api/reports/visitors ─────────────────────────────────

@router.get("/visitors")
async def get_visitors(
    date_from: Optional[str] = Query(None, description="ISO datetime, mặc định 24 giờ trước"),
    date_to:   Optional[str] = Query(None, description="ISO datetime, mặc định hiện tại"),
    gate_id:   Optional[str] = Query(None, description="Lọc theo cổng cụ thể"),
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Thống kê lượt vào/ra, khách hiện tại, peak hours, channel usage.
    Phân quyền: operator trở lên.
    """
    now    = datetime.now(timezone.utc)
    d_from = _parse_date(date_from, now - timedelta(days=1))
    d_to   = _parse_date(date_to, now)
    return await ReportService(db).get_visitors(d_from, d_to, gate_id=gate_id)


# ── GET /api/reports/errors ───────────────────────────────────

@router.get("/errors")
async def get_errors(
    date_from: Optional[str] = Query(None, description="ISO datetime, mặc định 24 giờ trước"),
    date_to:   Optional[str] = Query(None, description="ISO datetime, mặc định hiện tại"),
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Tỷ lệ lỗi check-in/out theo từng kênh.
    Dùng cho biểu đồ ErrorRateChart trên Dashboard.
    """
    now    = datetime.now(timezone.utc)
    d_from = _parse_date(date_from, now - timedelta(days=1))
    d_to   = _parse_date(date_to, now)
    return await ReportService(db).get_error_rates(d_from, d_to)


# ── GET /api/reports/realtime ─────────────────────────────────

@router.get("/realtime")
async def get_realtime(
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Snapshot realtime — Dashboard dùng để poll (fallback khi WS bị ngắt).
    Trả về cùng format với WebSocket push.
    """
    return await ReportService(db).get_realtime_stats()


# ── GET /api/reports/export/gate-events ──────────────────────

@router.get("/export/gate-events")
async def export_gate_events(
    date_from: Optional[str] = Query(None, description="ISO datetime, mặc định 7 ngày trước"),
    date_to:   Optional[str] = Query(None, description="ISO datetime, mặc định hiện tại"),
    current_user: dict = Depends(require_min_role(Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Export gate_events ra file CSV.
    Phân quyền: manager, admin.
    """
    now    = datetime.now(timezone.utc)
    d_from = _parse_date(date_from, now - timedelta(days=7))
    d_to   = _parse_date(date_to, now)

    events = await db["gate_events"].find(
        {"created_at": {"$gte": d_from, "$lte": d_to}},
        {"operator_id": 0},   # ẩn operator_id khỏi export
    ).sort("created_at", -1).to_list(10_000)

    # Build CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "event_id", "ticket_id", "ticket_type", "gate_id",
        "direction", "channel", "result", "fail_reason", "face_score", "created_at",
    ])
    writer.writeheader()
    for e in events:
        writer.writerow({
            "event_id":   str(e.get("_id", "")),
            "ticket_id":  e.get("ticket_id", ""),
            "ticket_type": e.get("ticket_type", ""),
            "gate_id":    e.get("gate_id", ""),
            "direction":  e.get("direction", ""),
            "channel":    e.get("channel", ""),
            "result":     e.get("result", ""),
            "fail_reason": e.get("fail_reason", ""),
            "face_score": e.get("face_score", ""),
            "created_at": e["created_at"].isoformat() if e.get("created_at") else "",
        })

    output.seek(0)
    filename = f"gate_events_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}.csv"

    await log_action(
        db, str(current_user["_id"]), ACTION_EXPORT_REPORT,
        detail={"type": "gate_events", "from": str(d_from), "to": str(d_to), "rows": len(events)},
    )

    return StreamingResponse(
        iter(["\ufeff", output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ── GET /api/reports/audit-logs ──────────────────────────────

@router.get("/audit-logs")
async def get_system_audit_logs(
    user_id:   Optional[str] = Query(None, description="Lọc theo user thực hiện"),
    action:    Optional[str] = Query(None, description="Lọc theo hành động"),
    resource:  Optional[str] = Query(None, description="Lọc theo tài nguyên (ticket_id, ...)"),
    limit:     int           = Query(50, ge=1, le=100),
    skip:      int           = Query(0, ge=0),
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Xem nhật ký thao tác toàn hệ thống.
    CHỈ DÀNH CHO ADMIN.
    """
    logs = await get_audit_logs(
        db, user_id=user_id, action=action, resource=resource,
        limit=limit, skip=skip
    )
    return logs
 