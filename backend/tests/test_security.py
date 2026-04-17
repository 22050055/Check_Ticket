"""
test_security.py — Unit test JWT, RBAC, password hashing
"""
import pytest
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock settings trước khi import security
from unittest.mock import patch, MagicMock


class TestPasswordHashing:

    def test_hash_and_verify(self):
        """Test trực tiếp bcrypt — bỏ qua passlib version warning."""
        import bcrypt
        pwd = b"mypassword123"
        hashed = bcrypt.hashpw(pwd, bcrypt.gensalt())
        assert bcrypt.checkpw(pwd, hashed) == True

    def test_wrong_password(self):
        import bcrypt
        hashed = bcrypt.hashpw(b"correct", bcrypt.gensalt())
        assert bcrypt.checkpw(b"wrong", hashed) == False

    def test_hash_is_different_each_time(self):
        import bcrypt
        h1 = bcrypt.hashpw(b"same", bcrypt.gensalt())
        h2 = bcrypt.hashpw(b"same", bcrypt.gensalt())
        assert h1 != h2  # bcrypt salt khác nhau mỗi lần


class TestJWT:

    def test_create_and_decode_access_token(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token("user-001", "operator", gate_id="gate-001")
        payload = decode_token(token)
        assert payload["sub"]     == "user-001"
        assert payload["role"]    == "operator"
        assert payload["gate_id"] == "gate-001"
        assert payload["type"]    == "access"

    def test_access_token_without_gate_id(self):
        from app.core.security import create_access_token, decode_token
        token = create_access_token("user-001", "admin")
        payload = decode_token(token)
        assert payload["gate_id"] is None
        assert payload["role"]    == "admin"

    def test_create_refresh_token(self):
        from app.core.security import create_refresh_token, decode_token
        token = create_refresh_token("user-001")
        payload = decode_token(token)
        assert payload["sub"]  == "user-001"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        from app.core.security import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("invalid.token.here")
        assert exc.value.status_code == 401

    def test_tokens_are_different(self):
        from app.core.security import create_access_token, create_refresh_token
        access  = create_access_token("u1", "operator")
        refresh = create_refresh_token("u1")
        assert access != refresh


class TestRBACHierarchy:

    def test_role_hierarchy_values(self):
        from app.core.security import ROLE_HIERARCHY, Role
        assert ROLE_HIERARCHY[Role.ADMIN]    == 4
        assert ROLE_HIERARCHY[Role.MANAGER]  == 3
        assert ROLE_HIERARCHY[Role.CASHIER]  == 2
        assert ROLE_HIERARCHY[Role.OPERATOR] == 1

    def test_admin_highest_level(self):
        from app.core.security import ROLE_HIERARCHY, Role
        admin_level = ROLE_HIERARCHY[Role.ADMIN]
        assert all(admin_level >= v for v in ROLE_HIERARCHY.values())

    def test_role_enum_values(self):
        from app.core.security import Role
        assert Role.ADMIN    == "admin"
        assert Role.MANAGER  == "manager"
        assert Role.OPERATOR == "operator"
        assert Role.CASHIER  == "cashier"
 