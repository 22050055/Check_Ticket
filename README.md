# 🏖️ Tourism Access Control System

> **Phát triển hệ thống kiểm soát ra/vào khu du lịch đa kênh dựa trên QR và xác thực định danh, tích hợp Dashboard phân tích vận hành**

---

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Hướng dẫn cài đặt](#hướng-dẫn-cài-đặt)
- [Hướng dẫn chạy từng phần](#hướng-dẫn-chạy-từng-phần)
- [API Reference](#api-reference)
- [Tài khoản demo](#tài-khoản-demo)
- [Ghi chú pháp lý](#ghi-chú-pháp-lý)

---

## Tổng quan

Hệ thống hỗ trợ **4 kênh xác thực** tại cổng ra/vào khu du lịch:

| Kênh | Mô tả | Bắt buộc |
|------|-------|----------|
| QR e-ticket | Quét mã QR ký số RS256, chống giả, chống dùng lại | ✅ |
| Face Verify 1:1 | So khớp khuôn mặt với ảnh đăng ký (opt-in) | Tùy chọn |
| CCCD / Booking ID | Tra cứu theo hash CCCD hoặc mã đặt vé | Tùy chọn |
| Manual Fallback | Tra cứu theo SĐT / tên khách | Dự phòng |

---

## Kiến trúc hệ thống

```
┌─────────────────┐        REST API (JWT)       ┌──────────────────┐
│  Android Gate   │ ─────────────────────────►  │                  │
│     App         │                             │   FastAPI        │
│  (Nhân viên     │ ◄─────────────────────────  │   Backend        │
│   cổng)         │        JSON Response        │                  │
└─────────────────┘                             └────────┬─────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │      MongoDB         │
                                              │  (vé, log, giao      │
                                              │   dịch, khách)       │
                                              └──────────┬──────────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │   AI Services        │
                                              │  (Face + QR verify)  │
                                              └──────────┬──────────┘
                                                         │ WebSocket/SSE
                                              ┌──────────▼──────────┐
                                              │   Web Dashboard      │
                                              │  (Admin/Kế toán)     │
                                              └─────────────────────┘
```

---

## Cấu trúc dự án

```
tourism-access-control/
│
├── 📱 gate-app/                             # Android App (Nhân viên cổng)
│   └── app/src/main/
│       ├── java/com/tourism/gate/
│       │   ├── ui/
│       │   │   ├── LoginActivity.kt         # Đăng nhập nhân viên
│       │   │   ├── GateSelectActivity.kt    # Chọn cổng làm việc
│       │   │   ├── SelectDirectionActivity.kt # Chọn hướng IN / OUT
│       │   │   ├── ScanActivity.kt          # Quét QR
│       │   │   ├── FaceVerifyActivity.kt    # Chụp ảnh xác thực khuôn mặt 1:1
│       │   │   ├── ResultActivity.kt        # Hiển thị kết quả hợp lệ / không hợp lệ
│       │   │   └── ManualSearchActivity.kt  # Tra cứu thủ công (SĐT / booking)
│       │   ├── data/
│       │   │   ├── api/
│       │   │   │   ├── ApiService.kt        # Retrofit interface (các endpoint)
│       │   │   │   └── ApiClient.kt         # Base URL, header JWT, timeout
│       │   │   ├── model/
│       │   │   │   ├── Ticket.kt            # Model vé điện tử
│       │   │   │   ├── Identity.kt          # Model định danh (CCCD hash / booking)
│       │   │   │   ├── GateEvent.kt         # Model sự kiện IN/OUT
│       │   │   │   └── CheckinResult.kt     # Model kết quả check-in/out
│       │   │   └── local/
│       │   │       ├── OfflineCache.kt      # Room DB cache vé theo ca trực
│       │   │       └── ShiftManager.kt      # Quản lý ca, đồng bộ nonce offline
│       │   ├── viewmodel/
│       │   │   ├── ScanViewModel.kt         # Logic quét QR
│       │   │   ├── FaceViewModel.kt         # Logic xác thực khuôn mặt
│       │   │   ├── ManualViewModel.kt       # Logic tra cứu thủ công
│       │   │   └── GateViewModel.kt         # Logic chọn cổng / ca trực
│       │   └── utils/
│       │       ├── QrParser.kt             # Parse payload QR
│       │       └── NetworkUtils.kt         # Detect offline / online, retry
│       └── res/layout/
│           ├── activity_login.xml
│           ├── activity_scan.xml
│           ├── activity_face_verify.xml
│           ├── activity_result.xml
│           └── activity_manual_search.xml
│
├── 🌐 web-dashboard/                        # Website Admin (React)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx                   # Đăng nhập JWT (Admin / Kế toán)
│   │   │   ├── Dashboard.jsx               # Tổng quan realtime
│   │   │   ├── GateMonitor.jsx             # Giám sát từng cổng realtime
│   │   │   ├── Revenue.jsx                 # Doanh thu theo ngày / loại vé / kênh
│   │   │   ├── Visitors.jsx                # Thống kê lượt khách
│   │   │   ├── AgeGroupAnalysis.jsx        # Phân tích cơ cấu nhóm tuổi
│   │   │   ├── Tickets.jsx                 # Quản lý vé (phát hành / huỷ)
│   │   │   ├── CustomerManagement.jsx      # Quản lý khách hàng
│   │   │   └── Reports.jsx                 # Xuất báo cáo CSV / PDF
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── PeakHourChart.jsx       # Biểu đồ giờ cao điểm
│   │   │   │   ├── ChannelPieChart.jsx     # Tỷ lệ kênh QR / Face / CCCD / Manual
│   │   │   │   ├── RevenueLineChart.jsx    # Doanh thu theo thời gian
│   │   │   │   ├── AgeGroupBarChart.jsx    # Cơ cấu khách theo nhóm tuổi
│   │   │   │   └── ErrorRateChart.jsx      # Tỷ lệ lỗi check-in/out
│   │   │   ├── RealtimeTable.jsx           # Bảng sự kiện check-in/out realtime
│   │   │   ├── GateStatusCard.jsx          # Thẻ trạng thái từng cổng
│   │   │   ├── ExportButton.jsx            # Nút xuất CSV / PDF
│   │   │   └── DateRangePicker.jsx         # Bộ lọc khoảng thời gian
│   │   ├── services/
│   │   │   ├── api.js                      # Axios base config (JWT header)
│   │   │   └── websocket.js               # Kết nối WebSocket / SSE realtime
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js            # Hook nhận sự kiện realtime
│   │   │   └── useAuth.js                 # Hook quản lý JWT, role check
│   │   └── store/                         # Redux / Zustand (global state)
│   │       ├── authStore.js
│   │       ├── gateStore.js
│   │       └── reportStore.js
│   ├── package.json
│   ├── Dockerfile                  # Build image cho Dashboard (Nginx) [NEW]
│   └── nginx.conf                  # Cấu hình proxy API cho Dashboard [NEW]
│
├── ⚙️ backend/                              # FastAPI Backend
│   ├── app/
│   │   ├── main.py                         # Khởi động FastAPI, đăng ký router
│   │   ├── core/
│   │   │   ├── config.py                   # ENV variables, settings
│   │   │   ├── security.py                 # JWT encode/decode, RBAC helper
│   │   │   └── database.py                 # Kết nối MongoDB (Motor async)
│   │   ├── api/
│   │   │   ├── auth.py                     # Login, refresh token, RBAC
│   │   │   ├── tickets.py                  # Issue / validate / revoke / hoàn huỷ vé
│   │   │   ├── checkin.py                  # Check-in/out endpoint thống nhất (đa kênh)
│   │   │   ├── gates.py                    # Quản lý cổng
│   │   │   ├── reports.py                  # Doanh thu, lượt khách, channel usage, export
│   │   │   ├── customer.py                 # API Khách hàng & Mua vé online [NEW]
│   │   │   └── websocket.py                # WebSocket endpoint cho dashboard realtime
│   │   ├── models/                         # MongoDB Document Schema (Beanie ODM)
│   │   │   ├── customer.py                 # Collection: customers
│   │   │   ├── identity.py                 # Collection: identities (qr/booking/phone/id_hash/face_embedding)
│   │   │   ├── ticket.py                   # Collection: tickets
│   │   │   ├── transaction.py              # Collection: transactions (doanh thu)
│   │   │   ├── gate.py                     # Collection: gates
│   │   │   ├── gate_event.py               # Collection: gate_events (IN/OUT log)
│   │   │   └── audit_log.py                # Collection: audit_logs
│   │   ├── schemas/                        # Pydantic validate request / response
│   │   │   ├── auth.py                     # LoginRequest, TokenResponse
│   │   │   ├── ticket.py                   # TicketCreate, TicketResponse
│   │   │   ├── checkin.py                  # CheckinRequest, CheckinResult
│   │   │   ├── gate.py                     # GateCreate, GateResponse
│   │   │   ├── customer.py                 # Customer schemas [NEW]
│   │   │   └── report.py                   # RevenueQuery, VisitorStats
│   │   ├── services/
│   │   │   ├── qr_service.py               # Gọi qr_generator: tạo & verify QR
│   │   │   ├── face_service.py             # Gọi ai-services: face verify 1:1
│   │   │   ├── channel_adapter.py          # Luồng check-in/out thống nhất (adapter pattern)
│   │   │   └── report_service.py           # Aggregation pipeline MongoDB cho báo cáo
│   │   ├── middleware/
│   │   │   ├── rbac.py                     # Phân quyền: Admin / NV cổng / Kế toán
│   │   │   └── audit_middleware.py         # Tự động ghi audit_log mỗi request
│   │   └── tests/                          # Phục vụ Chương 4 thực nghiệm
│   │       ├── test_checkin.py             # Test check-in/out 4 kênh
│   │       ├── test_qr_fraud.py            # Test phát hiện vé giả / đã dùng
│   │       └── test_load.py                # Test tải mô phỏng giờ cao điểm
│   ├── requirements.txt
│   └── Dockerfile
│
├── 🤖 ai-services/                          # Dịch vụ AI độc lập
│   ├── face_verification/
│   │   ├── models/
│   │   │   ├── facenet_512.onnx            # Model trích xuất embedding khuôn mặt
│   │   │   └── yunet_face_detect.onnx      # Model detect & crop khuôn mặt
│   │   ├── detector.py                     # Detect khuôn mặt, crop vùng ROI
│   │   ├── embedding.py                    # Trích xuất vector 512-d từ ảnh
│   │   ├── similarity.py                   # Cosine similarity giữa 2 embedding
│   │   ├── config.py                       # THRESHOLD = 0.6, model path
│   │   ├── face_service.py                 # API nội bộ: nhận 2 ảnh → True/False + score
│   │   └── privacy_guard.py               # Không lưu ảnh gốc, chỉ lưu embedding
│   ├── qr_generator/
│   │   ├── qr_service.py                   # Tạo QR payload + ký RS256
│   │   ├── nonce_store.py                  # Anti-reuse: lưu nonce đã dùng (MongoDB)
│   │   ├── time_window.py                  # Kiểm tra QR còn hiệu lực (time-window)
│   │   └── keys/
│   │       ├── private.pem                 # Private key ký QR  ← GITIGNORE!
│   │       └── public.pem                  # Public key verify
│   ├── id_service/
│   │   ├── id_hash_service.py              # SHA-256 hash CCCD/ID, không lưu ảnh gốc
│   │   └── booking_lookup.py              # Tra cứu theo booking ID / SĐT
│   ├── eval/                               # Script đánh giá Chương 4
│   │   ├── test_far_frr.py                 # Tính FAR / FRR với data mô phỏng
│   │   ├── test_qr_fraud.py                # Test phát hiện vé giả / đã dùng
│   │   ├── test_load_simulation.py         # Mô phỏng tải theo giờ cao điểm
│   │   └── sample_images/                  # Ảnh mẫu cho demo FAR/FRR
│   └── Dockerfile
│
├── 🐳 docker-compose.yml                   # Gom toàn bộ services
├── .env.example                            # Mẫu biến môi trường
├── .gitignore                              # Bỏ qua key, .env, __pycache__
├── README.md                               # File này
└── docs/
    ├── huong-dan-cai-dat.md               # Hướng dẫn cài đặt chi tiết
    ├── api-reference.md                    # Tài liệu API endpoint
    └── architecture-diagram.png           # Sơ đồ kiến trúc
```

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Android App | Kotlin, Retrofit2, CameraX, ML Kit (QR scan), Room DB |
| Backend | FastAPI, Beanie ODM, Motor (async), JWT, Pydantic |
| Database | MongoDB |
| AI - Face | ONNX Runtime, FaceNet-512, YuNet (OpenCV) |
| AI - QR | RS256 (python-jose), HMAC-SHA256 |
| Web Dashboard | React, Recharts, Ant Design, Axios |
| Realtime | WebSocket (FastAPI native) |
| Deploy | Docker, Docker Compose |

---

## Hướng dẫn cài đặt

### Yêu cầu

- Docker & Docker Compose
- Android Studio (Hedgehog trở lên)
- Node.js >= 18
- Python >= 3.10

### Clone dự án

```bash
git clone https://github.com/<your-username>/tourism-access-control.git
cd tourism-access-control
```

### Cấu hình môi trường

```bash
cp .env.example .env
# Chỉnh sửa .env theo môi trường của bạn
```

Nội dung `.env.example`:

```env
# MongoDB
MONGO_URI=mongodb://mongo:27017
MONGO_DB=tourism_db

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI Services
FACE_THRESHOLD=0.6
FACE_SERVICE_URL=http://ai-services:8001
QR_PRIVATE_KEY_PATH=./ai-services/qr_generator/keys/private.pem
QR_PUBLIC_KEY_PATH=./ai-services/qr_generator/keys/public.pem

# App
BACKEND_URL=http://localhost:8000
```

### Tạo RSA Key cho QR

```bash
cd ai-services/qr_generator/keys
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

---

## Hướng dẫn chạy từng phần

### 1. Chạy toàn bộ bằng Docker Compose

```bash
docker-compose up --build
```

Các service sẽ chạy tại:

| Service | URL |
|---------|-----|
| **Web Dashboard** | [http://localhost:3000](http://localhost:3000) |
| **Backend API** | [http://localhost:8000](http://localhost:8000) |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **AI Services** | [http://localhost:8001](http://localhost:8001) |
| **MongoDB (Local)** | `localhost:27017` |

> [!NOTE]
> Khi chạy bằng Docker Compose, dữ liệu được lưu tại thư mục `./mongodb_data`.

---

### 2. Backend (FastAPI) — chạy độc lập

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
---

### 3. AI Services — chạy độc lập

```bash
cd ai-services
pip install -r face_verification/requirements.txt
uvicorn face_verification.face_service:app --reload --port 8001
```

---

### 4. Web Dashboard — chạy độc lập

```bash
cd web-dashboard
npm install
npm run dev
# Chạy tại http://localhost:3000
```

---

### 5. Android Gate App

1. Mở Android Studio → **Open** → chọn thư mục `gate-app/`
2. Sửa `ApiClient.kt`, đặt `BASE_URL = "http://<your-ip>:8000/"`
3. Kết nối thiết bị Android hoặc dùng Emulator
4. Nhấn **Run ▶**

---

## API Reference

### Auth

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/auth/login` | Đăng nhập, trả về access_token |
| POST | `/api/auth/refresh` | Làm mới token |

### Tickets

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/tickets/issue` | Phát hành vé điện tử QR |
| POST | `/api/tickets/validate` | Xác thực vé |
| PUT | `/api/tickets/{id}/revoke` | Huỷ vé |
| POST | `/api/customer/buy-ticket` | Khách tự mua vé online |

### Customers (Admin)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/customer/all` | Danh sách toàn bộ khách hàng |
| PATCH | `/api/customer/{id}` | Cập nhật thông tin khách |
| DELETE | `/api/customer/{id}` | Xóa tài khoản khách |

### Check-in / Out

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/checkin` | Check-in/out (tất cả kênh) |

Body mẫu:
```json
{
  "channel": "qr",
  "direction": "IN",
  "gate_id": "gate_01",
  "qr_payload": "eyJ...",
  "face_image_b64": null
}
```

### Reports

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/reports/revenue` | Doanh thu theo ngày / loại vé |
| GET | `/api/reports/visitors` | Lượt vào/ra theo cổng / kênh |
| GET | `/api/reports/export` | Xuất CSV |

---

## Tài khoản demo

### 🌐 Web Dashboard & App (Nhân viên)
**Link truy cập:** [https://fc439656.tourism-dashboard.pages.dev/login](https://fc439656.tourism-dashboard.pages.dev/login)

| Quyền | Tài khoản | Mật khẩu |
|-------|-----------|----------|
| **Admin** | `admin` | `admin123` |
| **Quản lý (Manager)** | `manager1` | `manager123` |
| **Vận hành (Operator)** | `operator1` | `operator123` |
| **Vận hành (Operator)** | `operator2` | `operator123` |
| **Bán vé (Cashier)** | `cashier1` | `cashier123` |

### 📱 App (Khách hàng tự mua vé)
| Loại | Email | Mật khẩu |
|------|-------|----------|
| **Khách hàng** | `22050055@student.bdu.edu.vn` | `123456` |

---

## Triển khai (Deployment)

### ⚙️ Backend (Render)
Dự án được cấu hình để deploy tự động lên **Render** thông qua Dockerfile.
- Cần cấu hình biến môi trường: `MONGO_URI`, `AI_SERVICE_URL`, `CORS_ORIGINS`.

### 🌐 Web Dashboard (Cloudflare Pages)
- **Root Directory**: `web-dashboard`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variables**: Thêm `VITE_API_URL` trỏ về Backend Render.

---

## Ghi chú pháp lý

> ⚠️ Hệ thống tuân thủ các nguyên tắc bảo vệ dữ liệu cá nhân:

- **CCCD / ID:** Chỉ lưu hash SHA-256, không lưu số CCCD gốc, không lưu ảnh CCCD.
- **Khuôn mặt:** Chỉ lưu vector embedding, không lưu ảnh gốc. Triển khai theo cơ chế **opt-in** từ khách.
- **Face Verification:** Chỉ ở mức **1:1 (verification)**, không nhận diện đại trà 1:N.
- **Mục đích:** Hệ thống phục vụ vận hành và báo cáo, không sử dụng cho mục đích giám sát hoặc xâm phạm quyền riêng tư.

---

## Nhóm thực hiện

| Họ tên | MSSV | Vai trò |
|--------|------|---------|
| Mạnh Khang | ... | Phát triển toàn hệ thống |

**Giảng viên hướng dẫn:** ...

**Trường:** ...

---

*Đồ án tốt nghiệp — Hệ thống kiểm soát ra/vào khu du lịch đa kênh*
