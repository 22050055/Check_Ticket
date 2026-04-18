# 🏖️ Tourism Access Control System

> **Phát triển hệ thống kiểm soát ra/vào khu du lịch đa kênh dựa trên QR và xác thực định danh, tích hợp Dashboard phân tích vận hành**
>
> Đồ án Tốt nghiệp — Trần Mạnh Khang

---

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Triển khai (Deployment)](#triển-khai-deployment)
- [Hướng dẫn chạy Local](#hướng-dẫn-chạy-local)
- [API Reference](#api-reference)
- [Tài khoản demo](#tài-khoản-demo)
- [Ghi chú pháp lý](#ghi-chú-pháp-lý)

---

## Tổng quan

Hệ thống hỗ trợ **4 kênh xác thực** tại cổng ra/vào khu du lịch:

| Kênh | Mô tả | Bắt buộc |
|------|-------|----------|
| QR e-ticket | Quét mã QR ký số RS256, chống giả, chống dùng lại (nonce) | ✅ |
| Face Verify 1:1 | So khớp khuôn mặt với embedding đã đăng ký (ArcFace) | Tùy chọn (opt-in) |
| Identity Hash | Tra cứu theo hash CCCD hoặc mã đặt vé (Booking ID) | Tùy chọn |
| Manual Fallback | Tra cứu thủ công theo SĐT / tên khách | Dự phòng |

**Đặc điểm nổi bật:**
- **Dual App**: Ứng dụng Android dành riêng cho **Nhân viên cổng** (quét vé) và **Khách hàng** (mua vé, xem vé, đăng ký khuôn mặt).
- **AI On-Premise**: AI Service chạy độc lập (localhost/Ngrok) với mô hình **ArcFace buffalo_l** (State-of-the-Art, ONNX Runtime GPU).
- **Audit Trail**: Mọi action đều bị ghi lại `audit_log` với thông tin user, IP, thời gian, response status.
- **Staff Presence**: Theo dõi trạng thái Online/Offline của nhân viên thời gian thực qua WebSocket.
- **Customer Feedback**: Hệ thống đánh giá 1-5 sao cho vé đã sử dụng.

---

## Kiến trúc hệ thống

```
┌─────────────────────┐         REST API (JWT)        ┌──────────────────────┐
│  Android Gate App   │ ──────────────────────────►   │                      │
│  (Nhân viên cổng)   │                               │   FastAPI Backend     │
│  ─────────────────  │ ◄──────────────────────────   │   (Render Cloud)     │
│  Android Customer   │       JSON Response            │                      │
│  App (Khách hàng)   │                               └───────────┬──────────┘
└─────────────────────┘                                           │
                                                      ┌───────────▼──────────┐
┌─────────────────────┐                               │     MongoDB Atlas     │
│  Web Dashboard      │ ──── REST API / WebSocket ──► │  (vé, log, giao dịch,│
│  (Admin / Kế toán)  │                               │   khách, identities) │
│  Cloudflare Pages   │                               └──────────────────────┘
└─────────────────────┘
                                                      ┌──────────────────────┐
                                                      │   AI Services        │
                                                      │  (Local + Ngrok)     │
                                                      │  ArcFace buffalo_l   │
                                                      │  QR RS256 Verifier   │
                                                      └──────────────────────┘
```

> [!IMPORTANT]
> Backend gọi AI Service qua biến `AI_SERVICE_URL` (cấu hình trên Render). Khi demo local: chạy AI Service → expose qua Ngrok → cập nhật URL trên Render.

---

## Cấu trúc dự án

```
Check_ticket/
│
├── 📱 gate-app/                              # Android App (Kotlin)
│   └── app/src/main/java/com/tourism/gate/
│       ├── ui/
│       │   ├── LoginActivity.kt              # Đăng nhập — chọn vai trò Staff / Customer
│       │   ├── RoleSelectActivity.kt         # Chọn vai trò vận hành
│       │   ├── GateSelectActivity.kt         # Chọn cổng làm việc
│       │   ├── SelectDirectionActivity.kt    # Chọn hướng IN / OUT
│       │   ├── ScanActivity.kt               # Quét QR (ZXing) + chụp khuôn mặt
│       │   ├── FaceEnrollActivity.kt         # Đăng ký khuôn mặt (3 mẫu)
│       │   ├── FaceVerifyActivity.kt         # Xác thực khuôn mặt tại cổng (1:1)
│       │   ├── ResultActivity.kt             # Hiển thị kết quả HỢP LỆ / KHÔNG HỢP LỆ
│       │   ├── ManualSearchActivity.kt       # Tra cứu thủ công (SĐT / booking)
│       │   ├── SellTicketActivity.kt         # Bán vé tại quầy (Nhân viên)
│       │   ├── QrDisplayActivity.kt          # Hiển thị QR Code cho khách
│       │   └── customer/                     # Luồng App Khách hàng (Bottom Nav)
│       │       ├── CustomerWelcomeActivity.kt
│       │       ├── CustomerRegisterActivity.kt
│       │       ├── CustomerDashboardActivity.kt
│       │       ├── CustomerBuyTicketActivity.kt
│       │       ├── CustomerTicketAdapter.kt
│       │       ├── HomeFragment.kt
│       │       ├── TicketsFragment.kt        # Xem vé, hiển thị QR
│       │       ├── BuyFragment.kt            # Mua vé online
│       │       └── ProfileFragment.kt        # Chỉnh sửa hồ sơ, đăng ký Face ID
│       ├── data/api/
│       │   ├── ApiService.kt                 # Retrofit interface — định nghĩa endpoint
│       │   └── ApiClient.kt                  # Base URL, JWT header, timeout
│       ├── data/model/                       # Data class Kotlin
│       └── viewmodel/                        # ViewModel cho từng màn hình
│
├── 🌐 web-dashboard/                         # Web Admin (React + Vite)
│   └── src/
│       ├── pages/
│       │   ├── Login.jsx                     # Đăng nhập JWT
│       │   ├── Dashboard.jsx                 # Tổng quan realtime
│       │   ├── GateMonitor.jsx               # Giám sát từng cổng realtime
│       │   ├── Revenue.jsx                   # Doanh thu theo ngày / loại vé / kênh
│       │   ├── Visitors.jsx                  # Thống kê lượt khách
│       │   ├── AgeGroupAnalysis.jsx          # Phân tích cơ cấu nhóm tuổi
│       │   ├── Tickets.jsx                   # Quản lý vé (phát hành / huỷ)
│       │   ├── CustomerManagement.jsx        # Quản lý khách hàng
│       │   ├── UserManagement.jsx            # Quản lý tài khoản nhân viên
│       │   ├── Reviews.jsx                   # Xem đánh giá từ khách hàng
│       │   └── Reports.jsx                   # Xuất báo cáo CSV
│       ├── components/                       # Biểu đồ, bảng, filter dùng lại
│       ├── services/api.js                   # Axios base config (JWT header)
│       ├── hooks/                            # useAuth, useWebSocket
│       └── store/                            # Zustand global state
│
├── ⚙️ backend/                               # FastAPI Backend
│   └── app/
│       ├── main.py                           # Khởi động FastAPI, router, lifespan
│       ├── core/
│       │   ├── config.py                     # ENV variables (Pydantic Settings)
│       │   ├── security.py                   # JWT HS256, RBAC helper
│       │   └── database.py                   # MongoDB Motor async + indexes
│       ├── api/
│       │   ├── auth.py                       # Login, refresh token
│       │   ├── tickets.py                    # Phát hành / validate / huỷ vé
│       │   ├── checkin.py                    # Endpoint check-in/out thống nhất
│       │   ├── gates.py                      # Quản lý cổng
│       │   ├── reports.py                    # Doanh thu, lượt khách, export CSV
│       │   ├── customer.py                   # API Khách hàng: mua vé, hồ sơ, đánh giá
│       │   ├── face_enroll.py                # Đăng ký khuôn mặt (3–5 mẫu)
│       │   ├── review.py                     # API đánh giá vé
│       │   └── websocket.py                  # WebSocket: Staff Presence + Event push
│       ├── services/
│       │   ├── channel_adapter.py            # Adapter xử lý 4 kênh check-in/out
│       │   ├── report_service.py             # MongoDB Aggregation Pipeline
│       │   └── qr_image_service.py           # Render ảnh QR từ payload
│       └── middleware/
│           ├── rbac.py                       # Phân quyền: Admin / Operator / Cashier
│           └── audit_middleware.py           # Tự động ghi audit_log mỗi request
│
├── 🤖 ai_services/                           # AI Service độc lập (chạy local)
│   ├── face_verification/
│   │   ├── models/
│   │   │   ├── buffalo_l/
│   │   │   │   ├── w600k_r50.onnx            # ArcFace R50 — embedding 512-d
│   │   │   │   ├── det_10g.onnx              # RetinaFace — detect khuôn mặt
│   │   │   │   └── genderage.onnx            # Dự đoán tuổi/giới tính (Dashboard)
│   │   │   └── yunet_face_detect.onnx        # Fallback detector (OpenCV)
│   │   ├── config.py                         # FACE_THRESHOLD (load từ .env)
│   │   ├── detector.py                       # Detect + aligned crop 112×112
│   │   ├── embedding.py                      # ArcFace ONNX inference → 512-d vector
│   │   ├── similarity.py                     # Cosine similarity, is_same_person_multi
│   │   ├── face_service.py                   # FastAPI endpoints: /enroll, /verify
│   │   └── privacy_guard.py                  # Không lưu ảnh gốc, chỉ lưu embedding
│   ├── qr_generator/
│   │   ├── qr_service.py                     # Tạo QR payload + ký RS256
│   │   └── keys/
│   │       ├── private.pem                   # Private key ký QR ← GITIGNORE
│   │       └── public.pem                    # Public key verify
│   ├── id_service/                           # Hash CCCD / tra cứu booking
│   ├── .env                                  # FACE_THRESHOLD=0.60
│   └── requirements.txt
│
├── 🐳 docker-compose.yml                     # Stack local đầy đủ
├── .gitignore
└── README.md
```

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| **Android App** | Kotlin, Retrofit2, CameraX, ZXing (QR), Bottom Navigation |
| **Backend** | FastAPI, Motor (async MongoDB), JWT HS256, Pydantic v2 |
| **Database** | MongoDB Atlas (Cloud, Free Tier M0) |
| **AI - Khuôn mặt** | ArcFace w600k_r50 + RetinaFace det_10g (InsightFace buffalo_l), ONNX Runtime GPU |
| **AI - QR** | RS256 ký số (python-jose), Nonce anti-reuse |
| **Web Dashboard** | React + Vite, Recharts, Axios, Zustand |
| **Realtime** | WebSocket (Staff Presence + Gate Event push) |
| **Deploy** | Render (Backend), Cloudflare Pages (Web), Ngrok (AI local tunnel) |

---

## Triển khai (Deployment)

### ⚙️ Backend — Render
- **URL:** *(Xem riêng — không public)*
- **Build:** Auto-deploy từ GitHub `main` branch qua Dockerfile.
- **Biến môi trường cần thiết trên Render:**

| Biến | Giá trị |
|------|---------|
| `MONGO_URI` | `mongodb+srv://<user>:{password}@<cluster>.mongodb.net/?appName=<app>` |
| `MONGO_PASSWORD` | *(password MongoDB — xem riêng)* |
| `JWT_SECRET` | *(chuỗi ngẫu nhiên 32+ ký tự)* |
| `AI_SERVICE_URL` | URL Ngrok đang chạy, VD: `https://xxxx.ngrok-free.app` |
| `QR_PRIVATE_KEY` | Nội dung file `private.pem` (paste trực tiếp) |
| `QR_PUBLIC_KEY` | Nội dung file `public.pem` (paste trực tiếp) |

### 🌐 Web Dashboard — Cloudflare Pages
- **URL:** *(Xem riêng — không public)*
- **Root Directory:** `web-dashboard`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Biến môi trường:** `VITE_API_URL=https://<backend-url>`

### 🤖 AI Service — Local + Ngrok
```bash
# 1. Chạy AI Service
cd ai_services
python -m face_verification.face_service
# → http://localhost:8001

# 2. Expose qua Ngrok
./ngrok http 8001
# Lấy URL dạng https://xxxx.ngrok-free.app → cập nhật AI_SERVICE_URL trên Render
```

> [!NOTE]
> Header `ngrok-skip-browser-warning: 69420` đã được thêm vào tất cả request từ Backend đến AI Service để bypass trang cảnh báo của Ngrok free tier.

---

## Hướng dẫn chạy Local

### Yêu cầu
- Python >= 3.11
- Node.js >= 18
- Android Studio Hedgehog+
- Docker (tuỳ chọn)

### 1. Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt

# Tạo file .env
MONGO_URI=mongodb+srv://22050055_db_user:{your_password}@khang1402.e2kn7mt.mongodb.net/?appName=khang1402&retryWrites=true&w=majority
MONGO_PASSWORD=your_mongo_password_here
JWT_SECRET=dev-secret-key-change-in-prod
AI_SERVICE_URL=http://localhost:8001
QR_PRIVATE_KEY_PATH=../ai_services/qr_generator/keys/private.pem
QR_PUBLIC_KEY_PATH=../ai_services/qr_generator/keys/public.pem

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. AI Services
```bash
cd ai_services
pip install -r requirements.txt

# Đảm bảo đã có models trong face_verification/models/buffalo_l/
python -m face_verification.face_service
# → http://0.0.0.0:8001
```

### 3. Web Dashboard
```bash
cd web-dashboard
npm install
# Tạo file .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
# → http://localhost:5173
```

### 4. Android Gate App
1. Mở Android Studio → **Open** → chọn thư mục `gate-app/`
2. Trong `app/src/main/java/.../data/api/ApiClient.kt`, sửa `BASE_URL` thành IP máy tính local.
3. Kết nối thiết bị Android thật (khuyến nghị — camera ảo Emulator không hỗ trợ Face ID).
4. Nhấn **Run ▶**

### 5. Chạy toàn bộ bằng Docker Compose
```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Web Dashboard | http://localhost:5173 |
| AI Service | http://localhost:8001 |

---

## API Reference

### Auth
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/auth/login` | Đăng nhập Staff (username/password) → JWT |
| POST | `/api/auth/refresh` | Làm mới access token |
| POST | `/api/customer/login` | Đăng nhập Khách hàng (email/password) |
| POST | `/api/customer/register` | Đăng ký tài khoản khách hàng |

### Tickets
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/tickets/issue` | Staff phát hành vé tại quầy |
| POST | `/api/customer/buy-ticket` | Khách tự mua vé online |
| GET | `/api/customer/tickets` | Danh sách vé của khách đang đăng nhập |
| POST | `/api/customer/tickets/{id}/review` | Khách đánh giá vé đã sử dụng (1-5 ★) |

### Face ID
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/face/enroll` | Đăng ký khuôn mặt (3–5 mẫu) cho vé |

### Check-in / Out
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/checkin` | Check-in/out thống nhất (tất cả kênh) |

```json
// Body mẫu kênh QR + Face
{
  "channel": "qr_face",
  "direction": "IN",
  "gate_id": "gate_01",
  "qr_payload": "eyJ...",
  "face_image_b64": "data:image/jpeg;base64,..."
}
```

### Quản lý (Admin/Manager)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/customer/all` | Danh sách toàn bộ khách hàng |
| PATCH | `/api/customer/{id}` | Cập nhật thông tin khách |
| DELETE | `/api/customer/{id}` | Xoá tài khoản khách |
| GET | `/api/gates` | Danh sách cổng |

### Reports & Dashboard
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/reports/revenue` | Doanh thu theo ngày / loại vé |
| GET | `/api/reports/visitors` | Lượt vào/ra theo cổng / kênh |
| GET | `/api/reports/reviews` | Danh sách đánh giá |
| GET | `/api/reports/review-stats` | Thống kê sao trung bình |
| GET | `/api/reports/export` | Xuất báo cáo CSV |
| WS  | `/ws/presence?token=...` | Tracking trạng thái Online của Staff |

---

## Tài khoản demo

### 🌐 Web Dashboard
**URL:** [https://fc439656.tourism-dashboard.pages.dev](https://fc439656.tourism-dashboard.pages.dev)

| Quyền | Tài khoản | Mật khẩu |
|-------|-----------|----------|
| **Admin** | `admin` | `admin123` |
| **Quản lý (Manager)** | `manager1` | `manager123` |
| **Vận hành (Operator)** | `operator1` | `operator123` |
| **Bán vé (Cashier)** | `cashier1` | `cashier123` |

### 📱 App Khách hàng
| Email | Mật khẩu |
|-------|----------|
| `22050055@student.bdu.edu.vn` | `123456` |

---

## Ghi chú pháp lý

> ⚠️ Hệ thống tuân thủ nguyên tắc tối thiểu dữ liệu và bảo vệ quyền riêng tư:

- **CCCD / ID:** Chỉ lưu hash SHA-256, **không** lưu số CCCD gốc, **không** lưu ảnh CCCD.
- **Khuôn mặt:** Chỉ lưu vector embedding 512-d, **không** lưu ảnh gốc. Triển khai theo cơ chế **opt-in** từ khách hàng. Face chỉ thực hiện xác thực **1:1 (Verification)**, không nhận diện đại trà **1:N**.
- **Audit Trail:** Mọi request đều bị ghi log đầy đủ (user, IP, endpoint, status code, response time) phục vụ kiểm tra trách nhiệm.
- **Mục đích:** Hệ thống phục vụ vận hành và báo cáo của khu du lịch, không sử dụng cho mục đích giám sát hay xâm phạm quyền riêng tư.

---

## Nhóm thực hiện

| Họ tên | MSSV | Vai trò |
|--------|------|---------|
| Trần Mạnh Khang | 22050055 | Phát triển toàn hệ thống |

**Giảng viên hướng dẫn:** *(Thêm tên GV)*

**Trường:** Đại học Bình Dương — Khoa Công nghệ Thông tin

---

*Đồ án Tốt nghiệp — Hệ thống kiểm soát ra/vào khu du lịch đa kênh*