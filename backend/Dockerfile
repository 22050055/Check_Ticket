# ══════════════════════════════════════════════════════════════
# Tourism Access Control — Backend Dockerfile
# Base: python:3.11-slim
# Port: 8000
# ══════════════════════════════════════════════════════════════

# ── Stage: build dependencies ─────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Cài build tools (một số package cần compile C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Cài vào thư mục riêng để copy sang stage final
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage: runtime (nhỏ gọn, không có build tools) ────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Chỉ cài runtime libs cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy packages đã cài từ builder
COPY --from=builder /install /usr/local

# ── Non-root user (security best practice) ────────────────────
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy source code
COPY --chown=appuser:appuser . .

# Đổi sang non-root user
USER appuser

# Port
EXPOSE 8000

# ── Health check ──────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Startup ───────────────────────────────────────────────────
# Số workers lấy từ env WEB_CONCURRENCY (default=2)
# Production: set WEB_CONCURRENCY=4 hoặc dùng gunicorn
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2}"]
 