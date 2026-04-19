from fastapi import APIRouter, Depends, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..core.database import get_db
from ..core.security import require_role, Role
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["System Settings"])

class ModelUpdate(BaseModel):
    model_name: str

@router.get("/ai-model")
async def get_active_model(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Lấy tên mô hình AI đang được kích hoạt."""
    config = await db["system_configs"].find_one({"key": "active_ai_model"})
    if config:
        return {"model_name": config["value"]}
    
    # Mặc định lấy từ ENV nếu chưa có trong DB
    from ..core.config import settings
    return {"model_name": settings.AI_MODEL_NAME}

@router.post("/ai-model")
async def update_active_model(
    req: ModelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_admin: dict = Depends(require_role(Role.ADMIN))
):
    """Cập nhật mô hình AI (Chỉ ADMIN)."""
    await db["system_configs"].update_one(
        {"key": "active_ai_model"},
        {"$set": {"value": req.model_name, "updated_by": current_admin.get("username")}},
        upsert=True
    )
    return {"message": f"Đã cập nhật mô hình AI sang {req.model_name}"}
