"""
api/checkin.py — Endpoint thống nhất check-in/out
POST /api/checkin — route theo channel → ChannelAdapter → broadcast WebSocket
"""
import logging
from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import require_min_role, Role
from ..schemas.checkin import CheckinRequest, CheckinResponse
from ..services.channel_adapter import ChannelAdapter
from ..middleware.audit import log_action, ACTION_CHECKIN, ACTION_CHECKOUT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/checkin", tags=["Check-in/out"])


def get_adapter(db: AsyncIOMotorDatabase = Depends(get_db)) -> ChannelAdapter:
    """
    Tạo ChannelAdapter mới mỗi request — inject db đúng cách.
    ChannelAdapter giữ httpx.AsyncClient nội bộ, không cần singleton.
    """
    return ChannelAdapter(db)


@router.post("", response_model=CheckinResponse)
async def checkin(
    req: CheckinRequest,
    request: Request,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
    adapter: ChannelAdapter = Depends(get_adapter),
):
    """
    Endpoint duy nhất cho mọi kênh check-in/out.
    Gate App gọi endpoint này, truyền channel tương ứng.

    Sau khi xử lý:
    - Lưu gate_event vào MongoDB
    - Broadcast realtime tới Dashboard qua WebSocket
    - Ghi audit log
    """
    operator_id = str(current_user["_id"])

    result = await adapter.process(
        channel         = req.channel,
        direction       = req.direction,
        gate_id         = req.gate_id,
        operator_id     = operator_id,
        qr_token        = req.qr_token,
        probe_image_b64 = req.probe_image_b64,
        id_number       = req.id_number,
        booking_id      = req.booking_id,
        phone           = req.phone,
        ticket_id       = req.ticket_id,
    )

    # Broadcast realtime tới Dashboard
    from .websocket import manager
    await manager.broadcast({
        "type":       "gate_event",
        "gate_id":    req.gate_id,
        "direction":  req.direction.value,
        "channel":    req.channel.value,
        "result":     "SUCCESS" if result.success else "FAIL",
        "ticket_id":  result.ticket_id,
        "ticket_type": result.ticket_type,
        "message":    result.message,
    })

    # Audit log
    action = ACTION_CHECKIN if req.direction.value == "IN" else ACTION_CHECKOUT
    await log_action(
        db, operator_id, action,
        resource=result.ticket_id,
        detail={
            "channel":  req.channel.value,
            "gate_id":  req.gate_id,
            "success":  result.success,
            "message":  result.message,
        },
        ip=request.client.host if request.client else None,
    )

    return CheckinResponse(
        success     = result.success,
        ticket_id   = result.ticket_id,
        ticket_type = result.ticket_type,
        direction   = req.direction.value,
        channel     = req.channel.value,
        message     = result.message,
        face_score  = result.face_score,
    )
