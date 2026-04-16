"""
time_window.py — Kiểm tra QR còn trong time-window hợp lệ
Thêm lớp bảo vệ ngoài expiry chuẩn của JWT
"""
import os
from datetime import datetime, timezone

# Số phút cho phép QR được quét sau khi issue
# Dùng cho QR "1 lần dùng tại cổng" (khác với vé có hiệu lực cả ngày)
ENTRY_WINDOW_MINUTES: int = int(os.getenv("QR_ENTRY_WINDOW_MINUTES", "0"))
# 0 = tắt time-window (dùng exp của JWT), > 0 = giới hạn thêm


class TimeWindowError(Exception):
    """QR nằm ngoài khung giờ cho phép."""
    pass


def is_within_time_window(payload: dict) -> bool:
    """
    Kiểm tra QR có còn trong time-window hợp lệ không.

    Logic:
    - Nếu ENTRY_WINDOW_MINUTES = 0: bỏ qua, chỉ dùng exp của JWT.
    - Nếu ENTRY_WINDOW_MINUTES > 0: kiểm tra QR quét trong vòng N phút sau khi issue.

    Args:
        payload: dict đã decode từ JWT.

    Returns:
        True nếu hợp lệ.

    Raises:
        TimeWindowError nếu ngoài window.
    """
    if ENTRY_WINDOW_MINUTES <= 0:
        return True

    iat = payload.get("iat")
    if iat is None:
        raise TimeWindowError("QR thiếu trường iat (issued at).")

    issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    elapsed_minutes = (now - issued_at).total_seconds() / 60

    if elapsed_minutes > ENTRY_WINDOW_MINUTES:
        raise TimeWindowError(
            f"QR hết hiệu lực tại cổng. "
            f"Vé đã phát {elapsed_minutes:.1f} phút trước "
            f"(giới hạn {ENTRY_WINDOW_MINUTES} phút)."
        )

    return True


def get_remaining_seconds(payload: dict) -> int:
    """
    Trả về số giây còn lại trước khi QR hết hạn (theo exp).
    Dùng để hiển thị countdown trên app.
    """
    exp = payload.get("exp")
    if exp is None:
        return 0
    remaining = exp - datetime.now(timezone.utc).timestamp()
    return max(0, int(remaining))
