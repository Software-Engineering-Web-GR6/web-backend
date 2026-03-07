```text
Cảm biến (DHT22, MQ-135...)
        │  gửi dữ liệu qua MQTT / HTTP
        ▼
┌──────────────────────────────────────┐
│   API Layer  /sensors/ingest         │  ← Nhận reading từ thiết bị IoT
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│   SensorService  .ingest()           │  ← Lưu DB
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│   AutomationEngine  .evaluate()      │  ← So sánh với Rule ngưỡng
│                                      │
│   VD: nhiệt độ=34°C > threshold=30°C │
│       → action: bật quạt phòng A     │
└──────────────┬───────────────────────┘
               │          │
        ┌──────┘          └──────────┐
        ▼                           ▼
┌──────────────┐           ┌─────────────────┐
│ DeviceService│           │ AlertService     │
│ .control()   │           │ .create_alert()  │
│ Bật quạt/cửa│           │ Push WebSocket   │
└──────────────┘           └─────────────────┘
```
```bash
smart_classroom/
│
├── main.py
├── requirements.txt
├── .env
│
└── app/
    │
    └── websocket/
    |    └── manager.py           ← WebSocketManager: broadcast alert realtime
    |
    ├── api/v1/endpoints/        ◄── TẦNG 1: API
    │   ├── sensors.py           ← POST /sensors/ingest  (IoT device gửi lên)
    │   │                           GET  /sensors/{room_id}/latest
    │   │                           GET  /sensors/{room_id}/history
    │   ├── devices.py           ← GET  /devices/{room_id}
    │   │                           POST /devices/{id}/control  (manual override)
    │   ├── rules.py             ← CRUD /rules  (admin cấu hình ngưỡng)
    │   ├── alerts.py            ← GET  /alerts  (danh sách cảnh báo)
    │   │                           POST /alerts/{id}/resolve
    │   ├── dashboard.py         ← GET  /dashboard/{room_id}  (tổng hợp real-time)
    │   └── auth.py              ← POST /auth/login
    |
    ├── services/                ◄── TẦNG 2: Service Layer
    │   ├── sensor_service.py    ← ingest() → lưu reading → gọi AutomationEngine
    │   ├── device_service.py    ← control() → gửi lệnh tới thiết bị thật
    │   ├── alert_service.py     ← create(), resolve(), push WebSocket
    │   └── rule_service.py      ← CRUD rule, validate logic rule
    ├── domain/                 ◄── Layer 3: Domain
    │   ├── automation_engine.py
    |   └── condition_evaluator.py
    |
    ├── repositories/            ◄── TẦNG 4: reposities
    │   ├── base.py              ← Generic CRUD
    │   ├── sensor_repository.py ← get_latest(), get_history(), get_avg()
    │   ├── device_repository.py ← get_by_room(), update_state()
    │   ├── rule_repository.py   ← get_active_rules_by_room()
    │   ├── action_log_repository.py
    │   └── alert_repository.py  ← get_unresolved(), create_alert()
    |
    ├── models/                  ◄── ORM
    │   ├── room.py              ← Room (id, name, location)
    │   ├── device.py            ← Device (quạt, cửa sổ, điều hòa...)
    │   ├── sensor_reading.py    ← SensorReading (temp, humidity, co2, timestamp)
    │   ├── automation_rule.py   ← AutomationRule (if temp>30 → turn_on fan_01)
    │   ├── action_log.py        ← ActionLog (lịch sử lệnh đã thực thi)
    │   ├── alert.py             ← Alert (cảnh báo ngưỡng nguy hiểm)
    │   └── user.py              ← User (admin quản lý hệ thống)
    │

    ├── core/
    │   ├── config.py            ← Cấu hình app, ngưỡng mặc định
    │   ├── security.py          ← JWT, hash password
    │   └── dependencies.py      ← get_db, get_current_user
    │
    ├── db/
    │   └── session.py           ← AsyncSession, engine
    │
    ├── schemas/                 ← Pydantic DTOs
    │   ├── sensor.py            ← SensorReadingCreate, SensorReadingResponse
    │   ├── device.py            ← DeviceResponse, DeviceControlRequest
    │   ├── automation_rule.py   ← RuleCreate, RuleResponse
    │   ├── alert.py             ← AlertResponse
    |    └── auth.py              ← LoginRequest, TokenResponse
```
    
