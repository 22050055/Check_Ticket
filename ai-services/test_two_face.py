"""
test_two_face.py — Test thực sự 2 khuôn mặt khác nhau
Chạy: python test_two_face.py <img_A.jpg> <img_B.jpg>

img_A = ảnh người đã enroll
img_B = ảnh người KHÁC (mặt "sai")

Kết quả mong đợi:
  A vs A (same) → score > 0.28 → PASS ✅
  A vs B (diff) → score < 0.28 → FAIL ✅ (đúng logic)
"""
import sys, base64, json, requests
import numpy as np
from pathlib import Path

BASE_URL = "http://localhost:8001"

def img_to_b64(path: str) -> str:
    data = Path(path).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()

def enroll(img_b64: str) -> list:
    r = requests.post(f"{BASE_URL}/enroll", json={"image_b64": img_b64}, timeout=15)
    r.raise_for_status()
    return r.json()["embeddings"][0]   # lấy embedding đầu tiên

def verify(stored_emb: list, probe_b64: str, threshold: float = 0.28) -> dict:
    r = requests.post(f"{BASE_URL}/verify", json={
        "stored_embeddings": [stored_emb],
        "probe_image_b64": probe_b64,
        "threshold": threshold,
    }, timeout=15)
    r.raise_for_status()
    return r.json()

def cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a/np.linalg.norm(a), b/np.linalg.norm(b)))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_two_face.py <img_A.jpg> <img_B.jpg>")
        print()
        print("img_A = ảnh người đã enroll vào vé")
        print("img_B = ảnh người KHÁC (mặt 'sai' cần bị từ chối)")
        sys.exit(1)

    img_A_path = sys.argv[1]
    img_B_path = sys.argv[2]

    print("\n" + "="*50)
    print("  TWO-FACE VERIFICATION TEST")
    print("="*50)

    print(f"\n[1/4] Đang enroll ảnh A ({img_A_path})...")
    b64_A = img_to_b64(img_A_path)
    emb_A = enroll(b64_A)
    print(f"      Embedding A: {len(emb_A)}-d ✅")

    print(f"\n[2/4] Đang enroll ảnh B ({img_B_path})...")
    b64_B = img_to_b64(img_B_path)
    emb_B = enroll(b64_B)
    print(f"      Embedding B: {len(emb_B)}-d ✅")

    sim_AA = max(0, cosine(emb_A, emb_A))
    sim_AB = max(0, cosine(emb_A, emb_B))
    print(f"\n[3/4] Cosine similarity:")
    print(f"      A vs A (cùng người) = {sim_AA:.4f}")
    print(f"      A vs B (khác người) = {sim_AB:.4f}")

    threshold = 0.28
    print(f"\n[4/4] Verify với threshold={threshold}:")

    # Test A vs A (phải PASS)
    r_AA = verify(emb_A, b64_A, threshold)
    status = "✅ PASS" if r_AA["is_same_person"] else "❌ FAIL (bug!)"
    print(f"      Enroll A, verify A → score={r_AA['score']:.4f} → {status}")
    if not r_AA["is_same_person"]:
        print(f"      ⚠️  Cùng người mà bị từ chối → threshold quá chặt hoặc ảnh chất lượng kém")

    # Test A vs B (phải FAIL)
    r_AB = verify(emb_A, b64_B, threshold)
    if not r_AB["is_same_person"]:
        status = "✅ PASS (từ chối đúng)"
    else:
        status = f"❌ BUG! Mặt sai mà được chấp nhận (score={r_AB['score']:.4f})"

    print(f"      Enroll A, verify B → score={r_AB['score']:.4f} → {status}")

    print("\n" + "="*50)
    if r_AA["is_same_person"] and not r_AB["is_same_person"]:
        print("  ✅ Logic hoạt động đúng!")
        print(f"     Margin: cùng người={r_AA['score']:.3f} | khác người={r_AB['score']:.3f}")
        print(f"     Khoảng cách: {r_AA['score'] - r_AB['score']:.3f}")
    elif r_AB["is_same_person"]:
        print("  ❌ BUG XÁC NHẬN: Mặt B được nhận nhầm là mặt A!")
        print(f"     score={r_AB['score']:.4f} ≥ threshold={threshold}")
        print(f"     → Cần tăng threshold hoặc kiểm tra chất lượng enroll")
    else:
        print("  ⚠️  Cả 2 đều fail — vấn đề chất lượng ảnh hoặc threshold")
    print("="*50 + "\n")
 