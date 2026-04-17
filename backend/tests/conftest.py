"""
conftest.py — Pytest fixtures dùng chung cho tất cả test
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


# ── Event loop ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Mock MongoDB ──────────────────────────────────────────────

def make_mock_collection(docs: list = None):
    """Tạo mock Motor collection với find_one, insert_one, update_one."""
    col = MagicMock()
    docs = docs or []

    async def find_one(query, *args, **kwargs):
        for doc in docs:
            match = all(doc.get(k) == v for k, v in query.items()
                        if not isinstance(v, dict))
            if match:
                return doc
        return None

    async def insert_one(doc):
        docs.append(doc)
        result = MagicMock()
        result.inserted_id = doc.get("_id")
        return result

    async def update_one(query, update, upsert=False):
        result = MagicMock()
        result.modified_count = 0
        for doc in docs:
            match = all(doc.get(k) == v for k, v in query.items()
                        if not isinstance(v, dict))
            if match:
                if "$set" in update:
                    doc.update(update["$set"])
                result.modified_count = 1
                return result
        if upsert:
            new_doc = {**query, **(update.get("$set", {}))}
            docs.append(new_doc)
        return result

    async def count_documents(query):
        count = 0
        for doc in docs:
            match = all(doc.get(k) == v for k, v in query.items()
                        if not isinstance(v, dict))
            if match:
                count += 1
        return count

    col.find_one    = find_one
    col.insert_one  = insert_one
    col.update_one  = update_one
    col.count_documents = count_documents
    return col, docs


@pytest.fixture
def mock_db():
    """Mock database với tất cả collections cần thiết."""
    collections = {}
    db = MagicMock()

    def getitem(name):
        if name not in collections:
            col, _ = make_mock_collection()
            collections[name] = col
        return collections[name]

    db.__getitem__ = getitem
    db._data = collections
    return db


# ── Sample data ───────────────────────────────────────────────

@pytest.fixture
def sample_user():
    return {
        "_id":           "user-001",
        "username":      "operator1",
        "password_hash": "$2b$12$fakehash",
        "full_name":     "Nguyen Van A",
        "role":          "operator",
        "gate_id":       "gate-001",
        "is_active":     True,
        "created_at":    datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_ticket():
    return {
        "_id":         "ticket-001",
        "booking_id":  "BK001",
        "customer_id": "cust-001",
        "ticket_type": "adult",
        "price":       150000.0,
        "valid_from":  datetime.now(timezone.utc) - timedelta(hours=1),
        "valid_until": datetime.now(timezone.utc) + timedelta(hours=8),
        "status":      "active",
        "venue_id":    "tourism_default",
        "customer_name": "Nguyen Van B",
        "created_at":  datetime.now(timezone.utc),
        "updated_at":  datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_identity(sample_ticket):
    return {
        "_id":             "identity-001",
        "ticket_id":       sample_ticket["_id"],
        "booking_id":      "BK001",
        "id_hash":         None,
        "phone_hash":      None,
        "face_embedding":  None,
        "face_image_hash": None,
        "has_face":        False,
        "created_at":      datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_gate():
    return {
        "_id":        "gate-001",
        "gate_code":  "GATE_A1",
        "name":       "Cổng A1 — Vào chính",
        "location":   "Khu vực A",
        "is_active":  True,
        "created_at": datetime.now(timezone.utc),
    }
 