"""
api/face_enroll.py — Đăng ký khuôn mặt opt-in cho vé
POST /api/face/enroll

Flow:
  1. Kiểm tra vé tồn tại và còn active
  2. Gọi AI Services POST /enroll → nhận embedding 512-d + image_hash
  3. Lưu embedding vào collection identities
  4. KHÔNG lưu ảnh gốc (privacy guard — chỉ lưu SHA-256 hash)
"""
import logging

import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.config import settings
from ..core.database import get_db
from ..core.security import require_min_role, Role, get_current_actor
from ..middleware.audit import log_action

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/face", tags=["Face"])


class FaceEnrollRequest(BaseModel):
    """
    Nhận 1 hoặc nhiều ảnh khuôn mặt.
    - images_b64: list ảnh (3–5 ảnh, theo góp ý GVHD) — ưu tiên
    - face_image_b64: 1 ảnh (legacy / fallback)
    """
    ticket_id:      str
    images_b64:     Optional[list[str]] = Field(
        None, description="Nhiều ảnh base64 (3–5 ảnh ở các góc khác nhau)"
    )
    face_image_b64: Optional[str] = Field(
        None, description="1 ảnh base64 (legacy — dùng khi không có images_b64)"
    )

    @property
    def all_images(self) -> list[str]:
        """Trả về danh sách ảnh dù dùng field nào."""
        if self.images_b64:
            return self.images_b64[:5]
        if self.face_image_b64:
            return [self.face_image_b64]
        return []


class FaceEnrollResponse(BaseModel):
    ticket_id:       str
    embedding_dim:   int
    face_image_hash: str
    message:         str


@router.post("/enroll", response_model=FaceEnrollResponse)
async def enroll_face(
    req: FaceEnrollRequest,
    request: Request,
    current_actor: dict = Depends(get_current_actor),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Đăng ký khuôn mặt cho vé (opt-in).
    - Operator/Admin: Đăng ký cho bất kỳ vé active nào.
    - Customer: Chỉ đăng ký được cho vé của CHÍNH MÌNH.
    """
    # 0. Kiểm tra quyền cơ bản (role >= customer - luôn đúng nếu qua get_current_actor)
    actor_role = current_actor.get("role")
    actor_id   = str(current_actor["_id"])

    # 1. Kiểm tra vé
    ticket = await db["tickets"].find_one({"_id": req.ticket_id})
    if not ticket:
        raise HTTPException(status_code=404, detail="Vé không tồn tại.")
    
    # Kiểm tra quyền sở hữu nếu là customer
    if actor_role == Role.CUSTOMER.value:
        if ticket.get("customer_id") != actor_id:
            raise HTTPException(status_code=403, detail="Bạn không có quyền đăng ký khuôn mặt cho vé này.")
    else:
        # Nếu không phải customer, yêu cầu tối thiểu Operator
        from ..core.security import ROLE_HIERARCHY
        if ROLE_HIERARCHY.get(Role(actor_role), 0) < ROLE_HIERARCHY[Role.OPERATOR]:
            raise HTTPException(status_code=403, detail="Cần quyền Operator để đăng ký khuôn mặt cho vé người khác.")

    if ticket.get("status") != "active":
        raise HTTPException(status_code=400,
                            detail=f"Vé không ở trạng thái active (hiện: {ticket.get('status')}).")

    # Validate có ít nhất 1 ảnh
    images = req.all_images
    if not images:
        raise HTTPException(
            status_code=422,
            detail="Cần cung cấp images_b64 (nhiều ảnh) hoặc face_image_b64 (1 ảnh)."
        )

    # 2. Gọi AI Services /enroll
    try:
        async with httpx.AsyncClient(
            base_url=settings.AI_SERVICE_URL,
            timeout=settings.AI_SERVICE_TIMEOUT,
        ) as client:
            # Gửi nhiều ảnh nếu có, 1 ảnh nếu dùng legacy field
            if len(images) > 1:
                payload = {"images_b64": images}
            else:
                payload = {"image_b64": images[0]}
            resp = await client.post("/enroll", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI Services trả về lỗi: {e.response.status_code}",
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI Services không khả dụng: {e}",
        )

    # Hỗ trợ cả nhiều embedding mẫu (mới) và 1 embedding (legacy)
    embeddings_multi = data.get("embeddings", [])       # list[list] — nhiều mẫu
    embedding_single = data.get("embedding", [])        # list — 1 mẫu (legacy)
    face_image_hash  = data.get("face_image_hash", "")
    n_embeddings     = data.get("n_embeddings", 1)

    if not embeddings_multi and not embedding_single:
        raise HTTPException(status_code=422, detail="AI Services không trả về embedding.")

    # Xây dựng $set cho identities
    set_doc: dict = {
        "face_image_hash": face_image_hash,
        "has_face":        True,
    }
    if embeddings_multi:
        # Lưu nhiều mẫu (theo góp ý GVHD: 3–5 mẫu)
        set_doc["face_embeddings"] = embeddings_multi
        set_doc["n_face_samples"]  = len(embeddings_multi)
        # Xóa trường cũ nếu tồn tại
        set_doc["face_embedding"]  = None
    else:
        # Legacy: 1 mẫu
        set_doc["face_embedding"]  = embedding_single

    # 3. Lưu vào identities (upsert)
    await db["identities"].update_one(
        {"ticket_id": req.ticket_id},
        {"$set": set_doc},
        upsert=True,
    )

    n_saved = len(embeddings_multi) if embeddings_multi else 1

    # 4. Audit log
    await log_action(
        db,
        actor_id,
        "FACE_ENROLL",
        resource=req.ticket_id,
        detail={
            "n_samples":     n_saved,
            "role":          actor_role,
            "embedding_dim": len(embeddings_multi[0]) if embeddings_multi else len(embedding_single),
            "hash_prefix":   face_image_hash[:16] + "..." if face_image_hash else "",
        },
        ip=request.client.host if request.client else None,
    )

    return FaceEnrollResponse(
        ticket_id=req.ticket_id,
        embedding_dim=len(embeddings_multi[0]) if embeddings_multi else len(embedding_single),
        face_image_hash=face_image_hash,
        message=f"Đăng ký {n_saved} mẫu khuôn mặt thành công. Ảnh gốc không được lưu.",
    )
 