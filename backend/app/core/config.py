"""
core/config.py — Cấu hình toàn bộ Backend API
Đọc từ biến môi trường hoặc file .env

Cách dùng:
    from app.core.config import settings
    print(settings.MONGO_URI)
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str    = "Tourism Gate Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool      = False

    # ── MongoDB Atlas ─────────────────────────────────────────
    # Password lưu riêng để không hardcode vào URI
    MONGO_PASSWORD: str = "CHANGE_ME"
    MONGO_DB: str       = "tourism_db"

    # URI đầy đủ — tự động build bên dưới qua property
    # Nếu muốn override toàn bộ URI, set MONGO_URI trong .env
    MONGO_URI: str = (
        "mongodb+srv://22050055_db_user:{password}"
        "@khang1402.e2kn7mt.mongodb.net"
        "/?appName=khang1402"
        "&retryWrites=true&w=majority"
    )

    # ── JWT (HS256) ───────────────────────────────────────────
    JWT_SECRET: str                  = "CHANGE_THIS_TO_RANDOM_32_BYTES_IN_PRODUCTION"
    JWT_ALGORITHM: str               = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int   = 7

    # ── AI Services — face_service (port 8001) ────────────────
    AI_SERVICE_URL: str    = "http://localhost:8001"
    AI_SERVICE_TIMEOUT: float = 10.0    # giây

    # ── QR RSA Keys (dùng chung với ai-services) ──────────────
    QR_PRIVATE_KEY_PATH: str = "../ai-services/qr_generator/keys/private.pem"
    QR_PUBLIC_KEY_PATH: str  = "../ai-services/qr_generator/keys/public.pem"
    
    # Cho phép dán trực tiếp nội dung PEM vào ENV (ưu tiên hơn file path)
    QR_PRIVATE_KEY: Optional[str] = None
    QR_PUBLIC_KEY: Optional[str]  = None

    # ── ID / Phone Hash pepper (phải khớp với ai-services) ────
    ID_HASH_PEPPER: str = "tourism_id_pepper_v1_CHANGE_IN_PROD"

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://tourism-dashboard.pages.dev",  # Website của bạn trên Cloudflare
    ]

    # ── Nonce TTL — phải khớp với ai-services nonce_store ─────
    NONCE_TTL_HOURS: int = 24

    # ── Property: URI đã điền password ────────────────────────
    @property
    def mongo_uri_with_password(self) -> str:
        """
        Trả về URI MongoDB Atlas đã điền password.
        Ưu tiên dùng MONGO_URI nếu đã có {password} được điền sẵn,
        ngược lại tự điền từ MONGO_PASSWORD.
        """
        if "{password}" in self.MONGO_URI:
            return self.MONGO_URI.format(password=self.MONGO_PASSWORD)
        return self.MONGO_URI

    class Config:
        env_file          = ".env"
        env_file_encoding = "utf-8"
        # Cho phép alias: MONGO_URI trong .env override hoàn toàn
        extra = "ignore"


settings = Settings()
 