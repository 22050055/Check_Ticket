import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
import httpx

from ..core.config import settings
from ..core.database import get_db
from ..core.security import hash_password, verify_password, create_access_token, get_current_customer, Role, require_min_role
from ..schemas.customer import CustomerRegisterRequest, CustomerLoginRequest, CustomerResponse, TokenResponse, CustomerBuyTicketRequest, CustomerUpdateByAdminRequest
from ..schemas.ticket import TicketResponse, TicketEnrollFaceRequest
from .tickets import _make_qr_token, _auto_cleanup_expired_tickets
from ..services.qr_image_service import generate_qr_b64, generate_qr_png_bytes
from ..middleware.audit import log_action, ACTION_REVOKE_TICKET

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
        
    try:
        hashed_pwd = hash_password(req.password)
        customer_id = str(uuid.uuid4())
        
        # Chuẩn bị dữ liệu chèn (Chỉ bao gồm phone nếu có giá trị để tránh lỗi UNIQUE index khi giá trị là null)
        insert_data = {
            "_id": customer_id,
            "name": req.name,
            "email": req.email,
            "hashed_password": hashed_pwd,
            "created_at": now
        }
        if req.phone:
            insert_data["phone"] = req.phone

        if existing:
            customer_id = str(existing["_id"])
            await db["customers"].update_one(
                {"_id": customer_id}, 
                {"$set": {"hashed_password": hashed_pwd, "name": req.name}}
            )
        else:
            await db["customers"].insert_one(insert_data)
    except Exception as e:
        logger.error(f"Error registering customer: {e}")
        raise HTTPException(status_code=500, detail=f"DEBUG ERROR: {str(e)}")
        
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
    """Lấy danh sách các vé do customer này đã mua. Tự động kiểm tra hết hạn."""
    await _auto_cleanup_expired_tickets(db)
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
            timeout=settings.AI_SERVICE_TIMEOUT,
            headers={"ngrok-skip-browser-warning": "69420"}
        ) as client:
            resp = await client.post("/enroll", json={"image_b64": req.face_image_b64})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"AI Services error during customer enroll: {e}")
        raise HTTPException(503, f"Hệ thống xác thực khuôn mặt đang gặp sự cố. Vui lòng thử lại sau.")

    await db["identities"].update_one(
        {"ticket_id": ticket_id},
        {"$set": {
            "face_embeddings": data.get("embeddings"), # Lưu danh sách mẫu (ưu tiên)
            "face_embedding":  data.get("embeddings", [None])[0], # Fallback mẫu đầu tiên
            "face_image_hash": data.get("face_image_hash", ""),
            "has_face":        True,
        }},
        upsert=True,
    )
    return {
        "message": "Đăng ký khuôn mặt thành công.",
        "ticket_id": ticket_id
    }

@router.post("/buy-ticket", response_model=TicketResponse, status_code=201)
async def buy_ticket(
    req: CustomerBuyTicketRequest,
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Khách hàng tự mua vé online."""
    ticket_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Định nghĩa giá vé cơ bản (có thể lấy từ DB nếu có bảng cấu hình)
    prices = {
        "adult": 150000.0,
        "child": 80000.0,
        "student": 100000.0,
        "group": 500000.0
    }
    price = prices.get(req.ticket_type, 150000.0)
    
    # Hiệu lực trong ngày
    from datetime import time
    vn_tz = timezone(timedelta(hours=7)) # Múi giờ Việt Nam
    
    if req.valid_date:
        try:
            target_date = datetime.strptime(req.valid_date, "%Y-%m-%d").date()
            # Giờ mở cửa 07:00, đóng cửa 22:00 (Giờ VN)
            valid_from = datetime.combine(target_date, time(7, 0, 0)).replace(tzinfo=vn_tz)
            valid_until = datetime.combine(target_date, time(22, 0, 0)).replace(tzinfo=vn_tz)
            
            # Nếu là hôm nay và đã qua 7h, thì lấy giờ hiện tại làm valid_from
            if target_date == now.date() and now > valid_from:
                valid_from = now
        except ValueError:
            valid_from = datetime.combine(now.date(), time(7, 0, 0)).replace(tzinfo=vn_tz)
            valid_until = datetime.combine(now.date(), time(22, 0, 0)).replace(tzinfo=vn_tz)
    else:
        # Mặc định lấy ngày hôm nay
        start_7h = datetime.combine(now.date(), time(7, 0, 0)).replace(tzinfo=vn_tz)
        valid_from = now if now > start_7h else start_7h
        valid_until = datetime.combine(now.date(), time(22, 0, 0)).replace(tzinfo=vn_tz)
    customer_id = str(customer["_id"])
    
    # 0. Nới lỏng: Cho phép khách mua online ngay cả khi chưa cập nhật SĐT/CCCD.
    # (Vì App Android hiện tại chưa có form cập nhật thông tin cá nhân)
    # if not customer.get("phone") or not customer.get("cccd"):
    #     raise HTTPException(
    #         status_code=400, 
    #         detail="Bạn cần cập nhật Số điện thoại và CCCD trong phần quản lý tài khoản trước khi mua vé online."
    #     )

    booking_id = f"OL-{uuid.uuid4().hex[:8].upper()}"

    # 1. Tạo Ticket
    await db["tickets"].insert_one({
        "_id": ticket_id,
        "booking_id": booking_id,
        "customer_id": customer_id,
        "ticket_type": req.ticket_type,
        "price": price,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "status": "active",
        "venue_id": req.venue_id,
        "issued_by_id": customer_id,
        "issued_by_name": customer.get("name", "Khách hàng"),
        "created_at": now,
        "updated_at": now
    })
    
    # 2. Tạo Identity (Lưu hash SĐT/CCCD để đối soát tại cổng)
    from .tickets import _hash_id, _hash_phone
    identity_doc = {
        "_id": str(uuid.uuid4()),
        "ticket_id": ticket_id,
        "booking_id": booking_id,
        "face_embedding": None,
        "face_image_hash": None,
        "has_face": False,
        "created_at": now
    }
    try:
        identity_doc["id_hash"] = _hash_id(customer["cccd"])
        identity_doc["phone_hash"] = _hash_phone(customer["phone"])
    except: pass
    
    await db["identities"].insert_one(identity_doc)
    
    # 3. Tạo Transaction
    await db["transactions"].insert_one({
        "_id": str(uuid.uuid4()),
        "ticket_id": ticket_id,
        "action": "ISSUE",
        "actor_id": customer_id,
        "actor_role": "customer",
        "amount": price,
        "payment_method": req.payment_method,
        "timestamp": now
    })
    
    # 4. Tạo QR
    token = _make_qr_token(ticket_id, req.ticket_type, valid_until, req.venue_id)
    qr_b64 = generate_qr_b64(token) if token else None

    return TicketResponse(
        ticket_id=ticket_id,
        booking_id=booking_id,
        ticket_type=req.ticket_type,
        price=price,
        valid_from=valid_from,
        valid_until=valid_until,
        status="active",
        has_face=False,
        qr_image_b64=qr_b64,
        created_at=now
    )

@router.post("/tickets/{ticket_id}/cancel")
async def cancel_my_ticket(
    ticket_id: str,
    request: Request,
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Khách hàng tự hủy vé cũ (trước ngày đi). Hoàn 50% tiền."""
    ticket = await db["tickets"].find_one({"_id": ticket_id, "customer_id": str(customer["_id"])})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại hoặc không thuộc về bạn.")
    
    if ticket.get("status") != "active":
        raise HTTPException(400, f"Vé đang ở trạng thái '{ticket.get('status')}' không thể hủy.")
    
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    
    # Đảm bảo valid_until có timezone để so sánh chính xác
    valid_until = ticket.get("valid_until")
    if not valid_until:
        raise HTTPException(500, "Dữ liệu vé không hợp lệ (thiếu thời hạn).")
        
    # Motor returns aware datetime usually, but we ensure it's comparable
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)
        
    if valid_until < now:
        raise HTTPException(400, "Vé đã hết hạn, không thể hủy.")
        
    # Cập nhật status => revoked
    await db["tickets"].update_one(
        {"_id": ticket_id},
        {"$set": {
            "status": "revoked",
            "updated_at": now
        }}
    )
    
    refund_amount = ticket.get("price", 0) * 0.5
    
    # 1. Ghi nhận giao dịch tài chính
    await db["transactions"].insert_one({
        "_id": str(uuid.uuid4()),
        "ticket_id": ticket_id,
        "action": "CANCEL_REFUND",
        "actor_id": str(customer["_id"]),
        "actor_role": "customer",
        "amount": -refund_amount,
        "payment_method": "system_refund",
        "timestamp": now
    })

    # 2. Ghi Audit Log để Dashboard Admin theo dõi được
    await log_action(
        db, 
        user_id=str(customer["_id"]), 
        action=ACTION_REVOKE_TICKET,
        resource=ticket_id,
        detail={
            "reason": "Customer cancelled online",
            "refund_amount": refund_amount,
            "original_price": ticket.get("price")
        },
        ip=request.client.host if request.client else None
    )
    
    return {"message": "Hủy vé thành công. Bạn sẽ nhận lại 50% số tiền theo chính sách."}

# ── Quản lý khách hàng (Admin/Manager) ────────────────────────

@router.get("/all", response_model=list[CustomerResponse])
async def list_all_customers(
    current_user: dict = Depends(require_min_role(Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lấy danh sách toàn bộ khách hàng (Admin/Manager)."""
    cursor = db["customers"].find({}).sort("created_at", -1)
    customers = await cursor.to_list(length=1000)
    return [
        CustomerResponse(
            id=str(c["_id"]),
            name=c.get("name") or "",
            email=c.get("email") or ""
        ) for c in customers
    ]

@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer_by_admin(
    customer_id: str,
    req: CustomerUpdateByAdminRequest,
    current_user: dict = Depends(require_min_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Admin chỉnh sửa thông tin khách hàng."""
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "Không có dữ liệu cập nhật.")
        
    result = await db["customers"].update_one(
        {"_id": customer_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Không tìm thấy khách hàng.")
        
    customer = await db["customers"].find_one({"_id": customer_id})
    return CustomerResponse(
        id=str(customer["_id"]),
        name=customer.get("name") or "",
        email=customer.get("email") or ""
    )

@router.delete("/{customer_id}")
async def delete_customer_by_admin(
    customer_id: str,
    current_user: dict = Depends(require_min_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Admin xóa tài khoản khách hàng."""
    # Xóa customer
    result = await db["customers"].delete_one({"_id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Không tìm thấy khách hàng.")
        
    # Tùy chọn: Xóa các vé liên quan (hoặc để lại làm lịch sử)
    # await db["tickets"].delete_many({"customer_id": customer_id})
    
    return {"message": "Đã xóa tài khoản khách hàng thành công."}
 