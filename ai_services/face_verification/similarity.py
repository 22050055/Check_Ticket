"""
similarity.py — Tính cosine similarity giữa 2 embedding và quyết định xác thực
"""
import numpy as np
from .config import SIMILARITY_THRESHOLD


def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """
    Tính cosine similarity giữa 2 vector đã L2-normalize.
    Với L2-normalized vectors: cosine_sim = dot product.

    Returns:
        float trong [-1, 1]. Càng gần 1 càng giống nhau.
    """
    n1 = np.linalg.norm(emb1)
    n2 = np.linalg.norm(emb2)
    if n1 < 1e-10 or n2 < 1e-10:
        return 0.0
    return float(np.dot(emb1 / n1, emb2 / n2))


def euclidean_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
    return float(np.linalg.norm(emb1 - emb2))


def is_same_person(
    emb1: np.ndarray,
    emb2: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[bool, float]:
    """
    So sánh 2 embedding (1:1).

    Returns:
        (is_same: bool, score: float)
    """
    score = cosine_similarity(emb1, emb2)
    normalized_score = max(0.0, score)
    return normalized_score >= threshold, normalized_score


def is_same_person_multi(
    stored_embeddings: list[np.ndarray],
    probe_emb: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[bool, float, int]:
    """
    So sánh probe với NHIỀU embedding mẫu (1:N mẫu của cùng 1 người).
    Lấy MAX similarity để ra quyết định — giảm sai số do ánh sáng,
    góc quay, biểu cảm, khẩu trang một phần.

    Theo góp ý GVHD: lưu 3–5 embedding mẫu, verify lấy điểm cao nhất.

    Args:
        stored_embeddings: List embedding mẫu đã đăng ký (3–5 mẫu).
        probe_emb:         Embedding vừa chụp tại cổng.
        threshold:         Ngưỡng cosine similarity.

    Returns:
        (is_same: bool, best_score: float, best_idx: int)
        - best_score: điểm cao nhất trong tất cả cặp so sánh
        - best_idx:   chỉ số embedding mẫu cho điểm cao nhất
    """
    if not stored_embeddings:
        return False, 0.0, -1

    best_score = 0.0
    best_idx   = 0

    for i, stored_emb in enumerate(stored_embeddings):
        score = max(0.0, cosine_similarity(stored_emb, probe_emb))
        if score > best_score:
            best_score = score
            best_idx   = i

    return best_score >= threshold, best_score, best_idx


def explain_score(score: float, threshold: float = SIMILARITY_THRESHOLD) -> str:
    diff = score - threshold
    if score >= threshold:
        return f"✅ MATCH (score={score:.4f}, threshold={threshold}, +{diff:.4f})"
    return f"❌ NO MATCH (score={score:.4f}, threshold={threshold}, {diff:.4f})"


def explain_multi_score(
    best_score: float,
    best_idx: int,
    n_samples: int,
    threshold: float = SIMILARITY_THRESHOLD,
) -> str:
    diff = best_score - threshold
    status = "✅ MATCH" if best_score >= threshold else "❌ NO MATCH"
    return (
        f"{status} (best_score={best_score:.4f}, "
        f"sample={best_idx+1}/{n_samples}, "
        f"threshold={threshold}, diff={diff:+.4f})"
    )
 