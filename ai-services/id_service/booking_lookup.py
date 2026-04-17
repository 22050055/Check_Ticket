"""
booking_lookup.py — Tra cứu vé theo booking ID / SĐT / tên khách (manual fallback)
"""
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB  = os.getenv("MONGO_DB", "tourism_db")


class BookingLookupService:
    """
    Tra cứu thông tin đặt vé để hỗ trợ kênh Manual Fallback.
    Kết nối trực tiếp MongoDB (sync, dùng trong AI service nội bộ).
    """

    def __init__(self):
        self._db = None
        self._init_mongo()

    def _init_mongo(self):
        try:
            from pymongo import MongoClient
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
            self._db = client[MONGO_DB]
            logger.info("✅ BookingLookupService: MongoDB ready.")
        except Exception as exc:
            logger.warning("BookingLookup MongoDB init thất bại: %s", exc)
            self._db = None

    # ── Tra cứu theo booking ID ──────────────────────────────

    def find_by_booking_id(self, booking_id: str) -> Optional[dict]:
        """
        Tra cứu vé theo booking ID (mã đặt vé từ hệ thống bán vé).

        Returns:
            dict ticket info hoặc None.
        """
        if not booking_id or len(booking_id) < 4:
            return None
        return self._query_tickets({"booking_id": booking_id.strip().upper()})

    # ── Tra cứu theo SĐT ─────────────────────────────────────

    def find_by_phone(self, phone: str) -> list[dict]:
        """
        Tra cứu danh sách vé theo số điện thoại.
        Trả về list (1 SĐT có thể mua nhiều vé).
        """
        cleaned = re.sub(r'[^0-9]', '', phone)
        if len(cleaned) < 9:
            return []
        return self._query_tickets_many({"customer_phone": cleaned})

    # ── Tra cứu theo ticket ID trực tiếp ─────────────────────

    def find_by_ticket_id(self, ticket_id: str) -> Optional[dict]:
        """Tra cứu trực tiếp theo ticket_id trong DB."""
        return self._query_tickets({"_id": ticket_id})

    # ── Tra cứu theo ID hash ──────────────────────────────────

    def find_by_id_hash(self, id_hash: str) -> list[dict]:
        """
        Tra cứu vé theo hash CCCD/ID.
        Dùng kênh CCCD/ID verification.
        """
        if not id_hash or len(id_hash) != 64:  # SHA-256 hex = 64 ký tự
            return []
        # Tìm trong collection identities
        if self._db is None:
            return []
        try:
            identity = self._db["identities"].find_one({"id_hash": id_hash})
            if not identity:
                return []
            ticket_id = identity.get("ticket_id")
            if not ticket_id:
                return []
            ticket = self._db["tickets"].find_one({"_id": ticket_id})
            return [self._format_ticket(ticket)] if ticket else []
        except Exception as exc:
            logger.error("find_by_id_hash lỗi: %s", exc)
            return []

    # ── Helpers ───────────────────────────────────────────────

    def _query_tickets(self, query: dict) -> Optional[dict]:
        if self._db is None:
            return None
        try:
            ticket = self._db["tickets"].find_one(query)
            return self._format_ticket(ticket) if ticket else None
        except Exception as exc:
            logger.error("query_tickets lỗi: %s", exc)
            return None

    def _query_tickets_many(self, query: dict) -> list[dict]:
        if self._db is None:
            return []
        try:
            tickets = list(self._db["tickets"].find(query).limit(10))
            return [self._format_ticket(t) for t in tickets]
        except Exception as exc:
            logger.error("query_tickets_many lỗi: %s", exc)
            return []

    @staticmethod
    def _format_ticket(ticket: dict) -> dict:
        """Chuẩn hóa ticket document trả về (bỏ trường nhạy cảm)."""
        if not ticket:
            return {}
        return {
            "ticket_id": str(ticket.get("_id", "")),
            "booking_id": ticket.get("booking_id", ""),
            "ticket_type": ticket.get("ticket_type", ""),
            "status": ticket.get("status", ""),
            "valid_from": str(ticket.get("valid_from", "")),
            "valid_until": str(ticket.get("valid_until", "")),
            "customer_name": ticket.get("customer_name", ""),
            # Không trả về: id_number, face_embedding, CCCD
        }
 