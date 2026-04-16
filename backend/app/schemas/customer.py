from pydantic import BaseModel, EmailStr
from typing import Optional

class CustomerRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str

class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CustomerBuyTicketRequest(BaseModel):
    """Khách hàng tự mua vé online (không cần nhân viên)."""
    ticket_type: str               # adult | child | student | group
    payment_method: str = "demo"   # demo = giả lập thanh toán cho đồ án
    venue_id: str = "tourism_default"
