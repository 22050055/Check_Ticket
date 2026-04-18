"""
test_load_simulation.py — Mô phỏng tải check-in theo giờ cao điểm
Phục vụ Chương 4: Tải mô phỏng theo giờ cao điểm

Đo:
  - Thời gian phản hồi trung bình / p95 / p99 (ms)
  - Throughput (requests/giây)
  - Tỷ lệ lỗi dưới tải
"""
import sys
import json
import logging
import time
import statistics
import concurrent.futures
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


# ── Mock check-in function (thay bằng HTTP call thực nếu cần) ──

def mock_qr_checkin(ticket_id: str) -> dict:
    """Mô phỏng check-in QR (thay bằng requests.post thực)."""
    import random
    # Giả lập latency 20–80ms
    delay = random.uniform(0.020, 0.080)
    time.sleep(delay)
    # Giả lập 2% lỗi server
    if random.random() < 0.02:
        raise Exception("Server timeout")
    return {"status": "ok", "ticket_id": ticket_id, "latency_ms": delay * 1000}


def mock_face_checkin(ticket_id: str) -> dict:
    """Mô phỏng check-in QR + Face (nặng hơn, 100–300ms)."""
    import random
    delay = random.uniform(0.100, 0.300)
    time.sleep(delay)
    if random.random() < 0.03:
        raise Exception("Face service timeout")
    return {"status": "ok", "ticket_id": ticket_id, "latency_ms": delay * 1000}


# ── Load test engine ─────────────────────────────────────────

def run_load_test(
    fn: Callable,
    n_requests: int,
    concurrency: int,
    label: str = "load_test",
) -> dict:
    """
    Chạy load test với concurrency threads.

    Args:
        fn: Hàm check-in cần test (nhận ticket_id).
        n_requests: Tổng số request.
        concurrency: Số thread song song.
        label: Nhãn cho kết quả.

    Returns:
        dict kết quả thống kê.
    """
    latencies = []
    errors = 0
    start_total = time.perf_counter()

    def single_request(_):
        ticket_id = f"T_{uuid.uuid4().hex[:8]}"
        t0 = time.perf_counter()
        try:
            fn(ticket_id)
            return (time.perf_counter() - t0) * 1000, None
        except Exception as e:
            return (time.perf_counter() - t0) * 1000, str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = list(executor.map(single_request, range(n_requests)))

    for latency_ms, err in futures:
        latencies.append(latency_ms)
        if err:
            errors += 1

    total_time = time.perf_counter() - start_total
    throughput = n_requests / total_time

    result = {
        "label": label,
        "n_requests": n_requests,
        "concurrency": concurrency,
        "total_time_s": round(total_time, 3),
        "throughput_rps": round(throughput, 2),
        "error_count": errors,
        "error_rate_percent": round(errors / n_requests * 100, 2),
        "latency_ms": {
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
            "mean": round(statistics.mean(latencies), 2),
            "median": round(statistics.median(latencies), 2),
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
            "p99": round(sorted(latencies)[int(len(latencies) * 0.99)], 2),
        },
    }

    logger.info("\n=== %s ===", label.upper())
    logger.info("  Requests: %d | Concurrency: %d", n_requests, concurrency)
    logger.info("  Throughput: %.1f req/s | Total: %.2fs", throughput, total_time)
    logger.info(
        "  Latency (ms): mean=%.1f | p95=%.1f | p99=%.1f",
        result["latency_ms"]["mean"],
        result["latency_ms"]["p95"],
        result["latency_ms"]["p99"],
    )
    logger.info(
        "  Errors: %d (%.1f%%)", errors, result["error_rate_percent"]
    )

    return result


def run_peak_hour_simulation():
    """
    Mô phỏng giờ cao điểm: nhiều khách vào cùng lúc tại nhiều cổng.
    Kịch bản: 500 khách / 30 phút = ~16.7 khách/phút = ~0.28 req/s mỗi cổng (4 cổng).
    """
    logger.info("🚦 Bắt đầu Peak Hour Simulation")

    all_results = []

    # Kịch bản 1: QR-only, tải nhẹ
    r1 = run_load_test(mock_qr_checkin, n_requests=200, concurrency=5, label="QR_only_light")
    all_results.append(r1)

    # Kịch bản 2: QR-only, tải cao (giờ cao điểm)
    r2 = run_load_test(mock_qr_checkin, n_requests=500, concurrency=20, label="QR_only_peak")
    all_results.append(r2)

    # Kịch bản 3: QR + Face (nặng hơn)
    r3 = run_load_test(mock_face_checkin, n_requests=100, concurrency=5, label="QR_face_light")
    all_results.append(r3)

    # Kịch bản 4: QR + Face, tải cao
    r4 = run_load_test(mock_face_checkin, n_requests=200, concurrency=10, label="QR_face_peak")
    all_results.append(r4)

    # Lưu kết quả
    output = {
        "test_time": datetime.now(timezone.utc).isoformat(),
        "scenarios": all_results,
        "summary": {
            "best_throughput_rps": max(r["throughput_rps"] for r in all_results),
            "worst_p95_ms": max(r["latency_ms"]["p95"] for r in all_results),
            "max_error_rate": max(r["error_rate_percent"] for r in all_results),
        },
    }

    with open("load_test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info("\n📊 Tổng kết:")
    logger.info("  Best throughput: %.1f req/s", output["summary"]["best_throughput_rps"])
    logger.info("  Worst P95: %.1f ms", output["summary"]["worst_p95_ms"])
    logger.info("  Max error rate: %.1f%%", output["summary"]["max_error_rate"])
    logger.info("Kết quả lưu tại: load_test_results.json")

    return output


if __name__ == "__main__":
    run_peak_hour_simulation()
 