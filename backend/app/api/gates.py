"""
api/gates.py — Quản lý cổng ra/vào
GET    /api/gates           — danh sách cổng
POST   /api/gates           — tạo cổng mới (admin)
GET    /api/gates/{id}      — chi tiết 1 cổng
PUT    /api/gates/{id}/deactivate — tắt cổng (admin)
GET    /api/gates/{id}/events     — log sự kiện gần nhất của cổng
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import require_role, require_min_role, Role
from ..middleware.audit import log_action, ACTION_CREATE_GATE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gates", tags=["Gates"])


# ── Schemas (inline — gate không cần file riêng) ──────────────

class GateCreate(BaseModel):
    gate_code: str
    name:      str
    location:  Optional[str] = None


class GateResponse(BaseModel):
    gate_id:   str
    gate_code: str
    name:      str
    location:  Optional[str]
    is_active: bool


# ── POST /api/gates ───────────────────────────────────────────

@router.post("", response_model=GateResponse, status_code=201)
async def create_gate(
    req: GateCreate,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Tạo cổng mới — chỉ Admin."""
    if await db["gates"].find_one({"gate_code": req.gate_code.upper()}):
        raise HTTPException(400, f"gate_code='{req.gate_code}' đã tồn tại.")

    gate_id = str(uuid.uuid4())
    await db["gates"].insert_one({
        "_id":        gate_id,
        "gate_code":  req.gate_code.upper(),
        "name":       req.name,
        "location":   req.location,
        "is_active":  True,
        "created_at": datetime.now(timezone.utc),
    })
    await log_action(db, str(current_user["_id"]), ACTION_CREATE_GATE,
                     resource=gate_id, detail={"gate_code": req.gate_code.upper()})

    return GateResponse(gate_id=gate_id, gate_code=req.gate_code.upper(),
                        name=req.name, location=req.location, is_active=True)


# ── GET /api/gates ────────────────────────────────────────────

@router.get("", response_model=list[GateResponse])
async def list_gates(
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Danh sách tất cả cổng — operator trở lên."""
    gates = await db["gates"].find({}).sort("gate_code", 1).to_list(50)
    return [
        GateResponse(
            gate_id=str(g["_id"]), gate_code=g["gate_code"],
            name=g["name"], location=g.get("location"),
            is_active=g["is_active"],
        )
        for g in gates
    ]


# ── GET /api/gates/{gate_id} ──────────────────────────────────

@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(
    gate_id: str,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Chi tiết 1 cổng theo ID."""
    gate = await db["gates"].find_one({"_id": gate_id})
    if not gate:
        raise HTTPException(404, "Không tìm thấy cổng.")
    return GateResponse(
        gate_id=str(gate["_id"]), gate_code=gate["gate_code"],
        name=gate["name"], location=gate.get("location"),
        is_active=gate["is_active"],
    )


# ── PUT /api/gates/{gate_id}/deactivate ───────────────────────

@router.put("/{gate_id}/deactivate")
async def deactivate_gate(
    gate_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Tắt cổng — chỉ Admin."""
    gate = await db["gates"].find_one({"_id": gate_id})
    if not gate:
        raise HTTPException(404, "Không tìm thấy cổng.")
    if not gate.get("is_active"):
        raise HTTPException(400, "Cổng đã bị tắt từ trước.")

    await db["gates"].update_one(
        {"_id": gate_id},
        {"$set": {"is_active": False}},
    )
    await log_action(db, str(current_user["_id"]), "DEACTIVATE_GATE", resource=gate_id)
    return {"message": f"Đã tắt cổng {gate.get('gate_code')}.", "gate_id": gate_id}


# ── GET /api/gates/{gate_id}/events ──────────────────────────

@router.get("/{gate_id}/events")
async def get_gate_events(
    gate_id: str,
    limit: int = 50,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Log sự kiện gần nhất của 1 cổng.
    Dùng cho màn hình monitor tại cổng (Gate App hoặc Dashboard).
    Ẩn fail_reason và operator_id để bảo mật.
    """
    if limit > 200:
        limit = 200

    events = await db["gate_events"].find(
        {"gate_id": gate_id},
        {"fail_reason": 0, "operator_id": 0},   # ẩn trường nhạy cảm
    ).sort("created_at", -1).limit(limit).to_list(limit)

    for e in events:
        e["event_id"] = str(e.pop("_id"))
        if "created_at" in e:
            e["created_at"] = e["created_at"].isoformat()

    return {"gate_id": gate_id, "count": len(events), "events": events}
 