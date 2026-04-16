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

### ✨ Tính năng nổi bật dành cho Khách hàng (Customer Portal)
Hệ thống nay đã cung cấp trải nghiệm hoàn chỉnh từ đầu đến cuối cho Khách Du Lịch trực tiếp trên Mobile App:
- **Dual-Login Thông Minh**: Khách và Nhân viên dùng chung 1 màn hình Đăng nhập duy nhất. Hệ thống quét tự động nhận diện cấp bậc để phân phối giao diện điều khiển.
- **Tải ảnh vé QR Off-line**: Khách hàng mua vé có thể xuất File QR dạng ảnh (.PNG) và hệ thống lưu tự động vào Thư viện điện thoại (Gallery) thông qua Native `FileProvider` và `MediaStore API`.
- **Tự phục vụ Khuôn Mặt (Self-Enrollment)**: Khách hàng tự nạp khuôn mặt bằng Camera Selfie điện thoại. Khuôn mặt được đẩy thẳng về Server AI xử lý để khách hàng tự tin đi qua cửa kiểm soát khuôn mặt mà không cần xuất trình vé giấy.

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
Check_ticket/
│
├── 📱 gate-app/                             # Android App (Nhân viên cổng) — Kotlin
│   └── app/src/main/
│       ├── AndroidManifest.xml
│       └── java/com/tourism/gate/
│           │   GateApplication.kt           # Application class
│           │
│           ├── ui/                          # Activities (màn hình)
│           │   ├── LoginActivity.kt         # Màn hình Đăng nhập Tự động Nhận diện (Nhân viên / Khách)
│           │   ├── customer/                # CỤM CHỨC NĂNG KHÁCH HÀNG
│           │   │   ├── CustomerRegisterActivity.kt  # Khách tạo tài khoản
│           │   │   └── CustomerDashboardActivity.kt # Lịch sử vé đã mua
│           │   ├── RoleSelectActivity.kt    # Chọn vai trò (Operator / Cashier)
│           │   ├── GateSelectActivity.kt    # Chọn cổng làm việc
│           │   ├── SelectDirectionActivity.kt # Chọn hướng IN / OUT
│           │   ├── ScanActivity.kt          # Quét QR (CameraX + ML Kit)
│           │   ├── FaceVerifyActivity.kt    # Xác thực khuôn mặt 1:1
│           │   ├── FaceEnrollActivity.kt    # Đăng ký khuôn mặt (multi-shot)
│           │   ├── QrDisplayActivity.kt     # Hiển thị mã QR vé
│           │   ├── SellTicketActivity.kt    # Bán vé tại cổng
│           │   ├── ManualSearchActivity.kt  # Tra cứu thủ công (SĐT / booking)
│           │   └── ResultActivity.kt        # Hiển thị kết quả check-in/out
│           │
│           ├── data/
│           │   ├── api/
│           │   │   ├── ApiService.kt        # Retrofit interface (các endpoint)
│           │   │   └── ApiClient.kt         # Base URL, header JWT, timeout
│           │   ├── model/
│           │   │   ├── CustomerModels.kt    # DTO Đăng ký / Đăng nhập của Khách
│           │   │   ├── Ticket.kt            # Model vé điện tử
│           │   │   ├── TicketModels.kt      # TicketIssueRequest/Response
│           │   │   ├── Identity.kt          # Model định danh (CCCD hash / booking)
│           │   │   ├── GateEvent.kt         # Model sự kiện IN/OUT
│           │   │   └── CheckinResult.kt     # Model kết quả check-in/out
│           │   └── local/
│           │       ├── OfflineCache.kt      # Room DB — cache vé theo ca trực
│           │       └── ShiftManager.kt      # Quản lý ca, đồng bộ nonce offline
│           │
│           ├── viewmodel/
│           │   ├── ScanViewModel.kt         # Logic quét QR, xử lý trạng thái
│           │   ├── FaceViewModel.kt         # Logic xác thực khuôn mặt
│           │   ├── ManualViewModel.kt       # Logic tra cứu thủ công
│           │   └── GateViewModel.kt         # Logic chọn cổng / ca trực
│           │
│           └── utils/
│               ├── QrParser.kt              # Parse và validate payload QR
│               ├── NetworkUtils.kt          # Detect offline/online, retry logic
│               └── QrBitmapUtils.kt         # Lưu vé QR ra dạng ảnh & Chia sẻ
│
├── 🌐 web-dashboard/                        # Website Admin (React + Vite)
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── pages/
│       │   ├── Login.jsx                    # Đăng nhập JWT (Admin / Kế toán)
│       │   ├── Dashboard.jsx                # Tổng quan realtime
│       │   ├── GateMonitor.jsx              # Giám sát từng cổng realtime
│       │   ├── Revenue.jsx                  # Doanh thu theo ngày / loại vé / kênh
│       │   ├── Visitors.jsx                 # Thống kê lượt khách
│       │   ├── AgeGroupAnalysis.jsx         # Phân tích cơ cấu nhóm tuổi
│       │   ├── Tickets.jsx                  # Quản lý vé (phát hành / huỷ)
│       │   ├── Reports.jsx                  # Xuất báo cáo CSV / PDF
│       │   └── UserManagement.jsx           # Quản lý tài khoản nhân viên
│       ├── components/
│       │   ├── AppLayout.jsx                # Layout chính (sidebar, header)
│       │   ├── RealtimeTable.jsx            # Bảng sự kiện check-in/out realtime
│       │   ├── GateStatusCard.jsx           # Thẻ trạng thái từng cổng
│       │   ├── ExportButton.jsx             # Nút xuất CSV / PDF
│       │   ├── DateRangePicker.jsx          # Bộ lọc khoảng thời gian
│       │   └── charts/
│       │       ├── PeakHourChart.jsx        # Biểu đồ giờ cao điểm
│       │       ├── ChannelPieChart.jsx      # Tỷ lệ kênh QR / Face / CCCD / Manual
│       │       ├── RevenueLineChart.jsx     # Doanh thu theo thời gian
│       │       ├── AgeGroupBarChart.jsx     # Cơ cấu khách theo nhóm tuổi
│       │       └── ErrorRateChart.jsx       # Tỷ lệ lỗi check-in/out
│       ├── services/
│       │   ├── api.js                       # Axios base config (JWT header)
│       │   └── websocket.js                 # Kết nối WebSocket / SSE realtime
│       ├── hooks/
│       │   ├── useWebSocket.js              # Hook nhận sự kiện realtime
│       │   └── useAuth.js                   # Hook quản lý JWT, role check
│       └── store/                           # Zustand global state
│           ├── authStore.js
│           ├── gateStore.js
│           └── reportStore.js
│
├── ⚙️ backend/                              # FastAPI Backend
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py                          # Khởi động FastAPI, đăng ký router
│       ├── core/
│       │   ├── config.py                    # ENV variables, settings
│       │   ├── security.py                  # JWT encode/decode, RBAC helper
│       │   └── database.py                  # Kết nối MongoDB (Motor async)
│       ├── api/
│       │   ├── auth.py                      # Login, refresh token, RBAC
│       │   ├── customer.py                  # API Cổng Khách Hàng (Tạo vé tự túc, Lịch sử mua, Get ảnh QR .png)
│       │   ├── tickets.py                   # Issue / validate / revoke vé
│       │   ├── checkin.py                   # Check-in/out endpoint (đa kênh)
│       │   ├── face_enroll.py               # Endpoint đăng ký khuôn mặt
│       │   ├── gates.py                     # Quản lý cổng
│       │   ├── reports.py                   # Doanh thu, lượt khách, export
│       │   └── websocket.py                 # WebSocket cho dashboard realtime
│       ├── models/                          # MongoDB Document Schema
│       │   └── __init__.py
│       ├── schemas/                         # Pydantic validate request/response
│       │   ├── auth.py                      # LoginRequest, TokenResponse
│       │   ├── customer.py                  # DTO Register, Khách hàng Portal
│       │   ├── ticket.py                    # TicketCreate, TicketResponse
│       │   ├── checkin.py                   # CheckinRequest, CheckinResult
│       │   └── report.py                    # RevenueQuery, VisitorStats
│       ├── services/
│       │   ├── channel_adapter.py           # Luồng check-in/out thống nhất (adapter pattern)
│       │   └── report_service.py            # Aggregation pipeline MongoDB cho báo cáo
│       ├── middleware/
│       │   └── audit.py                     # Tự động ghi audit_log mỗi request
│       └── tests/
│           ├── conftest.py                  # Pytest fixtures, test DB setup
│           ├── test_models.py               # Test MongoDB document models
│           ├── test_schemas.py              # Test Pydantic schema validation
│           ├── test_security.py             # Test JWT encode/decode, RBAC
│           └── test_channel_adapter.py      # Test luồng check-in/out đa kênh
│
└── 🤖 ai-services/                          # Dịch vụ AI độc lập
    ├── requirements.txt
    ├── Dockerfile
    ├── face_verification/
    │   ├── config.py                        # THRESHOLD, model path, cấu hình
    │   ├── detector.py                      # Detect khuôn mặt, crop vùng ROI
    │   ├── embedding.py                     # Trích xuất vector embedding từ ảnh
    │   ├── similarity.py                    # Cosine similarity giữa 2 embedding
    │   ├── face_service.py                  # API nội bộ: nhận 2 ảnh → True/False + score
    │   ├── privacy_guard.py                 # Không lưu ảnh gốc, chỉ lưu embedding
    │   └── models/
    │       ├── yunet_face_detect.onnx       # Model detect & crop khuôn mặt (YuNet)
    │       ├── download_model.py            # Script tải model tự động
    │       └── buffalo_l/                   # InsightFace buffalo_l (ArcFace R50)
    │           ├── det_10g.onnx             # Face detector
    │           ├── w600k_r50.onnx           # Face recognition (embedding 512-d)
    │           ├── 2d106det.onnx            # 2D landmark 106 điểm
    │           ├── 1k3d68.onnx              # 3D landmark 68 điểm
    │           └── genderage.onnx           # Dự đoán giới tính và tuổi
    ├── qr_generator/
    │   ├── qr_service.py                    # Tạo QR payload + ký RS256
    │   ├── nonce_store.py                   # Anti-reuse: lưu nonce đã dùng
    │   ├── time_window.py                   # Kiểm tra QR còn hiệu lực
    │   └── keys/
    │       ├── private.pem                  # Private key ký QR  ← GITIGNORE!
    │       └── public.pem                   # Public key verify
    ├── id_service/
    │   ├── id_hash_service.py               # SHA-256 hash CCCD/ID, không lưu ảnh gốc
    │   └── booking_lookup.py                # Tra cứu theo booking ID / SĐT
    └── eval/                                # Script đánh giá & kết quả thực nghiệm
        ├── test_far_frr.py                  # Tính FAR / FRR với data mô phỏng
        ├── test_qr_fraud.py                 # Test phát hiện vé giả / đã dùng
        ├── test_load_simulation.py          # Mô phỏng tải theo giờ cao điểm
        ├── eval_results.json                # Kết quả đánh giá FAR/FRR
        ├── qr_fraud_results.json            # Kết quả kiểm thử chống gian lận QR
        └── load_test_results.json           # Kết quả kiểm thử tải
```

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Android App | Kotlin, Retrofit2, CameraX, ML Kit (QR scan), Room DB |
| Backend | FastAPI, Motor (async MongoDB), JWT, Pydantic |
| Database | MongoDB |
| AI - Face | ONNX Runtime, InsightFace buffalo_l (ArcFace R50), YuNet |
| AI - QR | RS256 (python-jose), nonce anti-replay |
| Web Dashboard | React, Vite, Recharts, Axios, Zustand |
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
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| AI Services | http://localhost:8001 |
| Web Dashboard | http://localhost:3000 |
| MongoDB | localhost:27017 |

---

### 2. Backend (FastAPI) — chạy độc lập

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 3. AI Services — chạy độc lập

```bash
cd ai-services
pip install -r requirements.txt
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
2. Mở file `app/build.gradle` điền IP máy chứa backend vào: `buildConfigField "String", "BASE_URL", '"http://<your-ip>:8000/"'`
3. Nhấn **Sync Project with Gradle Files**.
4. Kết nối thiết bị **Android thật** (Đảm bảo gọi chung mạng WiFi với laptop).
5. Nhấn **Run ▶** để build App vào điện thoại.

---

### 🚀 Mẹo Deploy (Triển khai hệ thống) tiết kiệm chi phí nhất

Với tính chất đồ án cần xử lý AI nặng nhưng không có tài chính thuê Server VPS có Card đồ hoạ/RAM lớn, kiến trúc đặc biệt của *Tourism Gate* hỗ trợ **Mô hình triển khai chéo (Hybrid Deployment)** để giải quyết vấn đề này 100% miễn phí:

1. **Host App & Code Web lên Cloud**: Đẩy Backend (`/backend`) và Dashboard (`/web-dashboard`) lên các nền tảng Free Tier mượt mà (VD: `Render`, `Vercel`). Các dịch vụ này dù RAM thấp (512MB) vẫn đáp ứng thừa sức các tính năng bán vé và Socket Realtime.
2. **Sử dụng Laptop làm Trạm xử lý AI**: Vì `ai-services` nặng vài GB RAM, hãy bật nó cục bộ (localhost) ngay trên chiếc Laptop của bạn.
3. **Mở luồng Internet (Tunnel) bằng Ngrok**: Chạy `ngrok http 8001` tại Laptop để lấy đường dẫn Internet HTTPS trỏ vào mạng LAN. Dán đường dẫn này làm cấu hình `AI_SERVICE_URL` trên server Backend mĩ (Render).
→ 🎯 Giao diện người dùng Web + App sẽ phản hồi tốc độ tên lửa, trong khi AI model mạnh mẽ được cõng hoàn toàn miễn phí bởi máy cá nhân.

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

### Face Enroll

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/face/enroll` | Đăng ký khuôn mặt (multi-shot) |

### Reports

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/reports/revenue` | Doanh thu theo ngày / loại vé |
| GET | `/api/reports/visitors` | Lượt vào/ra theo cổng / kênh |
| GET | `/api/reports/export` | Xuất CSV |

---

## Tài khoản demo

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Nhân viên cổng | `staff_gate1` | `staff123` |
| Kế toán | `accountant` | `acc123` |
| Khách hàng trải nghiệm | *Mở app lên, chọn "ĐĂNG KÝ" để tự nhập Account* | *Bạn tự cấu hình lúc đăng ký* |

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
