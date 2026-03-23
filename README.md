# Smart Classroom Backend

Backend cho hệ thống giám sát và điều khiển phòng học thông minh.

## Chức năng chính

- Đăng nhập bằng JWT
- Quản lý phòng học
- Nhận dữ liệu cảm biến
- Điều khiển thiết bị
- Tự động hóa theo rule
- Cảnh báo và dashboard
- Phân quyền theo `room + shift + day`
- Chế độ `tự động / thủ công` theo từng phòng
- Đổi mật khẩu cho tài khoản đang đăng nhập

## Yêu cầu

- Python 3.11+
- `pip`

Kiểm tra nhanh:

```bash
python --version
pip --version
```

## Cài đặt

### 1. Vào thư mục backend

```cmd
cd /d e:\baitapCNPM\backend
```

### 2. Tạo virtual environment

Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Cài dependencies

```bash
pip install -r requirements.txt
```

### 4. Tạo file môi trường

Nếu chưa có `.env.example`, bạn có thể tự tạo file `.env` tối thiểu như sau:

```env
SECRET_KEY=change-this-secret-key
DATABASE_URL=sqlite+aiosqlite:///./smart_classroom.db
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

## Chạy backend

Nếu đã có sẵn môi trường:

```cmd
cd /d e:\baitapCNPM\backend
.venv\Scripts\activate.bat
uvicorn main:app --reload
```

URL mặc định:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- WebSocket alerts: `ws://127.0.0.1:8000/ws/alerts`

## Tài khoản mặc định

Admin được seed tự động:

- Email: `admin@example.com`
- Password: `admin123`

Đăng nhập:

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

Trong Swagger:

- `username` = email
- `password` = mật khẩu

## Phân quyền theo phòng, ca, ngày

User thường chỉ được xem hoặc điều khiển phòng khi đồng thời đúng:

- `room_id`
- `shift_number`
- `day_of_week`

Admin được bỏ qua kiểm tra này.

Khung giờ 6 ca:

- Ca 1: `07:00 - 09:35`
- Ca 2: `09:35 - 12:00`
- Ca 3: `13:00 - 15:35`
- Ca 4: `15:35 - 18:00`
- Ca 5: `18:15 - 19:50`
- Ca 6: `19:55 - 21:30`

`day_of_week` dùng chuẩn Python: `0=Monday ... 6=Sunday`

### API phân quyền

```http
POST /api/v1/auth/users/{user_id}/room-access
Content-Type: application/json

{
  "room_id": 1,
  "shifts": [2, 3],
  "days_of_week": [0, 2, 4]
}
```

```http
GET /api/v1/auth/users/{user_id}/room-access
```

```http
GET /api/v1/auth/me/room-access
```

```http
GET /api/v1/auth/rooms/{room_id}/room-access
```

```http
DELETE /api/v1/auth/users/{user_id}/room-access?room_id=1&shift_number=2&day_of_week=0
```

## Thiết bị và tự động hóa

Mỗi phòng hiện được seed:

- 4 quạt
- 4 đèn
- 3 điều hòa

Chế độ hoạt động của phòng:

- `auto_control_enabled = true`: cho phép automation rules chạy khi ingest sensor
- `auto_control_enabled = false`: phòng ở chế độ thủ công, backend sẽ bỏ qua automation

API cập nhật mode:

```http
PUT /api/v1/rooms/{room_id}/automation-mode
Content-Type: application/json

{
  "auto_control_enabled": false
}
```

Lưu ý:

- Khi chuyển phòng sang `manual`, toàn bộ rules của phòng sẽ bị tắt theo.
- Khi rules của phòng được bật lại, mode của phòng cũng được đồng bộ lại theo backend.

## Đổi mật khẩu

Tài khoản đang đăng nhập có thể đổi mật khẩu bằng API:

```http
PUT /api/v1/auth/me/password
Content-Type: application/json

{
  "current_password": "admin123",
  "new_password": "admin12345"
}
```

## Sensor Simulator

File `sensor_simulator.py`:

- đăng nhập bằng admin mặc định
- lấy toàn bộ danh sách phòng từ backend
- sinh dữ liệu giả cho tất cả phòng
- phản ứng theo trạng thái thiết bị từng phòng

Chạy:

```cmd
cd /d e:\baitapCNPM\backend
.venv\Scripts\activate.bat
python sensor_simulator.py
```

Nếu backend đang chạy, simulator sẽ bơm dữ liệu liên tục vào:

```http
POST /api/v1/sensors/ingest
```

## Chạy test

Chạy toàn bộ:

```bash
pytest -q
```

Ví dụ:

```bash
pytest -q tests/test_room_shift_access.py
pytest -q tests/test_api_auth.py
pytest -q tests/test_api_sensors.py
pytest -q tests/test_api_alerts.py
```

## Cấu trúc chính

```text
app/
|-- api/v1/endpoints/   # REST endpoints
|-- core/               # config, security, dependencies
|-- db/                 # session + init db
|-- domain/             # automation / condition logic
|-- models/             # SQLAlchemy models
|-- repositories/       # data access layer
|-- schemas/            # Pydantic schemas
|-- services/           # business logic layer
`-- websocket/          # realtime broadcast

```
