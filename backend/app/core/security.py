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

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings
from .database import get_db

logger = logging.getLogger(__name__)


# Roles

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


# Password hashing (bcrypt)

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# JWT Logic

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


# Current actor dependency

async def get_current_actor(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> dict:
    """
    Dependency chung để xác định Actor (có thể là User hoặc Customer).
    Tự động gán user_id và role vào request.state để AuditMiddleware sử dụng.
    """
    payload = decode_token(token)
    actor_id = payload.get("sub")
    role     = payload.get("role")

    if not actor_id:
        raise HTTPException(401, "Token thiếu thông tin định danh.")

    actor = None
    if role == Role.CUSTOMER.value:
        actor = await db["customers"].find_one({"_id": actor_id})
        if actor:
            actor["role"] = Role.CUSTOMER.value
    else:
        actor = await db["users"].find_one({"_id": actor_id, "is_active": True})

    if not actor:
        raise HTTPException(401, "Danh tính không hợp lệ hoặc đã bị vô hiệu.")

    # Gán vào state cho middleware log
    request.state.user_id = actor_id
    request.state.role    = actor.get("role")
    
    return actor


async def get_current_user(
    request: Request,
    actor: dict = Depends(get_current_actor),
) -> dict:
    """
    Wrapper của get_current_actor: chỉ cho phép các role User (không phải Customer).
    """
    if actor.get("role") == Role.CUSTOMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản nhân viên được yêu cầu, không phải khách hàng.",
        )
    return actor


async def get_current_customer(
    request: Request,
    actor: dict = Depends(get_current_actor),
) -> dict:
    """
    Wrapper của get_current_actor: chỉ cho phép role Customer.
    """
    if actor.get("role") != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản khách hàng được yêu cầu.",
        )
    return actor



# RBAC factories

def require_role(*roles: Role):
    """
    Dependency: chỉ cho phép đúng các role được liệt kê.
    Chấp nhận cả User và Customer.
    """
    async def _check(actor: dict = Depends(get_current_actor)) -> dict:
        user_role = actor.get("role", "")
        allowed   = [r.value for r in roles]
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần quyền: {allowed}. Bạn có: '{user_role}'.",
            )
        return actor
    return _check


def require_min_role(min_role: Role):
    """
    Dependency: cho phép role >= min_role theo ROLE_HIERARCHY.
    Chấp nhận cả User và Customer.
    """
    async def _check(actor: dict = Depends(get_current_actor)) -> dict:
        user_role  = actor.get("role", "")
        try:
            # Nếu role rác hoặc không có trong enum, cho là 0 (customer)
            r_obj = Role(user_role)
            user_level = ROLE_HIERARCHY.get(r_obj, 0)
        except ValueError:
            user_level = 0
            
        min_level = ROLE_HIERARCHY[min_role]
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cần quyền tối thiểu: '{min_role.value}'. Bạn có: '{user_role}'.",
            )
        return actor
    return _check
 