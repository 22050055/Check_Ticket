import qrcode
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

def generate_qr_png_bytes(token: str) -> bytes:
    """Tạo đối tượng byte của ảnh QR PNG từ JWT token."""
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )
        qr.add_data(token)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Lỗi khi sinh ảnh QR PNG: {e}")
        raise ValueError("Không thể tạo nội dung QR.")

def generate_qr_b64(token: str) -> str:
    """Tạo ảnh QR b64 (để chèn HTML) từ JWT token."""
    png_bytes = generate_qr_png_bytes(token)
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()
 