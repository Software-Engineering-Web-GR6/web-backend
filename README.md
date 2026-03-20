# Smart Classroom Backend


## Yêu cầu môi trường

- Python 3.11+ (khuyến nghị 3.13 như máy hiện tại)
- `pip`
- Git

Kiểm tra nhanh:

```bash
python --version
pip --version
```

## Set Up

### Bước 1: vào thư mục backend

```bash
cd web-backend
```

### Bước 2: tạo virtual environment

macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### Bước 3: cài dependencies

```bash
pip install -r requirements.txt
```

### Bước 4: tạo file môi trường

```bash
cp .env.example .env
```

Sau đó chỉnh `SECRET_KEY` trong `.env` bằng chuỗi random an toàn:

```bash
openssl rand -hex 32
```

## Chạy ứng dụng

```bash
uvicorn main:app --reload
```

Server mặc định chạy tại:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

##  Đăng nhập lần đầu

Hệ thống sẽ seed tài khoản admin mặc định khi login lần đầu:

- Email: `admin@example.com`
- Password: `admin123`

Endpoint login:

```http
POST /api/v1/auth/login
```

Trong Swagger, dùng OAuth2 form:

- `username` = email
- `password` = mật khẩu

##  Phân quyền theo phòng + ca + ngày

User thường chỉ được xem/điều khiển phòng khi thỏa cả 3 điều kiện:

- đúng `room_id`
- đúng `shift_number`
- đúng `day_of_week`

Admin được bypass kiểm tra này.

### Khung giờ 6 ca

- Ca 1: 07:00 - 09:35
- Ca 2: 09:35 - 12:00
- Ca 3: 13:00 - 15:35
- Ca 4: 15:35 - 18:00
- Ca 5: 18:15 - 19:50
- Ca 6: 19:55 - 21:30

`day_of_week` dùng chuẩn Python: `0=Monday ... 6=Sunday`

### API admin cấp quyền

#### Cấp quyền

```http
POST /api/v1/auth/users/{user_id}/room-access
Content-Type: application/json

{
  "room_id": 1,
  "shifts": [2, 3],
  "days_of_week": [0, 2, 4]
}
```

#### Xem quyền

```http
GET /api/v1/auth/users/{user_id}/room-access
```

#### Thu hồi 1 quyền

```http
DELETE /api/v1/auth/users/{user_id}/room-access?room_id=1&shift_number=2&day_of_week=0
```

##  Chạy test

Chạy toàn bộ:

```bash
pytest -q
```

VD Chạy test phân quyền theo ca/ngày:

```bash
pytest -q tests/test_room_shift_access.py
```

##  Cấu trúc chính

```text
app/
├── api/v1/endpoints/     # REST endpoints
├── core/                 # config, security, dependencies
├── db/                   # session + init db
├── domain/               # automation/condition logic
├── models/               # SQLAlchemy models
├── repositories/         # data access layer
├── schemas/              # Pydantic schemas
├── services/             # business logic layer
└── websocket/            # realtime broadcast
```