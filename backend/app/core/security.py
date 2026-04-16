"""
core/security.py — JWT tạo/xác thực + password hashing + RBAC

Roles:
    admin    — toàn quyền hệ thống
    manager  — xem báo cáo, quản lý vé, tạo nhân viên
    operator — nhân viên cổng: check-in/out, phát vé
    cashier  — bán vé, xem doanh thu
"""
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)


# ── Roles ─────────────────────────────────────────────────────

class Role(str, Enum):
    ADMIN    = "admin"
    MANAGER  = "manager"
    OPERATOR = "operator"
    CASHIER  = "cashier"
    CUSTOMER = "customer"

# Hierarchy: số càng cao quyền càng cao
ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN:    4,
    Role.MANAGER:  3,
    Role.CASHIER:  2,
    Role.OPERATOR: 1,
    Role.CUSTOMER: 0,
}


# ── Password (bcrypt) ─────────────────────────────────────────

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(user_id: str, role: str, gate_id: str | None = None) -> str:
    """
    Tạo access token JWT (HS256).
    Payload gồm: sub (user_id), role, gate_id, type, exp.
    gate_id: cổng được gán cho operator — Gate App dùng để tự điền gate_id.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub":     user_id,
        "role":    role,
        "gate_id": gate_id,   # None nếu không phải operator
        "type":    "access",
        "exp":     expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Tạo refresh token JWT — chỉ chứa sub và exp."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub":  user_id,
        "type": "refresh",
        "exp":  expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode và verify JWT.
    Raise HTTP 401 nếu token không hợp lệ hoặc hết hạn.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token không hợp lệ: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current user dependency ───────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> dict:
    """
    FastAPI dependency: verify JWT → lấy user từ MongoDB.
    Raise 401 nếu token sai hoặc user không tồn tại/bị vô hiệu.

    Dùng:
        @router.get("/me")
        async def me(user = Depends(get_current_user)):
            return user
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cần access token, không phải refresh token.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token thiếu thông tin user.",
        )

    user = await db["users"].find_one({"_id": user_id, "is_active": True})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đã bị vô hiệu hóa.",
        )

    return user

async def get_current_customer(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> dict:
    """
    FastAPI dependency: verify JWT → lấy customer từ MongoDB thay vì users.
    Raise 401 nếu token sai hoặc customer không tồn tại.
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cần access token, không phải refresh token.",
        )

    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token thiếu thông tin khách hàng.",
        )

    customer = await db["customers"].find_one({"_id": customer_id})
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Khách hàng không tồn tại.",
        )

    # Đảm bảo gán thêm role customer vào object trả ra vì document có thể không lưu role
    customer["role"] = Role.CUSTOMER.value
    return customer


# ── RBAC dependency factories ─────────────────────────────────

def require_role(*roles: Role):
    """
    Dependency: chỉ cho phép đúng các role được liệt kê.

    Dùng:
        @router.delete("/", dependencies=[Depends(require_role(Role.ADMIN))])

    hoặc:
        @router.get("/", dependencies=[Depends(require_role(Role.ADMIN, Role.MANAGER))])
    """
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "")
        allowed   = [r.value for r in roles]
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần quyền: {allowed}. Bạn có: '{user_role}'.",
            )
        return current_user
    return _check


def require_min_role(min_role: Role):
    """
    Dependency: cho phép role >= min_role theo ROLE_HIERARCHY.
    Ví dụ require_min_role(Role.OPERATOR) → OPERATOR, CASHIER, MANAGER, ADMIN đều qua.

    Dùng:
        @router.post("/checkin", dependencies=[Depends(require_min_role(Role.OPERATOR))])
    """
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        user_role  = current_user.get("role", "")
        try:
            user_level = ROLE_HIERARCHY[Role(user_role)]
        except ValueError:
            user_level = 0
        min_level = ROLE_HIERARCHY[min_role]
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần quyền tối thiểu: '{min_role.value}'. Bạn có: '{user_role}'.",
            )
        return current_user
    return _check
