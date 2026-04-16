import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import httpx

from ..core.config import settings
from ..core.database import get_db
from ..core.security import hash_password, verify_password, create_access_token, get_current_customer, Role
from ..schemas.customer import CustomerRegisterRequest, CustomerLoginRequest, CustomerResponse, TokenResponse
from ..schemas.ticket import TicketResponse, TicketEnrollFaceRequest
from .tickets import _make_qr_token
from ..services.qr_image_service import generate_qr_b64, generate_qr_png_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer", tags=["Customer"])

@router.post("/register", response_model=CustomerResponse)
async def register_customer(req: CustomerRegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Đăng ký tài khoản cho khách hàng mua vé/quản lý vé."""
    now = datetime.now(timezone.utc)
    
    # Kiểm tra email tồn tại
    existing = await db["customers"].find_one({"email": req.email})
    if existing and existing.get("hashed_password"):
        raise HTTPException(status_code=400, detail="Email này đã được đăng ký tài khoản.")
        
    hashed_pwd = hash_password(req.password)
    customer_id = str(uuid.uuid4())
    
    if existing:
        customer_id = str(existing["_id"])
        await db["customers"].update_one(
            {"_id": customer_id}, 
            {"$set": {"hashed_password": hashed_pwd, "name": req.name}}
        )
    else:
        await db["customers"].insert_one({
            "_id": customer_id,
            "name": req.name,
            "email": req.email,
            "phone": None,
            "hashed_password": hashed_pwd,
            "created_at": now
        })
        
    return CustomerResponse(id=customer_id, name=req.name, email=req.email)

@router.post("/login", response_model=TokenResponse)
async def login_customer(req: CustomerLoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Khách hàng đăng nhập lấy JWT token."""
    customer = await db["customers"].find_one({"email": req.email})
    if not customer or not customer.get("hashed_password") or not verify_password(req.password, customer["hashed_password"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
        
    # Tạo Access Token với role CUSTOMER
    token = create_access_token(str(customer["_id"]), Role.CUSTOMER.value)
    return TokenResponse(access_token=token)

@router.get("/tickets")
async def get_my_tickets(
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lấy danh sách các vé do customer này đã mua."""
    cursor = db["tickets"].find({"customer_id": str(customer["_id"])})
    tickets = await cursor.to_list(length=100)
    
    results = []
    for t in tickets:
        identity = await db["identities"].find_one({"ticket_id": str(t["_id"])})
        results.append({
            "ticket_id": str(t["_id"]),
            "booking_id": t.get("booking_id"),
            "ticket_type": t.get("ticket_type"),
            "price": t.get("price"),
            "valid_from": t.get("valid_from"),
            "valid_until": t.get("valid_until"),
            "status": t.get("status"),
            "venue_id": t.get("venue_id"),
            "has_face": identity.get("has_face", False) if identity else False,
            "created_at": t.get("created_at")
        })
    return results

@router.get("/tickets/{ticket_id}/qr.png")
async def download_my_qr(
    ticket_id: str,
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Khách tải ảnh QR của vé."""
    ticket = await db["tickets"].find_one({"_id": ticket_id, "customer_id": str(customer["_id"])})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại hoặc bạn không có quyền xem.")
        
    token = _make_qr_token(ticket_id, ticket["ticket_type"], ticket["valid_until"], ticket["venue_id"])
    if not token:
        raise HTTPException(500, "Lỗi server khi tạo nội dung ký QR.")
        
    qr_bytes = generate_qr_png_bytes(token)
    from io import BytesIO
    return StreamingResponse(
        BytesIO(qr_bytes), 
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="ticket-{ticket_id}.png"'}
    )

@router.post("/tickets/{ticket_id}/enroll-face")
async def enroll_my_face(
    ticket_id: str,
    req: TicketEnrollFaceRequest,
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Khách hàng tự đăng ký khuôn mặt cho vé của mình bằng camera thiết bị (ví dụ: điện thoại Android)."""
    ticket = await db["tickets"].find_one({"_id": ticket_id, "customer_id": str(customer["_id"])})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại hoặc bạn không có quyền thao tác.")
    if ticket.get("status") != "active":
        raise HTTPException(400, "Vé không còn hiệu lực.")

    try:
        async with httpx.AsyncClient(
            base_url=settings.AI_SERVICE_URL,
            timeout=settings.AI_SERVICE_TIMEOUT
        ) as client:
            resp = await client.post("/enroll", json={"image_b64": req.face_image_b64})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(503, f"AI Services không khả dụng: {e}")

    await db["identities"].update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "face_embedding":  data.get("embedding"),
            "face_image_hash": data.get("face_image_hash", ""),
            "has_face":        True,
        }},
        upsert=True,
    )
    return {
        "message": "Đăng ký khuôn mặt thành công.",
        "ticket_id": ticket_id
    }
