from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import require_min_role, Role
from ..services.ai_service import AiService

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []

@router.post("/chat")
async def ai_chat(
    req: ChatRequest,
    current_user: dict = Depends(require_min_role(Role.CUSTOMER)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Endpoint chat với trợ lý ảo AI. 
    Hỗ trợ cả Nhân viên (Dashboard) và Khách hàng (Mobile App).
    """
    service = AiService(db, user_email=current_user.get("user_id"), user_role=current_user.get("role"))
    response_text = await service.chat(req.message, req.history)
    
    return {
        "reply": response_text
    }
