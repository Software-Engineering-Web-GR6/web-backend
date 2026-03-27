# Smart Classroom Backend

Backend cho he thong giam sat va dieu khien phong hoc thong minh.

## Chuc nang chinh

- Dang nhap bang JWT
- Quan ly phong hoc
- Nhan du lieu cam bien
- Dieu khien thiet bi
- Tu dong hoa theo rule
- Canh bao va dashboard
- Thoi khoa bieu theo `room + shift + day`
- Che do `tu dong / thu cong` theo tung phong
- Doi mat khau cho tai khoan dang dang nhap

## Yeu cau

- Python 3.11+
- `pip`

Kiem tra nhanh:

```bash
python --version
pip --version
```

## Cai dat

### 1. Vao thu muc backend

```cmd
cd /d e:\baitapCNPM\backend
```

### 2. Tao virtual environment

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

### 3. Cai dependencies

```bash
pip install -r requirements.txt
```

### 4. Tao file moi truong

Copy `.env.example` thanh `.env`, hoac tao file toi thieu nhu sau:

```env
SECRET_KEY=change-this-secret-key
DATABASE_URL=sqlite+aiosqlite:///./smart_classroom.db
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

## Chay backend

Neu da co san moi truong:

```cmd
cd /d e:\baitapCNPM\backend
.venv\Scripts\activate.bat
uvicorn main:app --reload
```

Dia chi mac dinh:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- WebSocket alerts: `ws://127.0.0.1:8000/ws/alerts`

## Tai khoan mac dinh

Admin duoc seed tu dong:

- Email: `admin@example.com`
- Password: `admin123`

Hai user demo co thoi khoa bieu mau cung duoc seed tu dong:

- Email: `demo.user1@example.com`
- Password: `user12345`
- Email: `demo.user2@example.com`
- Password: `user12345`

Dang nhap:

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

Trong Swagger:

- `username` = email
- `password` = mat khau

## Thoi khoa bieu theo phong, ca, ngay

User thuong chi duoc xem hoac dieu khien phong khi trong thoi khoa bieu hien tai co dung:

- `room_id`
- `shift_number`
- `day_of_week`

Admin duoc bo qua kiem tra nay.

Khung gio 6 ca:

- Ca 1: `07:00 - 09:35`
- Ca 2: `09:35 - 12:00`
- Ca 3: `13:00 - 15:35`
- Ca 4: `15:35 - 18:00`
- Ca 5: `18:15 - 19:50`
- Ca 6: `19:55 - 21:30`

`day_of_week` dung chuan Python: `0=Monday ... 6=Sunday`

### API thoi khoa bieu

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

Luu y:

- Cac endpoint tren hien van giu ten `room-access` de tuong thich voi code dang chay.
- Ve mat nghiep vu, moi ban ghi `room-access` duoc hieu la mot o trong thoi khoa bieu cua user.

## Thiet bi va tu dong hoa

Moi phong hien duoc seed:

- 4 quat
- 4 den
- 3 dieu hoa

Che do hoat dong cua phong:

- `auto_control_enabled = true`: cho phep automation rules chay khi ingest sensor
- `auto_control_enabled = false`: phong o che do thu cong, backend se bo qua automation

API cap nhat mode:

```http
PUT /api/v1/rooms/{room_id}/automation-mode
Content-Type: application/json

{
  "auto_control_enabled": false
}
```

Luu y:

- Khi chuyen phong sang `manual`, toan bo rules cua phong se bi tat theo.
- Khi rules cua phong duoc bat lai, mode cua phong cung duoc dong bo lai theo backend.

## Doi mat khau

Tai khoan dang dang nhap co the doi mat khau bang API:

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

- Dang nhap bang admin mac dinh
- Lay toan bo danh sach phong tu backend
- Sinh du lieu gia cho tat ca phong
- Phan ung theo trang thai thiet bi tung phong

Chay:

```cmd
cd /d e:\baitapCNPM\backend
.venv\Scripts\activate.bat
python sensor_simulator.py
```

Neu backend dang chay, simulator se bom du lieu lien tuc vao:

```http
POST /api/v1/sensors/ingest
```

## Chay test

Chay toan bo:

```bash
pytest -q
```

Vi du:

```bash
pytest -q tests/test_room_shift_access.py
pytest -q tests/test_api_auth.py
pytest -q tests/test_api_sensors.py
pytest -q tests/test_api_alerts.py
```

## Cau truc chinh

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
