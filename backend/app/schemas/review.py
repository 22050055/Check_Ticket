from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReviewCreateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: str
    ticket_id: str
    customer_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime

class ReviewStats(BaseModel):
    average_rating: float
    total_reviews: int
    rating_distribution: dict[int, int]
