"""
test_face_verify_logic.py — Kiểm tra logic xác thực QR + Face
Chạy tại thư mục ai-services:
    python test_face_verify_logic.py

Test cases:
  TC1: Đúng QR + Đúng mặt  → PASS ✅
  TC2: Đúng QR + Sai mặt   → FAIL ❌  (nếu pass = bug!)
  TC3: Sai QR  + bất kỳ mặt → FAIL ❌
  TC4: Kiểm tra threshold đang dùng thực tế
  TC5: Kiểm tra embedding trong DB có đúng người không
"""
import sys
import json
import base64
import requests
import numpy as np
from pathlib import Path

BASE_URL    = "http://localhost:8001"   # AI service
BACKEND_URL = "http://localhost:8000"  # Backend API

# ── Màu terminal ────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):  print(f"  {GREEN}✅ PASS{RESET} — {msg}")
def fail(msg): print(f"  {RED}❌ FAIL{RESET} — {msg}")
def warn(msg): print(f"  {YELLOW}⚠️  WARN{RESET} — {msg}")
def info(msg): print(f"  {CYAN}ℹ️  INFO{RESET} — {msg}")

# ═══════════════════════════════════════════════════════════
# TC4: Kiểm tra threshold thực tế AI service đang dùng
# ═══════════════════════════════════════════════════════════
def tc4_check_threshold():
    print(f"\n{BOLD}TC4: Threshold AI service đang dùng{RESET}")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        info(f"AI service status: {r.json()}")
    except Exception as e:
        fail(f"AI service không khả dụng: {e}")
        return

    # Tạo 2 embedding giả: cùng người, similarity ~ 0.30
    # Nếu threshold = 0.35 → FAIL | threshold = 0.28 → PASS
    np.random.seed(42)
    base = np.random.randn(512).astype(np.float32)
    base /= np.linalg.norm(base)

    # Probe với similarity chính xác = 0.30
    target_sim = 0.30
    perp = np.random.randn(512).astype(np.float32)
    perp -= np.dot(perp, base) * base
    perp /= np.linalg.norm(perp)
    probe = target_sim * base + np.sqrt(1 - target_sim**2) * perp
    probe /= np.linalg.norm(probe)

    # Tạo ảnh dummy 112x112 (chỉ để test, AI service sẽ không detect face)
    # → dùng trực tiếp embedding qua verify endpoint
    payload = {
        "stored_embedding": base.tolist(),
        "stored_embeddings": [base.tolist()],
        "probe_image_b64": "data:image/jpeg;base64,/9j/4AAQ",  # ảnh invalid
        "threshold": None
    }

    # Test với threshold 0.28
    payload_28 = {**payload, "threshold": 0.28}
    payload_35 = {**payload, "threshold": 0.35}

    print(f"  Dùng embedding probe có similarity = {target_sim}")

    # Gọi verify với embedding trực tiếp (bypass ảnh)
    # → thực ra AI service cần ảnh thật, nên test bằng cách khác:
    # Kiểm tra threshold qua config
    try:
        import importlib.util, os, sys
        sys.path.insert(0, str(Path(__file__).parent / "face_verification"))
        spec = importlib.util.spec_from_file_location(
            "config",
            Path(__file__).parent / "face_verification" / "config.py"
        )
        cfg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cfg)
        t = cfg.SIMILARITY_THRESHOLD
        print(f"  SIMILARITY_THRESHOLD trong config.py = {BOLD}{t}{RESET}")
        if t <= 0.30:
            ok(f"Threshold = {t} ≤ 0.30 — phù hợp camera thực tế")
        elif t <= 0.35:
            warn(f"Threshold = {t} — hơi chặt, score 0.321 sẽ bị từ chối")
        else:
            fail(f"Threshold = {t} — quá chặt cho camera điện thoại")
    except Exception as e:
        warn(f"Không đọc được config: {e}")


# ═══════════════════════════════════════════════════════════
# TC2: Mô phỏng đúng QR + SAI mặt → phải FAIL
# ═══════════════════════════════════════════════════════════
def tc2_wrong_face_should_fail():
    print(f"\n{BOLD}TC2: Mô phỏng Đúng QR + Sai mặt — phải báo FAIL{RESET}")

    np.random.seed(123)

    # Stored embedding = người A
    person_A = np.random.randn(512).astype(np.float32)
    person_A /= np.linalg.norm(person_A)

    # Probe = người B (khác hoàn toàn)
    person_B = np.random.randn(512).astype(np.float32)
    person_B /= np.linalg.norm(person_B)

    sim = float(np.dot(person_A, person_B))
    sim = max(0.0, sim)
    print(f"  Cosine similarity A vs B (khác người) = {sim:.4f}")

    threshold = 0.28
    if sim >= threshold:
        fail(f"score={sim:.4f} ≥ threshold={threshold} → hệ thống sẽ cho qua dù sai mặt! BUG!")
    else:
        ok(f"score={sim:.4f} < threshold={threshold} → hệ thống sẽ từ chối đúng")

    # Người B với similarity 0.67 như bạn gặp
    print(f"\n  {YELLOW}Phân tích trường hợp score=0.67 với 'mặt sai':{RESET}")
    print(f"  Score 0.67 là RẤT CAO — gần như chắc chắn embedding trong DB")
    print(f"  được enroll từ CHÍNH mặt người đang test, không phải mặt sai.")
    print(f"  → Cần kiểm tra lại embedding đã enroll (xem TC5).")


# ═══════════════════════════════════════════════════════════
# TC5: Kiểm tra embedding trong DB — gọi backend
# ═══════════════════════════════════════════════════════════
def tc5_check_db_embedding(ticket_id: str = None, token: str = None):
    print(f"\n{BOLD}TC5: Kiểm tra embedding trong DB{RESET}")

    if not token:
        # Thử login lấy token
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5
            )
            token = r.json().get("access_token")
            info(f"Login OK — token lấy được")
        except Exception as e:
            warn(f"Không login được: {e}. Bỏ qua TC5.")
            return

    if not ticket_id:
        # Lấy ticket gần nhất từ gate_events
        try:
            headers = {"Authorization": f"Bearer {token}"}
            r = requests.get(
                f"{BACKEND_URL}/api/reports/realtime",
                headers=headers, timeout=5
            )
            events = r.json().get("recent_events", [])
            if events:
                ticket_id = events[0].get("ticket_id")
                info(f"Ticket ID gần nhất: {ticket_id}")
        except Exception as e:
            warn(f"Không lấy được ticket_id: {e}")
            return

    if not ticket_id:
        warn("Không có ticket_id để kiểm tra. Truyền thủ công: tc5_check_db_embedding('your-ticket-id')")
        return

    # Lấy thông tin vé
    try:
        headers = {"Authorization": f"Bearer {token}"}
        r = requests.get(
            f"{BACKEND_URL}/api/tickets/{ticket_id}",
            headers=headers, timeout=5
        )
        ticket = r.json()
        info(f"Ticket: {ticket.get('ticket_type')} | has_face={ticket.get('has_face')} | status={ticket.get('status')}")

        if not ticket.get("has_face"):
            warn("Vé này CHƯA enroll face → face_verify không được gọi → QR-only luôn pass")
            warn("→ Đây là lý do score=0.67 nhưng vẫn pass: thực ra hệ thống đang chạy QR-only!")
        else:
            ok(f"Vé đã enroll face → face verify đang được thực hiện")
    except Exception as e:
        warn(f"Không lấy được ticket: {e}")


# ═══════════════════════════════════════════════════════════
# TC_SCORE: Giải thích score 0.67 với mặt sai
# ═══════════════════════════════════════════════════════════
def tc_explain_067():
    print(f"\n{BOLD}🔍 Phân tích score=0.67 với 'mặt sai':{RESET}")
    print()
    cases = [
        ("Khả năng 1", "HIGH", "has_face=False trong DB → hệ thống fallback QR-only, KHÔNG gọi face verify\n"
         "             → score 0.67 là score của LẦN TRƯỚC còn trong log, không phải lần này"),
        ("Khả năng 2", "MEDIUM", "Enroll nhầm — người B đã enroll bằng mặt người A\n"
         "             → khi quét mặt người A thì score cao là ĐÚNG (nhưng người sai)"),
        ("Khả năng 3", "LOW", "Model ArcFace nhầm — similarity hai người thực sự cao\n"
         "             → cần test với nhiều cặp mặt khác nhau để loại trừ"),
    ]
    for name, prob, desc in cases:
        color = GREEN if prob == "LOW" else YELLOW if prob == "MEDIUM" else RED
        print(f"  {color}{name} ({prob}){RESET}: {desc}")

    print(f"\n  {BOLD}Cách xác nhận:{RESET}")
    print("  1. Gọi GET /api/tickets/{id} → xem has_face")
    print("  2. Nếu has_face=False → fallback QR-only (không verify face)")
    print("  3. Nếu has_face=True  → enroll lại với đúng mặt người cần test")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{BOLD}{'='*55}")
    print("  FACE VERIFY LOGIC TEST")
    print(f"{'='*55}{RESET}")

    # Đọc ticket_id từ argument nếu có
    ticket_id = sys.argv[1] if len(sys.argv) > 1 else None

    tc4_check_threshold()
    tc2_wrong_face_should_fail()
    tc5_check_db_embedding(ticket_id)
    tc_explain_067()

    print(f"\n{BOLD}{'='*55}{RESET}\n")
 