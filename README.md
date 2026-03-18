# Smart Classroom Backend

Backend FastAPI cho đề tài **Hệ thống cảnh báo & kiểm soát phòng học thông minh**.

## Chức năng đã có
- Đăng nhập JWT nội bộ
- IoT ingest sensor data: `POST /api/v1/sensors/ingest`
- Xem latest/history sensor data
- Rule engine tự động tạo cảnh báo và điều khiển thiết bị
- Danh sách cảnh báo, resolve cảnh báo
- Điều khiển thiết bị thủ công
- Dashboard tổng hợp theo phòng
- WebSocket cảnh báo realtime tại `/ws/alerts`

## Cấu trúc chính
- `api/v1/endpoints`: tầng API
- `services`: tầng xử lý nghiệp vụ
- `domain`: rule engine / condition evaluator
- `repositories`: truy cập dữ liệu
- `models`: ORM
- `schemas`: DTO/Pydantic

## Tài khoản mặc định
Hệ thống tự seed tài khoản admin đầu tiên khi khởi động:
- email: `admin@example.com`
- password: `admin123`

## Dữ liệu mẫu được seed
- 1 phòng học: `Room A101`
- 3 thiết bị: quạt, điều hòa, cửa sổ
- 2 rule mẫu:
  - nhiệt độ > 30 => bật quạt
  - CO2 > 1000 => mở cửa sổ

## Cài đặt
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy ứng dụng
```bash
uvicorn main:app --reload
```

## Swagger Docs
- `http://127.0.0.1:8000/docs`

## Luồng test nhanh
1. Gọi `POST /api/v1/auth/login`
2. Dùng token để gọi các API bảo vệ
3. Gọi `POST /api/v1/sensors/ingest` với dữ liệu ví dụ:
```json
{
  "room_id": 1,
  "temperature": 32,
  "humidity": 70,
  "co2": 1200,
  "motion_detected": true
}
```
4. Kiểm tra:
- `GET /api/v1/alerts/`
- `GET /api/v1/devices/1`
- `GET /api/v1/dashboard/1`

## Gợi ý mở rộng
- thêm MQTT thật để publish control command xuống ESP32
- thêm endpoint quản lý room/user/action_log
- thêm role teacher/technician
- thêm unit tests và Alembic migrations
