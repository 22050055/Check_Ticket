import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import get_current_customer, require_min_role, Role
from ..schemas.review import ReviewCreateRequest, ReviewResponse, ReviewStats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Reviews"])

@router.post("/customer/tickets/{ticket_id}/review", response_model=ReviewResponse)
async def submit_review(
    ticket_id: str,
    req: ReviewCreateRequest,
    customer: dict = Depends(get_current_customer),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Khách hàng đánh giá mức độ hài lòng cho một vé đã sử dụng."""
    # 1. Kiểm tra vé tồn tại và thuộc về khách hàng này
    ticket = await db["tickets"].find_one({"_id": ticket_id, "customer_id": str(customer["_id"])})
    if not ticket:
        raise HTTPException(404, "Vé không tồn tại hoặc không thuộc quyền sở hữu của bạn.")
    
    # 2. Kiểm tra trạng thái vé (cho phép đánh giá khi đang hoạt động, đã vào cổng hoặc hết hạn)
    ticket_status = ticket.get("status", "").lower()
    if ticket_status not in ["active", "used", "inside", "outside", "expired"]:
        raise HTTPException(400, "Bạn chỉ có thể đánh giá sau khi mua vé, sử dụng vé hoặc vé đã hết hạn.")

    # 3. Kiểm tra xem đã đánh giá chưa
    existing = await db["reviews"].find_one({"ticket_id": ticket_id})
    if existing:
        raise HTTPException(400, "Vé này đã được đánh giá trước đó.")

    # 4. Lưu đánh giá
    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    review_doc = {
        "_id": review_id,
        "ticket_id": ticket_id,
        "customer_id": str(customer["_id"]),
        "customer_name": customer.get("name", "Khách hàng"),
        "rating": req.rating,
        "comment": req.comment,
        "created_at": now
    }
    
    await db["reviews"].insert_one(review_doc)
    
    # Broadcast (Real-time update for Web Dashboard)
    # Note: socket broadcasting will be implemented in main.py logic or shared manager
    
    return ReviewResponse(
        id=review_id,
        ticket_id=ticket_id,
        customer_name=review_doc["customer_name"],
        rating=req.rating,
        comment=req.comment,
        created_at=now
    )

@router.get("/reports/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    current_user: dict = Depends(require_min_role(Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lấy danh sách đánh giá của khách hàng (Dành cho Admin/Manager)."""
    cursor = db["reviews"].find({}).sort("created_at", -1).limit(100)
    reviews = await cursor.to_list(length=100)
    
    return [
        ReviewResponse(
            id=str(r["_id"]),
            ticket_id=r["ticket_id"],
            customer_name=r["customer_name"],
            rating=r["rating"],
            comment=r.get("comment"),
            created_at=r["created_at"]
        ) for r in reviews
    ]

@router.get("/reports/review-stats", response_model=ReviewStats)
async def get_review_stats(
    current_user: dict = Depends(require_min_role(Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Thống kê đánh giá của khách hàng."""
    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_rating": {"$avg": "$rating"},
                "total": {"$sum": 1},
                "r1": {"$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}},
                "r2": {"$sum": {"$cond": [{"$eq": ["$rating", 2]}, 1, 0]}},
                "r3": {"$sum": {"$cond": [{"$eq": ["$rating", 3]}, 1, 0]}},
                "r4": {"$sum": {"$cond": [{"$eq": ["$rating", 4]}, 1, 0]}},
                "r5": {"$sum": {"$cond": [{"$eq": ["$rating", 5]}, 1, 0]}}
            }
        }
    ]
    
    results = await db["reviews"].aggregate(pipeline).to_list(length=1)
    
    if not results:
        return ReviewStats(
            average_rating=0.0,
            total_reviews=0,
            rating_distribution={1:0, 2:0, 3:0, 4:0, 5:0}
        )
        
    res = results[0]
    return ReviewStats(
        average_rating=round(res["avg_rating"], 1),
        total_reviews=res["total"],
        rating_distribution={
            1: res["r1"], 2: res["r2"], 3: res["r3"], 4: res["r4"], 5: res["r5"]
        }
    )
