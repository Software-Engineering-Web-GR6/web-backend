# Smart Classroom Architecture

## Muc tieu

Tai lieu nay tom tat kien truc hien tai cua du an de dua vao bao cao va de mo ta ro luong du lieu.

## Thanh phan chinh

- `Frontend`: giao dien React/Vite cho admin va user.
- `Backend`: FastAPI xu ly auth, room, device, sensor, alert, dashboard.
- `Database`: PostgreSQL la database chinh cho local/dev/deploy.
- `MQTT Broker`: lop trung gian cho sensor data va device command.
- `sensor_simulator.py`: gia lap node IoT gui du lieu cam bien.
- `device_command_simulator.py`: gia lap node IoT nhan lenh dieu khien thiet bi.

## Luong du lieu cam bien

1. `sensor_simulator.py` dang nhap backend bang tai khoan admin.
2. Simulator lay danh sach phong va trang thai thiet bi hien tai.
3. Simulator tao du lieu nhiet do, do am, CO2 va motion.
4. Simulator publish JSON len topic MQTT:
   `smartclassrooms/sensors/readings`
5. Backend subscribe topic nay trong `app/services/mqtt_service.py`.
6. Backend validate payload va goi `sensor_service.ingest(...)`.
7. `sensor_service.ingest(...)`:
   - luu sensor reading vao database
   - evaluate automation rule
   - tao alert neu vuot nguong
   - broadcast realtime qua WebSocket
8. Frontend doc du lieu qua REST API va WebSocket.

## Luong dieu khien thiet bi

1. User bam bat/tat thiet bi tren frontend.
2. Frontend goi REST API:
   - `POST /api/v1/devices/{device_id}/control`
   - `PUT /api/v1/devices/{device_id}/temperature`
3. Backend kiem tra quyen truy cap.
4. `device_service.py` cap nhat state trong database.
5. Backend publish MQTT command len topic:
   `smartclassrooms/devices/{room_id}/{device_id}/commands`
6. `device_command_simulator.py` subscribe wildcard command topic va in ra lenh da nhan.
7. Simulator publish acknowledgement len topic:
   `smartclassrooms/devices/{room_id}/{device_id}/status`

## Y nghia cua 2 simulator

- `sensor_simulator.py` thay vai tro ESP32 o chieu gui du lieu cam bien.
- `device_command_simulator.py` thay vai tro ESP32 o chieu nhan lenh dieu khien.

## Trang thai hien tai

- He thong da ho tro du 2 chieu qua MQTT o muc backend:
  - sensor -> MQTT -> backend
  - backend -> MQTT -> device command consumer
- Frontend hien tai van giao tiep voi backend bang REST va WebSocket.
- PostgreSQL la duong chay chinh; nhanh xu ly SQLite chi con de tuong thich du lieu cu.
- MQTT status acknowledgement da co o muc simulator, nhung backend chua consume topic status nay de cap nhat `is_online` hay command ack.

## Huong mo rong sau nay

- Them consumer cho topic device status/ack trong backend.
- Dong bo `is_online`, `last_seen`, `last_command_status` theo ack that.
- Thay simulator bang ESP32/gateway that ma khong can doi nghiep vu chinh.
