import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from jose import jwt, JWTError

from ..core.database import get_db
from ..core.config import settings
from ..core.security import Role
from ..services.report_service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])


# ── Connection Manager ────────────────────────────────────────

class ConnectionManager:
    """
    Quản lý danh sách WebSocket client đang kết nối.
    Theo dõi user_id để hiển thị trạng thái 'Đang hoạt động'.
    """

    def __init__(self):
        # { user_id: [WebSocket, ...] }
        self._user_connections: dict[str, list[WebSocket]] = {}
        # { WebSocket: user_id }
        self._ws_to_user: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, user_id: Optional[str] = None, db: Optional[AsyncIOMotorDatabase] = None):
        await ws.accept()
        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = []
                # Nếu là connection đầu tiên của user này, cập nhật DB là Online
                if db is not None:
                    await db["users"].update_one({"_id": user_id}, {"$set": {"is_online": True, "last_seen": datetime.now(timezone.utc)}})
            
            self._user_connections[user_id].append(ws)
            self._ws_to_user[ws] = user_id
            
        logger.info("📡 WS connected. User: %s. Total users online: %d", user_id, len(self._user_connections))

    async def disconnect(self, ws: WebSocket, db: Optional[AsyncIOMotorDatabase] = None):
        user_id = self._ws_to_user.get(ws)
        if ws in self._ws_to_user:
            del self._ws_to_user[ws]
        
        if user_id and user_id in self._user_connections:
            if ws in self._user_connections[user_id]:
                self._user_connections[user_id].remove(ws)
            
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
                # Nếu là connection cuối cùng, cập nhật DB là Offline
                if db is not None:
                    await db["users"].update_one({"_id": user_id}, {"$set": {"is_online": False, "last_seen": datetime.now(timezone.utc)}})

        logger.info("📡 WS disconnected. User: %s. Remaining users: %d", user_id, len(self._user_connections))

    async def broadcast(self, data: dict):
        msg = json.dumps(data, ensure_ascii=False, default=str)
        dead = []
        # Broadcast to all connected sockets
        for ws in self._ws_to_user.keys():
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        
        for ws in dead:
            await self.disconnect(ws)

# Singleton
manager = ConnectionManager()


# ── WebSocket endpoint ────────────────────────────────────────

@router.websocket("/ws/realtime")
async def realtime_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = None
    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            # Chỉ track presence cho nhân viên (không track khách hàng để bảo mật riêng tư)
            if payload.get("role") != Role.CUSTOMER.value:
                user_id = payload.get("sub")
        except JWTError:
            pass

    await manager.connect(websocket, user_id, db)
    svc = ReportService(db)

    try:
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

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if msg.strip().lower() == "ping":
                    await websocket.send_text("pong")
                # Theo dõi hoạt động để cập nhật last_seen
                if user_id:
                    await db["users"].update_one({"_id": user_id}, {"$set": {"last_seen": datetime.now(timezone.utc)}})
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        push_task.cancel()
        await manager.disconnect(websocket, db)
 