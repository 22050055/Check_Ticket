"""
test_models.py — Unit test models factories và constants
"""
import pytest
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import (
    new_user, new_ticket, new_identity, new_transaction,
    new_gate, new_gate_event, new_audit_log, new_used_nonce,
    new_customer,
    TicketStatus, GateEventResult, Direction, Channel, Role, Action,
)


class TestFactories:

    def test_new_user(self):
        doc = new_user("admin", "hash123", "Admin User", "admin")
        assert doc["username"]      == "admin"
        assert doc["password_hash"] == "hash123"
        assert doc["role"]          == "admin"
        assert doc["is_active"]     == True
        assert doc["gate_id"]       is None
        assert "_id" in doc
        assert isinstance(doc["created_at"], datetime)

    def test_new_user_with_gate(self):
        doc = new_user("op1", "hash", "Op 1", "operator", gate_id="gate-001")
        assert doc["gate_id"] == "gate-001"

    def test_new_ticket(self):
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        doc = new_ticket("adult", 150000.0, now, now + timedelta(hours=8))
        assert doc["ticket_type"] == "adult"
        assert doc["price"]       == 150000.0
        assert doc["status"]      == "active"
        assert doc["venue_id"]    == "tourism_default"
        assert doc["created_at"]  == doc["updated_at"]

    def test_new_identity_defaults(self):
        doc = new_identity("ticket-001")
        assert doc["ticket_id"]      == "ticket-001"
        assert doc["has_face"]       == False
        assert doc["face_embedding"] is None
        assert doc["id_hash"]        is None
        assert doc["phone_hash"]     is None

    def test_new_identity_with_hashes(self):
        doc = new_identity("ticket-001",
                           booking_id="BK001",
                           id_hash="hash_cccd",
                           phone_hash="hash_phone")
        assert doc["booking_id"]  == "BK001"
        assert doc["id_hash"]     == "hash_cccd"
        assert doc["phone_hash"]  == "hash_phone"

    def test_new_transaction(self):
        doc = new_transaction("ticket-001", "adult", 150000.0, "cash")
        assert doc["ticket_id"]      == "ticket-001"
        assert doc["ticket_type"]    == "adult"
        assert doc["amount"]         == 150000.0
        assert doc["payment_method"] == "cash"

    def test_new_gate(self):
        doc = new_gate("gate_a1", "Cổng A1", "Khu A")
        assert doc["gate_code"] == "GATE_A1"   # phải uppercase
        assert doc["is_active"] == True

    def test_new_gate_code_uppercase(self):
        doc = new_gate("gate_b2", "Cổng B2")
        assert doc["gate_code"] == "GATE_B2"

    def test_new_gate_event_success(self):
        doc = new_gate_event(
            gate_id="gate-001", direction="IN", channel="QR",
            result="SUCCESS", ticket_id="t-001", ticket_type="adult",
            operator_id="user-001",
        )
        assert doc["result"]      == "SUCCESS"
        assert doc["direction"]   == "IN"
        assert doc["channel"]     == "QR"
        assert doc["fail_reason"] is None
        assert doc["face_score"]  is None

    def test_new_gate_event_fail(self):
        doc = new_gate_event(
            gate_id="gate-001", direction="IN", channel="QR",
            result="FAIL", fail_reason="QR đã được sử dụng.",
        )
        assert doc["result"]      == "FAIL"
        assert doc["fail_reason"] == "QR đã được sử dụng."

    def test_new_gate_event_with_face_score(self):
        doc = new_gate_event(
            gate_id="g1", direction="IN", channel="QR_FACE",
            result="SUCCESS", face_score=0.412,
        )
        assert doc["face_score"] == 0.412

    def test_new_audit_log(self):
        doc = new_audit_log("user-001", "LOGIN", ip="127.0.0.1")
        assert doc["user_id"] == "user-001"
        assert doc["action"]  == "LOGIN"
        assert doc["ip"]      == "127.0.0.1"
        assert doc["resource"] is None

    def test_new_used_nonce(self):
        doc = new_used_nonce("jti-abc123", "ticket-001")
        assert doc["jti"]       == "jti-abc123"
        assert doc["ticket_id"] == "ticket-001"
        assert "used_at" in doc

    def test_all_factories_generate_unique_ids(self):
        ids = [
            new_user("u1","h","U1","operator")["_id"],
            new_user("u2","h","U2","operator")["_id"],
            new_ticket("adult",1.0,datetime.now(timezone.utc),datetime.now(timezone.utc))["_id"],
            new_gate("G1","Gate 1")["_id"],
        ]
        assert len(ids) == len(set(ids)), "IDs phải unique"


class TestConstants:

    def test_ticket_status(self):
        assert TicketStatus.ACTIVE  == "active"
        assert TicketStatus.USED    == "used"
        assert TicketStatus.REVOKED == "revoked"
        assert TicketStatus.EXPIRED == "expired"

    def test_gate_event_result(self):
        assert GateEventResult.SUCCESS == "SUCCESS"
        assert GateEventResult.FAIL    == "FAIL"

    def test_direction(self):
        assert Direction.IN  == "IN"
        assert Direction.OUT == "OUT"

    def test_channel(self):
        assert Channel.QR      == "QR"
        assert Channel.QR_FACE == "QR_FACE"
        assert Channel.ID      == "ID"
        assert Channel.BOOKING == "BOOKING"
        assert Channel.MANUAL  == "MANUAL"

    def test_role(self):
        assert Role.ADMIN    == "admin"
        assert Role.MANAGER  == "manager"
        assert Role.OPERATOR == "operator"
        assert Role.CASHIER  == "cashier"

    def test_action(self):
        assert Action.LOGIN         == "LOGIN"
        assert Action.ISSUE_TICKET  == "ISSUE_TICKET"
        assert Action.REVOKE_TICKET == "REVOKE_TICKET"
        assert Action.CHECKIN       == "CHECKIN"
        assert Action.CHECKOUT      == "CHECKOUT"
        assert Action.FACE_ENROLL   == "FACE_ENROLL"
