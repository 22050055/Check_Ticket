"""
schemas/auth.py — Request/Response cho Authentication & User management
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── Login / Token ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Trả về sau login / refresh."""
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    role:          str
    full_name:     str
    gate_id:       Optional[str] = None   # Gate App dùng để tự điền gate_id


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User management (chỉ Admin) ───────────────────────────────

class UserCreate(BaseModel):
    """Tạo tài khoản nhân viên mới."""
    username:  str = Field(..., min_length=3, max_length=50)
    password:  str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1)
    role:      str = Field(..., pattern="^(admin|manager|operator|cashier)$")
    phone:     Optional[str] = None
    cccd:      Optional[str] = None
    gate_id:   Optional[str] = None   # Gán cổng mặc định cho operator

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Username chỉ chứa chữ, số, dấu gạch dưới."""
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username chỉ được chứa chữ cái, số và dấu gạch dưới.")
        return v.lower()


class UserResponse(BaseModel):
    """Thông tin tài khoản trả về (không có password)."""
    id:        str
    username:  str
    full_name: str
    role:      str
    phone:     Optional[str] = None
    cccd:      Optional[str] = None
    gate_id:   Optional[str] = None
    is_active: bool
    is_online: Optional[bool] = False  # Trạng thái real-time


class UserListResponse(BaseModel):
    """Danh sách tài khoản (dùng cho trang quản lý nhân sự)."""
    total: int
    users: list[UserResponse]
 