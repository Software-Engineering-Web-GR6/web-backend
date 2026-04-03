# Smart Classroom Backend

Backend FastAPI cho he thong giam sat va dieu khien phong hoc thong minh.

## Chuc nang chinh

- Dang nhap JWT
- Quan ly phong hoc
- Nhan du lieu cam bien
- Dieu khien thiet bi
- Tu dong hoa theo rule
- Alert va dashboard
- Phan quyen theo `room + shift + day`
- MQTT cho sensor data va device command

## Yeu cau

- Python 3.11+
- Pip
- MQTT Broker neu muon chay luong MQTT that

## Cai dat

```powershell
cd e:\baitapCNPM\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Cau hinh

Copy `.env.example` thanh `.env`.

Bien toi thieu:

```env
SECRET_KEY=change-this-secret-key
DATABASE_URL=postgresql+asyncpg://smartclassroom:smartclassroom@localhost:5432/smart_classroom
TEST_DATABASE_URL=postgresql+asyncpg://smartclassroom:smartclassroom@localhost:5432/smart_classroom_test
ACCESS_TOKEN_EXPIRE_MINUTES=120
MQTT_ENABLED=true
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_SENSOR_TOPIC=smartclassrooms/sensors/readings
MQTT_DEVICE_COMMAND_TOPIC_PREFIX=smartclassrooms/devices
MQTT_DEVICE_ACK_TIMEOUT_SECONDS=1.5
SMTP_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@smartclassroom.local
SMTP_USE_TLS=true
PASSWORD_RESET_CODE_EXPIRE_MINUTES=10
PASSWORD_RESET_CODE_LENGTH=6
PASSWORD_RESET_MAX_ATTEMPTS=5
SIMULATOR_RESET_HISTORY_ON_START=false
```

## Chay backend

```powershell
cd e:\baitapCNPM\backend
.\.venv\Scripts\Activate.ps1
$env:MQTT_BROKER_HOST="localhost"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Neu chay local khong dung Docker, ban can co PostgreSQL dang chay tai `localhost:5432`
va database `smart_classroom`/user `smartclassroom` theo `DATABASE_URL`, hoac tu sua lai
chuoi ket noi trong `.env`.

Dia chi mac dinh:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- WebSocket alerts: `ws://127.0.0.1:8000/ws/alerts`

## Tai khoan mac dinh

- Admin:
  - Email: `admin@example.com`
  - Password: `admin123`
- Demo user 1:
  - Email: `demo.user1@example.com`
  - Password: `user12345`
- Demo user 2:
  - Email: `demo.user2@example.com`
  - Password: `user12345`

## MQTT flow

He thong hien ho tro 2 huong:

- Sensor data:
  `sensor_simulator.py -> MQTT Broker -> backend -> database -> websocket/api -> frontend`
- Device command:
  `frontend -> backend -> MQTT Broker -> device_command_simulator.py`

## Sensor simulator

File: `sensor_simulator.py`

Chuc nang:

- Dang nhap backend bang admin
- Lay danh sach phong
- Lay trang thai thiet bi tung phong
- Gia lap nhiet do, do am, CO2
- Publish du lieu len MQTT hoac goi HTTP ingest

Chay voi MQTT:

```powershell
cd e:\baitapCNPM\backend
.\.venv\Scripts\Activate.ps1
$env:SIMULATOR_TRANSPORT="mqtt"
$env:MQTT_BROKER_HOST="localhost"
$env:BACKEND_BASE_URL="http://localhost:8000"
python sensor_simulator.py
```

Neu muon reset lich su sensor truoc khi chay:

```powershell
$env:SIMULATOR_RESET_HISTORY_ON_START="true"
```

## Device command simulator

File: `device_command_simulator.py`

Chuc nang:

- Subscribe topic device command
- Gia lap ESP32 nhan lenh `ON / OFF / OPEN / CLOSE / SET_TEMPERATURE`
- Publish ACK nhe len topic status

Chay:

```powershell
cd e:\baitapCNPM\backend
.\.venv\Scripts\Activate.ps1
$env:MQTT_BROKER_HOST="localhost"
python device_command_simulator.py
```

Topic command mac dinh:

```text
smartclassrooms/devices/{room_id}/{device_id}/commands
```

## API chinh

- Auth:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/forgot-password`
  - `POST /api/v1/auth/verify-reset-code`
  - `POST /api/v1/auth/reset-password`
- Rooms:
  - `GET /api/v1/rooms`
  - `PUT /api/v1/rooms/{room_id}/automation-mode`
- Sensors:
  - `POST /api/v1/sensors/ingest`
  - `GET /api/v1/sensors/{room_id}/latest`
  - `GET /api/v1/sensors/{room_id}/history`
- Devices:
  - `GET /api/v1/devices/{room_id}`
  - `POST /api/v1/devices/{device_id}/control`
  - `PUT /api/v1/devices/{device_id}/temperature`
- Alerts:
  - `GET /api/v1/alerts/`
  - `POST /api/v1/alerts/{alert_id}/resolve`

## Test

Chay toan bo:

```powershell
cd e:\baitapCNPM\backend
.\.venv\Scripts\Activate.ps1
pytest -q
```

Tinh den luc README nay duoc cap nhat, backend pass:

- `102` tests

## Docker

### Chay rieng trong repo backend

Repo backend nay da co file Docker rieng tai `docker-compose.yml`.

Neu Docker Desktop dang chay:

```powershell
cd e:\baitapCNPM\backend
docker compose up --build
```

Compose trong repo backend se dung:

- PostgreSQL
- Backend

Mac dinh:

- Backend: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`
- MQTT da tat (`MQTT_ENABLED=false`) de demo/deploy backend don gian hon

Neu chi muon bat PostgreSQL:

```powershell
cd e:\baitapCNPM\backend
docker compose up -d postgres
```

### Chay full stack o workspace goc

Neu ban dang dung full workspace co ca frontend + mqtt broker:

```powershell
cd e:\baitapCNPM
docker compose up --build
```

Compose o workspace goc se dung:

- PostgreSQL
- MQTT Broker
- Backend
- Frontend `frontend-demo2/smart-classrooms`
- Device command simulator
- Sensor simulator

## Ghi chu migration

- PostgreSQL la database mac dinh cua ung dung.
- Nhanh migration SQLite trong code chi con de doc/nang cap file SQLite cu neu can.
- Test suite da duoc chuyen sang PostgreSQL qua `TEST_DATABASE_URL`.

## Tai lieu bo sung

- `ARCHITECTURE.md`: tom tat kien truc va luong du lieu
- `DEPLOY_VPS.md`: huong dan deploy production tren VPS (backend + postgres + mqtt + simulator profile)

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
