"""
Giả lập sensor nhiệt độ (ESP32/DHT22)
Cứ mỗi INTERVAL giây, script gửi HTTP POST lên backend
với dữ liệu nhiệt độ dao động tự nhiên.

Cách chạy:
    pip install requests
    python sensor_simulator.py
"""

import requests
import random
import time
from datetime import datetime

# ── Cấu hình ──────────────────────────────────────────
BASE_URL    = "http://localhost:8000"
LOGIN_URL   = f"{BASE_URL}/api/v1/auth/login"
INGEST_URL  = f"{BASE_URL}/api/v1/sensors/ingest"

USERNAME    = "admin@example.com"
PASSWORD    = "admin123"

ROOM_ID     = 1
INTERVAL    = 2                                    # giây giữa mỗi lần gửi
TEMP_INIT   = 27.0                                 # nhiệt độ ban đầu
TEMP_MIN    = 22.0
TEMP_MAX    = 40.0
HUM_MIN     = 45.0
HUM_MAX     = 80.0
CO2_MIN     = 500.0
CO2_MAX     = 1400.0
# ──────────────────────────────────────────────────────

def next_temp(current: float) -> float:
    """Random walk: dao động ±0.6°C mỗi bước, giống sensor thật."""
    delta = (random.random() - 0.48) * 0.6
    return round(min(TEMP_MAX, max(TEMP_MIN, current + delta)), 1)

def get_access_token() -> str:
    res = requests.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD},
        timeout=5,
    )
    res.raise_for_status()
    body = res.json()
    return body["access_token"]


def send(temp: float, token: str) -> None:
    payload = {
        "room_id": ROOM_ID,
        "temperature": temp,
        "humidity": round(random.uniform(HUM_MIN, HUM_MAX), 1),
        "co2": round(random.uniform(CO2_MIN, CO2_MAX), 1),
        "motion_detected": random.choice([True, False]),
        "recorded_at": datetime.now().isoformat(),
    }
    try:
        res = requests.post(
            INGEST_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        print(
            f"[{payload['recorded_at']}]  {temp}°C  | hum={payload['humidity']}%"
            f" | co2={payload['co2']}ppm  →  HTTP {res.status_code}"
        )
    except requests.exceptions.ConnectionError:
        print(f"[{datetime.now().isoformat()}]  {temp}°C  →  ⚠️  Không kết nối được backend")
    except Exception as e:
        print(f"Lỗi: {e}")

def main():
    token = get_access_token()

    print("=" * 50)
    print(f"  Sensor simulator  |  ROOM_ID: {ROOM_ID}")
    print(f"  Login URL: {LOGIN_URL}")
    print(f"  Ingest URL: {INGEST_URL}")
    print(f"  Tần suất: mỗi {INTERVAL}s")
    print("  Nhấn Ctrl+C để dừng")
    print("=" * 50)

    temp = TEMP_INIT
    while True:
        send(temp, token)
        temp = next_temp(temp)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
