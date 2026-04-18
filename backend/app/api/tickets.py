"""api/tickets.py — Quản lý vé điện tử"""
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.config import settings
from ..core.database import get_db
from ..core.security import get_current_user, require_role, require_min_role, Role
from fastapi.responses import StreamingResponse
from ..schemas.ticket import TicketIssueRequest, TicketEnrollFaceRequest, TicketResponse, TicketRevokeRequest
from ..middleware.audit import log_action, ACTION_ISSUE_TICKET, ACTION_REVOKE_TICKET
from ..services.qr_image_service import generate_qr_b64, generate_qr_png_bytes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tickets", tags=["Tickets"])


# ── QR: load public key trực tiếp (không qua sys.path) ───────

def _load_qr_keys() -> tuple[Optional[str], Optional[str]]:
    """Load RSA private/public key từ config (ưu tiên string trong ENV, sau đó đến file)."""
    # 1. Thử lấy trực tiếp từ string (cho Render)
    raw_private = settings.QR_PRIVATE_KEY
    raw_public  = settings.QR_PUBLIC_KEY

    import base64
    import re

    def _safe_decode(val: Optional[str]) -> Optional[str]:
        if not val: return None
        # Nếu chuỗi có vẻ là Base64 của cả file (thường bắt đầu bằng LS0tLS1 cho -----), ta decode nó trước.
        if val.startswith("LS0tLS1"):
            try:
                # Thử decode base64
                decoded = base64.b64decode(val).decode("utf-8")
                if "-----BEGIN" in decoded:
                    return decoded
            except Exception:
                pass
        return val

    private = _safe_decode(raw_private)
    public  = _safe_decode(raw_public)

    def _sanitize(key_str: Optional[str], key_type: str = "PRIVATE") -> Optional[str]:
        if not key_str:
            return None
            
        import re
        # Làm sạch tuyệt đối: lấy phần Base64 bên trong
        s = key_str.strip()
        
        # Nếu đã có header/footer chuẩn thì bóc tách
        pattern = rf"-----BEGIN {key_type} KEY-----([\s\S]*?)-----END {key_type} KEY-----"
        match = re.search(pattern, s)
        
        if match:
            blob = match.group(1)
        else:
            # Nếu không thấy header, coi như cả chuỗi là blob (đã xóa dấu -)
            blob = s.replace("-", "")
            
        # Xóa mọi khoảng trắng/xuống dòng/tab
        clean_blob = re.sub(r"[\s\r\n\t]", "", blob)
        
        # Xây dựng lại PEM chuẩn 64 chars mỗi dòng
        lines = [clean_blob[i:i+64] for i in range(0, len(clean_blob), 64)]
        reconstructed = f"-----BEGIN {key_type} KEY-----\n" + "\n".join(lines) + f"\n-----END {key_type} KEY-----"
        return reconstructed

    private = _sanitize(private, "PRIVATE")
    public  = _sanitize(public, "PUBLIC")

    # 2. Nếu không có ở ENV, thử đọc từ file
    if not private:
        priv_path = Path(settings.QR_PRIVATE_KEY_PATH)
        if priv_path.exists():
            private = priv_path.read_text().strip()
            
    if not public:
        pub_path  = Path(settings.QR_PUBLIC_KEY_PATH)
        if pub_path.exists():
            public = pub_path.read_text().strip()

    if not private:
        logger.warning("QR private key không tìm thấy trong cả ENV và file path.")
        
    return private, public


_PRIVATE_KEY, _PUBLIC_KEY = _load_qr_keys()


def _make_qr_token(ticket_id: str, ticket_type: str, valid_until: datetime, venue_id: str) -> Optional[str]:
    """Tạo JWT RS256 cho QR. Trả None nếu chưa có key hoặc key lỗi."""
    if not _PRIVATE_KEY:
        logger.warning("Không thể tạo QR token vì thiếu _PRIVATE_KEY.")
        return None
        
    try:
        from jose import jwt as jose_jwt
        now = datetime.now(timezone.utc)
        payload = {
            "jti": str(uuid.uuid4()),
            "sub": ticket_id,
            "tid": ticket_type,
            "vid": venue_id,
            "iat": int(now.timestamp()),
            "exp": int(valid_until.timestamp()),
        }
        # Thống kê độ dài key để debug (không log nội dung key)
        key_len = len(_PRIVATE_KEY)
        logger.info("Đang ký QR JWT với key dài %s ký tự", key_len)
        
        return jose_jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")
    except Exception as e:
        logger.exception("Tạo QR JWT thất bại")
        return None



# ── ID Hash: inline HMAC (không qua sys.path) ─────────────────

def _hash_id(id_number: str) -> str:
    cleaned = id_number.strip().upper().replace(" ", "").replace("-", "")
    return hmac.new(settings.ID_HASH_PEPPER.encode(), cleaned.encode(), hashlib.sha256).hexdigest()

def _hash_phone(phone: str) -> str:
    import re
    cleaned = re.sub(r'[^0-9]', '', phone)
    return hmac.new(settings.ID_HASH_PEPPER.encode(), cleaned.encode(), hashlib.sha256).hexdigest()


# ── POST /api/tickets — Phát hành vé ─────────────────────────

@router.post("", response_model=TicketResponse, status_code=201)
async def issue_ticket(
    req: TicketIssueRequest,
    current_user: dict = Depends(require_min_role(Role.CASHIER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Phát hành vé mới:
    1. Tạo/lấy customer
    2. Lưu ticket
    3. Lưu identity (hash CCCD/SĐT nếu có)
    4. Lưu transaction
    5. Tạo QR JWT + ảnh QR
    """
    ticket_id = str(uuid.uuid4())
    now       = datetime.now(timezone.utc)

    # 1. Customer
    customer_id = None
    if req.customer_phone or req.customer_email:
        query = {}
        if req.customer_phone:
            query["phone"] = req.customer_phone
        elif req.customer_email:
            query["email"] = req.customer_email
        customer = await db["customers"].find_one(query)
        if not customer:
            customer_id = str(uuid.uuid4())
            await db["customers"].insert_one({
                "_id":        customer_id,
                "name":       req.customer_name,
                "phone":      req.customer_phone,
                "email":      req.customer_email,
                "created_at": now,
            })
        else:
            customer_id = str(customer["_id"])

    # 2. Ticket
    await db["tickets"].insert_one({
        "_id":         ticket_id,
        "booking_id":  req.booking_id,
        "customer_id": customer_id,
        "ticket_type": req.ticket_type,
        "price":       req.price,
        "valid_from":  req.valid_from,
        "valid_until": req.valid_until,
        "status":      "active",
        "venue_id":    req.venue_id,
        "issued_by_id":   str(current_user["_id"]),
        "issued_by_name": current_user.get("full_name", "Nhân viên"),
        "created_at":  now,
        "updated_at":  now,
    })

    # 3. Identity — hash CCCD/SĐT nếu được cung cấp
    identity_doc: dict = {
        "_id":             str(uuid.uuid4()),
        "ticket_id":       ticket_id,
        "booking_id":      req.booking_id,
        "face_embedding":  None,
        "face_image_hash": None,
        "has_face":        False,
        "created_at":      now,
    }
    if req.id_number:
        try:
            identity_doc["id_hash"] = _hash_id(req.id_number)
        except Exception:
            pass
    if req.phone_for_hash:
        try:
            identity_doc["phone_hash"] = _hash_phone(req.phone_for_hash)
        except Exception:
            pass
    await db["identities"].insert_one(identity_doc)

    # 4. Transaction
    await db["transactions"].insert_one({
        "_id":            str(uuid.uuid4()),
        "ticket_id":      ticket_id,
        "ticket_type":    req.ticket_type,
        "amount":         req.price,
        "payment_method": req.payment_method,
        "created_at":     now,
    })

    # 5. QR
    qr_image_b64 = None
    token = _make_qr_token(ticket_id, req.ticket_type, req.valid_until, req.venue_id)
    if token:
        qr_image_b64 = generate_qr_b64(token)

    await log_action(db, str(current_user["_id"]), ACTION_ISSUE_TICKET, resource=ticket_id,
                     detail={"type": req.ticket_type, "price": req.price})

    return TicketResponse(
        ticket_id=ticket_id, booking_id=req.booking_id,
        ticket_type=req.ticket_type, price=req.price,
        valid_from=req.valid_from, valid_until=req.valid_until,
        status="active", has_face=False, qr_image_b64=qr_image_b64,
        created_at=now,
    )


# ── POST /api/tickets/{id}/enroll-face — Đăng ký khuôn mặt ──

@router.post("/{ticket_id}/enroll-face")
async def enroll_face(
    ticket_id: str,
    req: TicketEnrollFaceRequest,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Đăng ký khuôn mặt opt-in cho vé.
    Gọi AI Services /enroll → nhận embedding 512-d → lưu vào identities.
    KHÔNG lưu ảnh gốc (privacy guard).
    """
    ticket = await db["tickets"].find_one({"_id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại.")
    if ticket.get("status") != "active":
        raise HTTPException(400, "Vé không còn active.")

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
        "message":       "Đăng ký khuôn mặt thành công. Ảnh gốc không được lưu.",
        "ticket_id":     ticket_id,
        "embedding_dim": len(data.get("embedding", [])),
    }


# ── GET /api/tickets/search — Tra cứu vé ──────────────────────

@router.get("/search", response_model=list[TicketResponse])
async def search_tickets(
    q: Optional[str] = Query(None, description="Tìm theo Ticket ID hoặc Booking ID"),
    ticket_type: Optional[str] = Query(None, description="Lọc theo loại vé"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    current_user: dict = Depends(require_min_role(Role.CASHIER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Tra cứu danh sách vé với các điều kiện lọc nâng cao.
    """
    filter_query = {}
    
    if q:
        # Tìm kiếm theo ID hoặc Booking ID (hoặc SĐT khách hàng if we link it)
        q_clean = q.strip()
        filter_query["$or"] = [
            {"_id": q_clean},
            {"booking_id": {"$regex": q_clean, "$options": "i"}}
        ]
        
    if ticket_type:
        filter_query["ticket_type"] = ticket_type
        
    if status:
        filter_query["status"] = status
        
    cursor = db["tickets"].find(filter_query).sort("created_at", -1).limit(100)
    tickets = await cursor.to_list(length=100)
    
    results = []
    for t in tickets:
        identity = await db["identities"].find_one({"ticket_id": str(t["_id"])})
        results.append(TicketResponse(
            ticket_id=str(t["_id"]),
            booking_id=t.get("booking_id"),
            ticket_type=t["ticket_type"],
            price=t["price"],
            valid_from=t["valid_from"],
            valid_until=t["valid_until"],
            status=t["status"],
            has_face=identity.get("has_face", False) if identity else False,
            issued_by_name=t.get("issued_by_name"),
            created_at=t["created_at"],
        ))
    return results


# ── GET /api/tickets/{id} ────────────────────────────────────

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ticket   = await db["tickets"].find_one({"_id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại.")
    identity = await db["identities"].find_one({"ticket_id": ticket_id})
    return TicketResponse(
        ticket_id=ticket_id,
        booking_id=ticket.get("booking_id"),
        ticket_type=ticket["ticket_type"],
        price=ticket["price"],
        valid_from=ticket["valid_from"],
        valid_until=ticket["valid_until"],
        status=ticket["status"],
        has_face=identity.get("has_face", False) if identity else False,
        created_at=ticket["created_at"],
    )


# ── GET /api/tickets/{id}/qr.png ─────────────────────────────

@router.get("/{ticket_id}/qr.png")
async def download_qr(
    ticket_id: str,
    current_user: dict = Depends(require_min_role(Role.OPERATOR)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Cho phép nhân viên hoặc admin tải xuống ảnh QR trực tiếp từ Ticket ID.
    Trả về định dạng tệp PNG (Content-Disposition: attachment).
    """
    ticket = await db["tickets"].find_one({"_id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại.")
        
    token = _make_qr_token(ticket_id, ticket["ticket_type"], ticket["valid_until"], ticket.get("venue_id", ""))
    if not token:
        raise HTTPException(500, "Không thể sinh chữ ký QR. Có thể thiếu private key.")
        
    try:
        qr_bytes = generate_qr_png_bytes(token)
    except Exception as e:
        raise HTTPException(500, f"Lỗi tạo nội dung QR: {e}")
        
    from io import BytesIO
    return StreamingResponse(
        BytesIO(qr_bytes), 
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="ticket-{ticket_id}.png"'}
    )


# ── PUT /api/tickets/{id}/revoke ──────────────────────────────

@router.put("/{ticket_id}/revoke")
async def revoke_ticket(
    ticket_id: str,
    req: TicketRevokeRequest,
    current_user: dict = Depends(require_role(Role.ADMIN, Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    ticket = await db["tickets"].find_one({"_id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại.")
    if ticket.get("status") == "revoked":
        raise HTTPException(400, "Vé đã bị revoke trước đó.")

    await db["tickets"].update_one(
        {"_id": ticket_id},
        {"$set": {"status": "revoked", "updated_at": datetime.now(timezone.utc)}},
    )
    await log_action(db, str(current_user["_id"]), ACTION_REVOKE_TICKET,
                     resource=ticket_id, detail={"reason": req.reason})

    return {"message": "Vé đã bị thu hồi.", "ticket_id": ticket_id}
 