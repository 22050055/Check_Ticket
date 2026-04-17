"""
test_channel_adapter.py — Unit test ChannelAdapter
Dùng mock DB, không cần MongoDB thật.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.channel_adapter import ChannelAdapter, CheckinResult, _hash_id, _hash_phone
from app.schemas.checkin import Channel, Direction


# ── Mock DB helper ────────────────────────────────────────────

def make_db(tickets=None, identities=None, used_nonces=None):
    """Tạo mock DB với data cố định."""
    tickets     = tickets     or []
    identities  = identities  or []
    used_nonces = used_nonces or []

    db = MagicMock()
    store = {"tickets": tickets, "identities": identities, "used_nonces": used_nonces}

    def get_col(name):
        data = store.get(name, [])
        col = MagicMock()

        async def find_one(query, *a, **kw):
            for doc in data:
                if all(doc.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                    return doc
            return None

        async def insert_one(doc):
            data.append(doc)
            r = MagicMock(); r.inserted_id = doc.get("_id"); return r

        async def update_one(query, update, upsert=False):
            r = MagicMock(); r.modified_count = 0
            for doc in data:
                if all(doc.get(k) == v for k, v in query.items() if not isinstance(v, dict)):
                    if "$set" in update: doc.update(update["$set"])
                    r.modified_count = 1; return r
            return r

        async def aggregate(pipeline): return MagicMock()

        col.find_one    = find_one
        col.insert_one  = insert_one
        col.update_one  = update_one
        col.aggregate   = aggregate
        return col

    db.__getitem__ = MagicMock(side_effect=get_col)
    return db


def active_ticket(ticket_id="t-001"):
    return {
        "_id": ticket_id, "ticket_type": "adult", "price": 150000.0,
        "status": "active", "customer_name": "Nguyen Van A",
        "valid_from": datetime.now(timezone.utc) - timedelta(hours=1),
        "valid_until": datetime.now(timezone.utc) + timedelta(hours=8),
        "venue_id": "tourism_default",
    }


# ══════════════════════════════════════════════════════════════
#  Kênh QR
# ══════════════════════════════════════════════════════════════

class TestQRChannel:

    def setup_method(self):
        """Patch QR public key cho mỗi test."""
        self.patcher = patch(
            'app.services.channel_adapter._get_public_key',
            return_value=None  # key = None → sẽ trả lỗi "Chưa cấu hình"
        )
        self.patcher.start()

    def teardown_method(self):
        self.patcher.stop()

    @pytest.mark.asyncio
    async def test_qr_missing_token(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_qr(None)
        assert result.success == False
        assert "Thiếu" in result.message

    @pytest.mark.asyncio
    async def test_qr_no_public_key(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_qr("fake.token.here")
        assert result.success == False
        assert "public key" in result.message.lower() or "Chưa cấu hình" in result.message


# ══════════════════════════════════════════════════════════════
#  Kênh Booking ID
# ══════════════════════════════════════════════════════════════

class TestBookingChannel:

    @pytest.mark.asyncio
    async def test_booking_found_active(self):
        ticket  = active_ticket()
        identity = {"_id": "id-001", "ticket_id": "t-001", "booking_id": "BK001"}
        db = make_db(tickets=[ticket], identities=[identity])
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking("BK001")
        assert result.success == True
        assert result.ticket_id == "t-001"
        assert result.ticket_type == "adult"

    @pytest.mark.asyncio
    async def test_booking_not_found(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking("BK999")
        assert result.success == False
        assert "BK999" in result.message

    @pytest.mark.asyncio
    async def test_booking_missing_id(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking(None)
        assert result.success == False

    @pytest.mark.asyncio
    async def test_booking_used_ticket(self):
        ticket = {**active_ticket(), "status": "used"}
        identity = {"_id": "id-001", "ticket_id": "t-001", "booking_id": "BK001"}
        db = make_db(tickets=[ticket], identities=[identity])
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking("BK001")
        assert result.success == False
        assert "sử dụng" in result.message

    @pytest.mark.asyncio
    async def test_booking_revoked_ticket(self):
        ticket = {**active_ticket(), "status": "revoked"}
        identity = {"_id": "id-001", "ticket_id": "t-001", "booking_id": "BK001"}
        db = make_db(tickets=[ticket], identities=[identity])
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking("BK001")
        assert result.success == False
        assert "thu hồi" in result.message

    @pytest.mark.asyncio
    async def test_booking_expired_ticket(self):
        ticket = {
            **active_ticket(),
            "valid_until": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        identity = {"_id": "id-001", "ticket_id": "t-001", "booking_id": "BK001"}
        db = make_db(tickets=[ticket], identities=[identity])
        adapter = ChannelAdapter(db)
        result = await adapter._handle_booking("BK001")
        assert result.success == False
        assert "hết hạn" in result.message


# ══════════════════════════════════════════════════════════════
#  Kênh Manual
# ══════════════════════════════════════════════════════════════

class TestManualChannel:

    @pytest.mark.asyncio
    async def test_manual_by_ticket_id(self):
        ticket = active_ticket("t-002")
        db = make_db(tickets=[ticket])
        adapter = ChannelAdapter(db)
        result = await adapter._handle_manual(phone=None, ticket_id="t-002")
        assert result.success == True
        assert result.ticket_id == "t-002"

    @pytest.mark.asyncio
    async def test_manual_ticket_not_found(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_manual(phone=None, ticket_id="not-exist")
        assert result.success == False

    @pytest.mark.asyncio
    async def test_manual_missing_both(self):
        db = make_db()
        adapter = ChannelAdapter(db)
        result = await adapter._handle_manual(phone=None, ticket_id=None)
        assert result.success == False
        assert "phone" in result.message.lower() or "ticket_id" in result.message.lower()


# ══════════════════════════════════════════════════════════════
#  _validate_ticket_status
# ══════════════════════════════════════════════════════════════

class TestValidateTicketStatus:

    def test_active_ticket(self):
        ticket = active_ticket()
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert err is None

    def test_used_ticket(self):
        ticket = {**active_ticket(), "status": "used"}
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert err is not None
        assert "sử dụng" in err

    def test_revoked_ticket(self):
        ticket = {**active_ticket(), "status": "revoked"}
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert "thu hồi" in err

    def test_expired_by_status(self):
        ticket = {**active_ticket(), "status": "expired"}
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert "hết hạn" in err

    def test_expired_by_datetime(self):
        ticket = {
            **active_ticket(),
            "valid_until": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert err is not None
        assert "hết hạn" in err

    def test_not_yet_expired(self):
        ticket = {
            **active_ticket(),
            "valid_until": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        err = ChannelAdapter._validate_ticket_status(ticket)
        assert err is None


# ══════════════════════════════════════════════════════════════
#  Hash functions
# ══════════════════════════════════════════════════════════════

class TestHashFunctions:

    def test_hash_id_consistent(self):
        """Cùng CCCD phải cho cùng hash."""
        h1 = _hash_id("079012345678")
        h2 = _hash_id("079012345678")
        assert h1 == h2

    def test_hash_id_case_insensitive(self):
        """Sau khi strip + upper → hash giống nhau."""
        assert _hash_id("079abc") == _hash_id("079ABC")

    def test_hash_id_whitespace_stripped(self):
        assert _hash_id(" 079012 ") == _hash_id("079012")

    def test_hash_id_different_ids(self):
        """CCCD khác nhau phải cho hash khác nhau."""
        assert _hash_id("079000000001") != _hash_id("079000000002")

    def test_hash_id_hex_output(self):
        h = _hash_id("079012345678")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_phone_consistent(self):
        h1 = _hash_phone("0901234567")
        h2 = _hash_phone("0901234567")
        assert h1 == h2

    def test_hash_phone_strips_non_digits(self):
        assert _hash_phone("090-123-4567") == _hash_phone("0901234567")

    def test_hash_phone_invalid(self):
        with pytest.raises(ValueError):
            _hash_phone("abc")
 