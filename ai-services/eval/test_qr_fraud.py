"""
test_qr_fraud.py — Kiểm thử phát hiện vé giả và vé đã dùng
Phục vụ Chương 4: Tỷ lệ vé giả/đã dùng bị phát hiện

Kịch bản test:
  1. QR hợp lệ — lần 1 → PASS
  2. QR hợp lệ — dùng lại lần 2 → FAIL (anti-reuse)
  3. QR chữ ký giả → FAIL (signature invalid)
  4. QR hết hạn → FAIL (expired)
  5. QR payload bị sửa → FAIL (signature mismatch)
"""
import sys
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from qr_generator.qr_service import QRService, QRInvalidError

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def run_fraud_tests() -> dict:
    """Chạy toàn bộ kịch bản test gian lận QR."""
    service = QRService()
    results = []
    passed = 0
    total = 0

    # ── Helper ───────────────────────────────────────────────
    def record(name: str, expected: str, got: str, detail: str = ""):
        nonlocal passed, total
        success = expected == got
        total += 1
        if success:
            passed += 1
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info("%s | %s | Expected=%s Got=%s %s", status, name, expected, got, detail)
        results.append({
            "test": name,
            "expected": expected,
            "got": got,
            "pass": success,
            "detail": detail,
        })

    now = datetime.now(timezone.utc)

    # ── Test 1: QR hợp lệ lần đầu ───────────────────────────
    ticket_id = f"TICKET_{uuid.uuid4().hex[:8]}"
    valid_until = now + timedelta(hours=8)
    try:
        token = service.create_ticket_jwt(ticket_id, "adult", valid_until)
        payload = service.verify_ticket_jwt(token)
        record("TC01_valid_first_use", "PASS", "PASS", f"ticket={payload.get('sub')}")
    except QRInvalidError as e:
        record("TC01_valid_first_use", "PASS", "FAIL", str(e))
    except RuntimeError as e:
        record("TC01_valid_first_use", "SKIP", "SKIP", f"No key: {e}")

    # ── Test 2: Dùng lại QR (anti-reuse) ────────────────────
    try:
        token2 = service.create_ticket_jwt(f"TICKET_{uuid.uuid4().hex[:8]}", "adult", valid_until)
        service.verify_ticket_jwt(token2)            # Lần 1 OK
        try:
            service.verify_ticket_jwt(token2)        # Lần 2 phải bị block
            record("TC02_reuse_blocked", "FAIL", "PASS", "Không bị block!")
        except QRInvalidError:
            record("TC02_reuse_blocked", "FAIL", "FAIL", "Reuse đã bị block ✓")
    except RuntimeError as e:
        record("TC02_reuse_blocked", "SKIP", "SKIP", f"No key: {e}")

    # ── Test 3: Chữ ký giả (tampered signature) ─────────────
    try:
        token3 = service.create_ticket_jwt(f"TICKET_{uuid.uuid4().hex[:8]}", "adult", valid_until)
        # Sửa 1 ký tự cuối của signature
        parts = token3.split(".")
        if len(parts) == 3:
            sig = parts[2]
            fake_sig = sig[:-4] + ("XXXX" if not sig.endswith("XXXX") else "YYYY")
            fake_token = ".".join([parts[0], parts[1], fake_sig])
            try:
                service.verify_ticket_jwt(fake_token)
                record("TC03_fake_signature", "FAIL", "PASS", "Chữ ký giả không bị phát hiện!")
            except QRInvalidError:
                record("TC03_fake_signature", "FAIL", "FAIL", "Chữ ký giả đã bị từ chối ✓")
    except RuntimeError as e:
        record("TC03_fake_signature", "SKIP", "SKIP", f"No key: {e}")

    # ── Test 4: QR hết hạn ───────────────────────────────────
    try:
        expired_until = now - timedelta(hours=1)   # Đã hết hạn 1 giờ trước
        token4 = service.create_ticket_jwt(f"TICKET_{uuid.uuid4().hex[:8]}", "adult", expired_until)
        try:
            service.verify_ticket_jwt(token4)
            record("TC04_expired_qr", "FAIL", "PASS", "QR hết hạn không bị từ chối!")
        except QRInvalidError:
            record("TC04_expired_qr", "FAIL", "FAIL", "QR hết hạn đã bị từ chối ✓")
    except RuntimeError as e:
        record("TC04_expired_qr", "SKIP", "SKIP", f"No key: {e}")

    # ── Test 5: Payload bị sửa (tampered payload) ────────────
    try:
        import base64 as b64mod
        token5 = service.create_ticket_jwt(f"TICKET_{uuid.uuid4().hex[:8]}", "adult", valid_until)
        parts = token5.split(".")
        if len(parts) == 3:
            # Decode payload, sửa ticket_type từ adult → vip
            pad = 4 - len(parts[1]) % 4
            decoded = b64mod.urlsafe_b64decode(parts[1] + "=" * pad).decode()
            import json as jsonmod
            payload_dict = jsonmod.loads(decoded)
            payload_dict["tid"] = "vip"   # Sửa loại vé
            new_payload = b64mod.urlsafe_b64encode(
                jsonmod.dumps(payload_dict).encode()
            ).decode().rstrip("=")
            tampered_token = ".".join([parts[0], new_payload, parts[2]])
            try:
                service.verify_ticket_jwt(tampered_token)
                record("TC05_tampered_payload", "FAIL", "PASS", "Payload giả không bị phát hiện!")
            except QRInvalidError:
                record("TC05_tampered_payload", "FAIL", "FAIL", "Payload giả đã bị từ chối ✓")
    except RuntimeError as e:
        record("TC05_tampered_payload", "SKIP", "SKIP", f"No key: {e}")

    # ── Tổng kết ─────────────────────────────────────────────
    skipped = sum(1 for r in results if r["got"] == "SKIP")
    effective_total = total - skipped
    detection_rate = (passed / effective_total * 100) if effective_total > 0 else 0

    summary = {
        "total_tests": total,
        "passed": passed,
        "skipped": skipped,
        "detection_rate_percent": round(detection_rate, 2),
        "results": results,
    }

    logger.info("\n=== KẾT QUẢ QR FRAUD TEST ===")
    logger.info("  Tổng: %d | Pass: %d | Skip: %d", total, passed, skipped)
    logger.info("  Detection rate: %.1f%%", detection_rate)

    with open("qr_fraud_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


if __name__ == "__main__":
    run_fraud_tests()
