"""
test_schemas.py — Unit test Pydantic schemas
Kiểm tra validators, required fields, enum values
"""
import pytest
from datetime import datetime, timezone, timedelta

# Thêm path để import
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.checkin import CheckinRequest, CheckinResponse, Channel, Direction
from app.schemas.ticket import TicketIssueRequest, TicketEnrollFaceRequest, TicketRevokeRequest
from app.schemas.auth import LoginRequest, UserCreate, TokenResponse


# ══════════════════════════════════════════════════════════════
#  CheckinRequest — validator per channel
# ══════════════════════════════════════════════════════════════

class TestCheckinRequest:

    def _base(self, **kwargs):
        defaults = {"gate_id": "gate-001", "direction": Direction.IN, "channel": Channel.QR,
                    "qr_token": "fake.jwt.token"}
        return {**defaults, **kwargs}

    def test_qr_valid(self):
        req = CheckinRequest(**self._base())
        assert req.channel == Channel.QR
        assert req.gate_id == "gate-001"

    def test_qr_missing_token(self):
        with pytest.raises(Exception) as exc:
            CheckinRequest(**self._base(qr_token=None))
        assert "qr_token" in str(exc.value).lower() or "QR" in str(exc.value)

    def test_qr_face_missing_image(self):
        with pytest.raises(Exception):
            CheckinRequest(**self._base(channel=Channel.QR_FACE, probe_image_b64=None))

    def test_qr_face_valid(self):
        req = CheckinRequest(**self._base(
            channel=Channel.QR_FACE,
            probe_image_b64="base64imagedata=="
        ))
        assert req.channel == Channel.QR_FACE
        assert req.probe_image_b64 == "base64imagedata=="

    def test_id_channel_missing_id_number(self):
        with pytest.raises(Exception):
            CheckinRequest(**self._base(channel=Channel.ID, qr_token=None, id_number=None))

    def test_id_channel_valid(self):
        req = CheckinRequest(**self._base(
            channel=Channel.ID, qr_token=None, id_number="079012345678"
        ))
        assert req.id_number == "079012345678"

    def test_booking_channel_valid(self):
        req = CheckinRequest(**self._base(
            channel=Channel.BOOKING, qr_token=None, booking_id="BK001"
        ))
        assert req.booking_id == "BK001"

    def test_booking_missing_booking_id(self):
        with pytest.raises(Exception):
            CheckinRequest(**self._base(channel=Channel.BOOKING, qr_token=None, booking_id=None))

    def test_manual_with_phone(self):
        req = CheckinRequest(**self._base(
            channel=Channel.MANUAL, qr_token=None, phone="0901234567"
        ))
        assert req.phone == "0901234567"

    def test_manual_missing_both(self):
        with pytest.raises(Exception):
            CheckinRequest(**self._base(
                channel=Channel.MANUAL, qr_token=None, phone=None, ticket_id=None
            ))

    def test_direction_enum(self):
        req = CheckinRequest(**self._base(direction=Direction.OUT))
        assert req.direction == Direction.OUT

    def test_invalid_direction(self):
        with pytest.raises(Exception):
            CheckinRequest(**self._base(direction="SIDEWAYS"))


# ══════════════════════════════════════════════════════════════
#  TicketIssueRequest — date validator + phone validator
# ══════════════════════════════════════════════════════════════

class TestTicketIssueRequest:

    def _base(self, **kwargs):
        now = datetime.now(timezone.utc)
        defaults = {
            "customer_name":  "Nguyen Van A",
            "ticket_type":    "adult",
            "price":          150000.0,
            "valid_from":     now,
            "valid_until":    now + timedelta(hours=8),
            "payment_method": "cash",
        }
        return {**defaults, **kwargs}

    def test_valid_ticket(self):
        req = TicketIssueRequest(**self._base())
        assert req.ticket_type == "adult"
        assert req.price == 150000.0

    def test_invalid_ticket_type(self):
        with pytest.raises(Exception):
            TicketIssueRequest(**self._base(ticket_type="vip"))

    def test_invalid_payment_method(self):
        with pytest.raises(Exception):
            TicketIssueRequest(**self._base(payment_method="bitcoin"))

    def test_negative_price(self):
        with pytest.raises(Exception):
            TicketIssueRequest(**self._base(price=-1000))

    def test_valid_until_before_valid_from(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(Exception) as exc:
            TicketIssueRequest(**self._base(
                valid_from=now + timedelta(hours=8),
                valid_until=now,
            ))
        assert "valid_until" in str(exc.value).lower() or "sau" in str(exc.value)

    def test_phone_normalization(self):
        """SĐT có dấu gạch được tự clean thành chỉ số."""
        req = TicketIssueRequest(**self._base(customer_phone="090-123-4567"))
        assert req.customer_phone == "0901234567"

    def test_invalid_phone(self):
        with pytest.raises(Exception):
            TicketIssueRequest(**self._base(customer_phone="123"))

    def test_optional_fields_none(self):
        req = TicketIssueRequest(**self._base())
        assert req.customer_phone is None
        assert req.id_number is None
        assert req.booking_id is None


# ══════════════════════════════════════════════════════════════
#  UserCreate — username validator
# ══════════════════════════════════════════════════════════════

class TestUserCreate:

    def _base(self, **kwargs):
        defaults = {
            "username":  "staff01",
            "password":  "password123",
            "full_name": "Nhan Vien 01",
            "role":      "operator",
        }
        return {**defaults, **kwargs}

    def test_valid_user(self):
        user = UserCreate(**self._base())
        assert user.username == "staff01"
        assert user.role == "operator"

    def test_username_lowercased(self):
        user = UserCreate(**self._base(username="Staff01"))
        assert user.username == "staff01"

    def test_username_special_chars(self):
        with pytest.raises(Exception):
            UserCreate(**self._base(username="staff@01"))

    def test_invalid_role(self):
        with pytest.raises(Exception):
            UserCreate(**self._base(role="superadmin"))

    def test_short_password(self):
        with pytest.raises(Exception):
            UserCreate(**self._base(password="abc"))

    def test_short_username(self):
        with pytest.raises(Exception):
            UserCreate(**self._base(username="ab"))

    def test_valid_roles(self):
        for role in ["admin", "manager", "operator", "cashier"]:
            user = UserCreate(**self._base(role=role))
            assert user.role == role
 