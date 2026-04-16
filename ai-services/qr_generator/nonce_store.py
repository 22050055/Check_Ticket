"""
nonce_store.py — Lưu nonce (jti) đã dùng để chống QR reuse
Hỗ trợ 2 backend: MongoDB (production) và In-memory (dev/test)
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# TTL để xóa nonce cũ (tương ứng thời gian hiệu lực tối đa của QR)
NONCE_TTL_HOURS: int = int(os.getenv("NONCE_TTL_HOURS", "24"))


class NonceStore:
    """
    Quản lý nonce đã dùng.
    - Môi trường production: dùng MongoDB collection `used_nonces`.
    - Môi trường dev/test: dùng dict in-memory.
    """

    def __init__(self):
        self._use_mongo = os.getenv("USE_MONGO_NONCE", "false").lower() == "true"
        self._memory: dict[str, dict] = {}  # fallback in-memory
        self._collection = None

        if self._use_mongo:
            self._init_mongo()

    def _init_mongo(self):
        """Khởi tạo MongoDB collection (sync, dùng pymongo)."""
        try:
            from pymongo import MongoClient, ASCENDING
            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            db_name = os.getenv("MONGO_DB", "tourism_db")
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
            db = client[db_name]
            self._collection = db["used_nonces"]
            # TTL index: tự xóa sau NONCE_TTL_HOURS giờ
            self._collection.create_index(
                [("used_at", ASCENDING)],
                expireAfterSeconds=NONCE_TTL_HOURS * 3600,
                background=True,
            )
            logger.info("✅ NonceStore: MongoDB ready (TTL=%dh)", NONCE_TTL_HOURS)
        except Exception as exc:
            logger.warning("NonceStore MongoDB init thất bại, dùng in-memory: %s", exc)
            self._use_mongo = False
            self._collection = None

    def is_used(self, jti: str) -> bool:
        """Kiểm tra nonce đã được dùng chưa."""
        if self._use_mongo and self._collection is not None:
            return self._collection.find_one({"jti": jti}) is not None
        return jti in self._memory

    def mark_used(self, jti: str, ticket_id: Optional[str] = None) -> None:
        """Đánh dấu nonce đã dùng."""
        now = datetime.now(timezone.utc)
        record = {
            "jti": jti,
            "ticket_id": ticket_id,
            "used_at": now,
        }

        if self._use_mongo and self._collection is not None:
            try:
                self._collection.insert_one(record)
                return
            except Exception as exc:
                logger.error("Không thể lưu nonce vào MongoDB: %s", exc)

        # Fallback in-memory
        self._memory[jti] = record
        self._cleanup_memory()

    def _cleanup_memory(self) -> None:
        """Dọn nonce cũ trong in-memory store (tránh memory leak)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=NONCE_TTL_HOURS)
        expired = [
            k for k, v in self._memory.items()
            if v.get("used_at", datetime.now(timezone.utc)) < cutoff
        ]
        for k in expired:
            del self._memory[k]
        if expired:
            logger.debug("Dọn %d nonce hết hạn.", len(expired))

    def count_used(self) -> int:
        """Số nonce hiện đang lưu (dùng cho testing)."""
        if self._use_mongo and self._collection is not None:
            return self._collection.count_documents({})
        return len(self._memory)
