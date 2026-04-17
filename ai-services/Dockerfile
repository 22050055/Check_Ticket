FROM python:3.11-slim

WORKDIR /app

# Cài system dependencies cho OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Cài Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Tạo thư mục models (mount volume khi chạy)
RUN mkdir -p face_verification/models qr_generator/keys

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# Chạy face service (service chính)
CMD ["uvicorn", "face_verification.face_service:app", \
     "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
 