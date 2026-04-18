from fastapi import APIRouter, Depends, HTTPException, Body
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Dict, Optional

from ..core.database import get_db
from ..core.security import require_min_role, Role
from ..services.ai_service import AiService

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

@router.post("/chat")
async def ai_chat(
    message: str = Body(..., embed=True),
    history: Optional[List[Dict[str, str]]] = Body(None),
    current_user: dict = Depends(require_min_role(Role.CUSTOMER)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Endpoint chat với trợ lý ảo AI. 
    Hỗ trợ cả Nhân viên (Dashboard) và Khách hàng (Mobile App).
    """
    service = AiService(db, user_email=current_user.get("user_id"), user_role=current_user.get("role"))
    response_text = await service.chat(message, history)
    
    return {
        "reply": response_text
    }
