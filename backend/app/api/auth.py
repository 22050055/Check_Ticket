"""api/auth.py — Authentication & User management endpoints"""
import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    get_current_user, require_role, Role,
)
from ..schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserCreate, UserResponse
from ..middleware.audit import log_action, ACTION_LOGIN, ACTION_CREATE_USER

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Đăng nhập — trả về access_token + refresh_token."""
    user = await db["users"].find_one({"username": req.username, "is_active": True})
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Sai username hoặc password.")

    user_id = str(user["_id"])
    # Truyền gate_id vào token để Gate App biết cổng của operator
    access  = create_access_token(user_id, user["role"], gate_id=user.get("gate_id"))
    refresh = create_refresh_token(user_id)

    await log_action(db, user_id, ACTION_LOGIN,
                     ip=request.client.host if request.client else None)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        role=user["role"],
        full_name=user["full_name"],
        gate_id=user.get("gate_id"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Làm mới access_token bằng refresh_token."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token không phải refresh token.")

    user = await db["users"].find_one({"_id": payload["sub"], "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại.")

    user_id = str(user["_id"])
    access  = create_access_token(user_id, user["role"], gate_id=user.get("gate_id"))
    refresh = create_refresh_token(user_id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        role=user["role"],
        full_name=user["full_name"],
        gate_id=user.get("gate_id"),
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    req: UserCreate,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Tạo tài khoản nhân viên — chỉ Admin."""
    if await db["users"].find_one({"username": req.username}):
        raise HTTPException(status_code=400, detail="Username đã tồn tại.")

    user_id  = str(uuid.uuid4())
    user_doc = {
        "_id":           user_id,
        "username":      req.username,
        "password_hash": hash_password(req.password),
        "full_name":     req.full_name,
        "role":          req.role,
        "gate_id":       req.gate_id,
        "is_active":     True,
        "created_at":    datetime.now(timezone.utc),
    }
    await db["users"].insert_one(user_doc)
    await log_action(db, str(current_user["_id"]), ACTION_CREATE_USER, resource=user_id)

    return UserResponse(
        id=user_id, username=req.username, full_name=req.full_name,
        role=req.role, gate_id=req.gate_id, is_active=True,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Lấy thông tin tài khoản hiện tại."""
    return UserResponse(
        id=str(current_user["_id"]),
        username=current_user["username"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        gate_id=current_user.get("gate_id"),
        is_active=current_user["is_active"],
    )


@router.get("/users", response_model=dict)
async def list_users(
    current_user: dict = Depends(require_role(Role.ADMIN, Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Danh sách tất cả tài khoản — Admin và Manager.
    Không trả về password_hash.
    """
    users_raw = await db["users"].find(
        {},
        {"password_hash": 0},   # ẩn password
    ).sort("created_at", 1).to_list(200)

    users = [
        UserResponse(
            id=str(u["_id"]),
            username=u["username"],
            full_name=u["full_name"],
            role=u["role"],
            gate_id=u.get("gate_id"),
            is_active=u.get("is_active", True),
        )
        for u in users_raw
    ]
    return {"total": len(users), "users": users}


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN, Role.MANAGER)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Chi tiết 1 tài khoản theo ID."""
    user = await db["users"].find_one({"_id": user_id}, {"password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")
    return UserResponse(
        id=str(user["_id"]),
        username=user["username"],
        full_name=user["full_name"],
        role=user["role"],
        gate_id=user.get("gate_id"),
        is_active=user.get("is_active", True),
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    req: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """
    Cập nhật tài khoản — chỉ Admin.
    Hỗ trợ: is_active (kích hoạt / vô hiệu), gate_id, role.
    Không cho phép đổi password qua endpoint này.
    """
    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")

    # Không cho vô hiệu chính mình
    if str(current_user["_id"]) == user_id and req.get("is_active") is False:
        raise HTTPException(status_code=400, detail="Không thể vô hiệu hóa tài khoản đang dùng.")

    # Chỉ cho phép sửa các trường an toàn
    allowed_fields = {"is_active", "gate_id", "role", "full_name"}
    update_data = {k: v for k, v in req.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=400, detail="Không có trường hợp lệ để cập nhật.")

    update_data["updated_at"] = datetime.now(timezone.utc)
    await db["users"].update_one({"_id": user_id}, {"$set": update_data})

    await log_action(
        db, str(current_user["_id"]), "UPDATE_USER",
        resource=user_id, detail=update_data,
    )

    updated = await db["users"].find_one({"_id": user_id}, {"password_hash": 0})
    return UserResponse(
        id=str(updated["_id"]),
        username=updated["username"],
        full_name=updated["full_name"],
        role=updated["role"],
        gate_id=updated.get("gate_id"),
        is_active=updated.get("is_active", True),
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Xóa tài khoản — chỉ Admin. Không cho xóa chính mình."""
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản đang đăng nhập.")

    user = await db["users"].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại.")

    if user.get("username") == "admin":
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản admin gốc.")

    await db["users"].delete_one({"_id": user_id})
    await log_action(db, str(current_user["_id"]), "DELETE_USER", resource=user_id,
                     detail={"username": user.get("username")})

    return {"message": f"Đã xóa tài khoản '{user.get('username')}'.", "user_id": user_id}
 