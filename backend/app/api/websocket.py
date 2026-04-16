"""
api/websocket.py — WebSocket realtime cho Dashboard
WS /ws/realtime — server push stats + gate_events mỗi 5 giây

Hai loại message server gửi tới Dashboard:
  1. type=stats     — snapshot realtime (mỗi 5 giây)
  2. type=gate_event — sự kiện check-in/out ngay lập tức (từ checkin.py)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..services.report_service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


# ── Connection Manager ────────────────────────────────────────

class ConnectionManager:
    """
    Quản lý danh sách WebSocket client đang kết nối.
    Thread-safe với asyncio (single event loop).
    """

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info("📡 WS client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("📡 WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, data: dict):
        """
        Gửi data tới tất cả client đang kết nối.
        Tự dọn client chết (đã ngắt kết nối nhưng chưa raise exception).
        Gọi từ:
          - Loop 5 giây trong ws endpoint (type=stats)
          - checkin.py sau mỗi gate_event (type=gate_event)
        """
        dead = []
        msg  = json.dumps(data, ensure_ascii=False, default=str)
        for ws in self._connections.copy():
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


# Singleton — dùng chung toàn app
manager = ConnectionManager()


# ── WebSocket endpoint ────────────────────────────────────────

@router.websocket("/ws/realtime")
async def realtime_ws(
    websocket: WebSocket,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Dashboard connect vào endpoint này để nhận realtime data.

    Giao thức:
      - Server push JSON mỗi 5 giây: {"type": "stats", ...stats_data}
      - Client có thể gửi ping: "ping" → server trả "pong"
      - Gate_events được push ngay khi xảy ra từ checkin.py
    """
    await manager.connect(websocket)
    svc = ReportService(db)

    try:
        # Task vòng lặp push stats mỗi 5 giây
        async def _push_loop():
            while True:
                try:
                    stats = await svc.get_realtime_stats()
                    stats["type"]      = "stats"
                    stats["timestamp"] = datetime.now(timezone.utc).isoformat()
                    await websocket.send_json(stats)
                except Exception as e:
                    logger.error("WS push error: %s", e)
                await asyncio.sleep(5)

        push_task = asyncio.create_task(_push_loop())

        # Nhận message từ client (ping/pong keepalive)
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if msg.strip().lower() == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Timeout bình thường — client chưa gửi gì
                pass
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        manager.disconnect(websocket)
