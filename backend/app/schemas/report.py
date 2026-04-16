"""
schemas/report.py — Response schemas cho Dashboard/Reports API

Endpoints dùng:
    GET /api/reports/revenue    → RevenueReport
    GET /api/reports/visitors   → VisitorReport
    GET /api/reports/errors     → ErrorRateReport
    GET /api/reports/realtime   → RealtimeStats  (cũng gửi qua WebSocket)
    GET /api/reports/export/... → StreamingResponse CSV (không dùng schema)
"""
from pydantic import BaseModel, Field
from typing import Optional


# ── Revenue ───────────────────────────────────────────────────

class RevenueByType(BaseModel):
    """Doanh thu theo loại vé."""
    ticket_type: str
    revenue:     float
    count:       int


class RevenueByDate(BaseModel):
    """Doanh thu theo ngày."""
    date:    str    # YYYY-MM-DD
    revenue: float
    count:   int


class RevenueReport(BaseModel):
    """
    GET /api/reports/revenue
    Dùng cho biểu đồ RevenueLineChart và bảng tổng hợp doanh thu.
    """
    total_revenue: float
    total_tickets: int
    by_type:       dict = Field(
        default_factory=dict,
        description='{"adult": 1500000, "child": 300000, ...}',
    )
    by_date:       list[dict] = Field(
        default_factory=list,
        description='[{"date": "2026-03-11", "revenue": 1800000, "count": 45}, ...]',
    )


# ── Visitors ──────────────────────────────────────────────────

class VisitorByGate(BaseModel):
    """Lượt vào/ra theo cổng."""
    gate_id:  str
    gate:     Optional[str] = None   # Tên cổng
    count:    int


class VisitorByHour(BaseModel):
    """Peak hours — số lượt theo từng giờ."""
    hour:  int    # 0–23
    count: int


class VisitorByChannel(BaseModel):
    """Tỷ lệ sử dụng từng kênh xác thực."""
    channel: str  # QR | QR_FACE | ID | BOOKING | MANUAL
    count:   int


class VisitorReport(BaseModel):
    """
    GET /api/reports/visitors
    Dùng cho ChannelPieChart, PeakHourChart, GateStatusCard.
    """
    total_checkins:  int
    total_checkouts: int
    current_inside:  int = Field(description="Số khách hiện đang trong khu = IN - OUT hôm nay")
    by_gate:         list[dict] = Field(default_factory=list)
    by_hour:         list[dict] = Field(default_factory=list)
    by_channel:      list[dict] = Field(default_factory=list)


# ── Error rates ───────────────────────────────────────────────

class ErrorRateByChannel(BaseModel):
    """Tỷ lệ lỗi theo từng kênh."""
    channel:    str
    total:      int
    failed:     int
    error_rate: float   # %


class ErrorRateReport(BaseModel):
    """
    GET /api/reports/errors
    Dùng cho biểu đồ ErrorRateChart trên Dashboard.
    """
    date_from:           str
    date_to:             str
    total_events:        int
    total_failed:        int
    overall_error_rate:  float = Field(description="Tỷ lệ lỗi tổng thể (%)")
    by_channel:          list[dict] = Field(default_factory=list)


# ── Realtime (WebSocket + /realtime poll) ─────────────────────

class GateStatus(BaseModel):
    """Trạng thái 1 cổng — dùng trong RealtimeStats."""
    gate_id:    str
    gate_code:  Optional[str] = None
    name:       Optional[str] = None
    last_event: Optional[str] = None    # SUCCESS | FAIL | None
    last_time:  Optional[str] = None    # ISO datetime


class RealtimeStats(BaseModel):
    """
    Snapshot realtime gửi qua WebSocket mỗi 5 giây.
    Cũng dùng cho GET /api/reports/realtime (fallback khi WS bị ngắt).

    type: "stats" — để Dashboard phân biệt với "gate_event" push.
    """
    type:             str = "stats"
    timestamp:        Optional[str] = None      # ISO datetime khi tạo

    current_inside:   int   = Field(description="Khách hiện đang trong khu")
    checkins_today:   int   = Field(description="Tổng lượt vào hôm nay")
    checkouts_today:  int   = Field(description="Tổng lượt ra hôm nay")
    revenue_today:    float = Field(description="Doanh thu hôm nay (VND)")
    error_rate_today: float = Field(description="Tỷ lệ lỗi check-in hôm nay (%)")

    recent_events: list[dict] = Field(
        default_factory=list,
        description="10 sự kiện gate_event gần nhất",
    )
    gates_status: list[dict] = Field(
        default_factory=list,
        description="Trạng thái từng cổng đang active",
    )


# ── Gate Event (log realtime) ─────────────────────────────────

class GateEventBroadcast(BaseModel):
    """
    Message push qua WebSocket ngay sau mỗi check-in/out.
    type: "gate_event" — Dashboard dùng để cập nhật bảng realtime.
    """
    type:        str = "gate_event"
    gate_id:     str
    direction:   str              # IN | OUT
    channel:     str              # QR | QR_FACE | ...
    result:      str              # SUCCESS | FAIL
    ticket_id:   Optional[str] = None
    ticket_type: Optional[str] = None
    message:     str
