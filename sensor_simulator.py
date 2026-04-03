"""
Sensor simulator for Smart Classroom.

This simulator logs in as admin, discovers all rooms from the backend, then
continuously ingests synthetic sensor readings for every room.

Each room has its own evolving environment and reacts to current device state:
- air_conditioner ON: temperature drops faster
- fan ON: temperature and CO2 drop slightly
- window OPEN: CO2 drops clearly and temperature trends toward outdoor air

Run:
    python sensor_simulator.py
"""

from __future__ import annotations

import random
import threading
import time
import json
import os
from datetime import datetime

import requests
import paho.mqtt.publish as mqtt_publish

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
ROOMS_URL = f"{BASE_URL}/api/v1/rooms"
INGEST_URL = f"{BASE_URL}/api/v1/sensors/ingest"
DEVICES_URL = f"{BASE_URL}/api/v1/devices"
RESET_HISTORY_URL = f"{BASE_URL}/api/v1/sensors/history/reset"
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_SENSOR_TOPIC = os.getenv("MQTT_SENSOR_TOPIC", "smartclassrooms/sensors/readings")
TRANSPORT_MODE = os.getenv("SIMULATOR_TRANSPORT", "mqtt").lower()
RESET_HISTORY_ON_START = os.getenv("SIMULATOR_RESET_HISTORY_ON_START", "false").lower() == "true"

USERNAME = os.getenv("SIMULATOR_USERNAME", "admin@example.com")
PASSWORD = os.getenv("SIMULATOR_PASSWORD", "admin123")

INTERVAL_SECONDS = 2
REQUEST_TIMEOUT = 5

TEMP_MIN = 18.0
TEMP_MAX = 40.0
HUM_MIN = 35.0
HUM_MAX = 85.0
CO2_MIN = 420.0
CO2_MAX = 1600.0

OUTDOOR_TEMP = 30.0
OUTDOOR_HUM = 63.0
OUTDOOR_CO2 = 470.0
INDOOR_HUM_BASELINE = 56.0


class TokenManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: str | None = None

    def get(self) -> str:
        with self._lock:
            if not self._token:
                self._token = get_access_token()
            return self._token

    def refresh(self) -> str:
        with self._lock:
            self._token = get_access_token()
            return self._token


def clamp(value: float, minimum: float, maximum: float) -> float:
    return round(min(maximum, max(minimum, value)), 1)


def get_access_token() -> str:
    response = requests.post(
        LOGIN_URL,
        data={"username": USERNAME, "password": PASSWORD},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_room_ids(token: str) -> list[int]:
    response = requests.get(
        ROOMS_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    rooms = response.json()
    return [room["id"] for room in rooms]


def reset_sensor_history(token: str, room_ids: list[int]) -> None:
    response = requests.delete(
        RESET_HISTORY_URL,
        params=[("room_ids", room_id) for room_id in room_ids],
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    print(
        f"Reset old sensor history before simulation: deleted={body.get('deleted', 0)}",
        flush=True,
    )


def get_device_states(token: str, room_id: int) -> dict[str, float | bool]:
    response = requests.get(
        f"{DEVICES_URL}/{room_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    devices = response.json()
    fan_on = any(
        device["device_type"] == "fan" and device["state"] == "ON"
        for device in devices
    )
    ac_devices_on = [
        device for device in devices
        if device["device_type"] == "air_conditioner" and device["state"] == "ON"
    ]
    light_on = any(
        device["device_type"] == "light" and device["state"] == "ON"
        for device in devices
    )
    window_open = any(
        device["device_type"] == "window" and device["state"] == "OPEN"
        for device in devices
    )
    ac_target_temp = (
        sum(device.get("target_temp", 24) for device in ac_devices_on) / len(ac_devices_on)
        if ac_devices_on else 24.0
    )
    return {
        "fan_on": fan_on,
        "ac_on": len(ac_devices_on) > 0,
        "light_on": light_on,
        "window_open": window_open,
        "ac_target_temp": ac_target_temp,
    }


def is_unauthorized(error: requests.HTTPError) -> bool:
    response = getattr(error, "response", None)
    return bool(response is not None and response.status_code == 401)


def create_initial_environment(seed_offset: int) -> tuple[float, float, float]:
    randomizer = random.Random(seed_offset)
    temp = 27.0 + randomizer.uniform(-1.5, 2.5)
    humidity = 62.0 + randomizer.uniform(-5.0, 6.0)
    co2 = 900.0 + randomizer.uniform(-120.0, 180.0)
    return (
        clamp(temp, TEMP_MIN, TEMP_MAX),
        clamp(humidity, HUM_MIN, HUM_MAX),
        clamp(co2, CO2_MIN, CO2_MAX),
    )


def evolve_environment(
    temp: float,
    humidity: float,
    co2: float,
    states: dict[str, float | bool],
) -> tuple[float, float, float]:
    fan_on = bool(states.get("fan_on"))
    ac_on = bool(states.get("ac_on"))
    window_open = bool(states.get("window_open"))
    ac_target_temp = float(states.get("ac_target_temp", 24.0))

    base_temp_target = OUTDOOR_TEMP - 2.5
    base_hum_target = INDOOR_HUM_BASELINE if not window_open else OUTDOOR_HUM
    temp_delta = (base_temp_target - temp) * 0.16 + random.uniform(-0.12, 0.12)
    hum_delta = (base_hum_target - humidity) * 0.12 + random.uniform(-0.18, 0.18)
    co2_delta = random.uniform(8, 28)

    if ac_on:
        temp_delta = (ac_target_temp - temp) * 0.42 + random.uniform(-0.08, 0.08)
        hum_delta += (48.0 - humidity) * 0.08 - random.uniform(0.05, 0.18)
        co2_delta -= random.uniform(5, 15)

    if fan_on:
        if ac_on:
            temp_delta += (ac_target_temp - temp) * 0.08 + random.uniform(-0.04, 0.04)
        elif temp > 24.0:
            temp_delta -= random.uniform(0.05, 0.18)
        else:
            temp_delta += random.uniform(-0.05, 0.05)
        hum_delta += (52.0 - humidity) * 0.04 - random.uniform(0.02, 0.08)
        co2_delta -= random.uniform(20, 55)

    if window_open:
        temp_delta += (OUTDOOR_TEMP - temp) * 0.18
        hum_delta += (OUTDOOR_HUM - humidity) * 0.15
        co2_delta += (OUTDOOR_CO2 - co2) * 0.28

    temp = clamp(temp + temp_delta, TEMP_MIN, TEMP_MAX)
    if ac_on and abs(temp - ac_target_temp) < 0.5:
        temp = clamp(ac_target_temp + random.uniform(-0.2, 0.2), TEMP_MIN, TEMP_MAX)

    humidity = clamp(humidity + hum_delta, HUM_MIN, HUM_MAX)
    co2 = clamp(co2 + co2_delta, CO2_MIN, CO2_MAX)
    return temp, humidity, co2


def send_reading(
    token: str,
    room_id: int,
    temp: float,
    humidity: float,
    co2: float,
) -> None:
    payload = {
        "room_id": room_id,
        "temperature": temp,
        "humidity": humidity,
        "co2": co2,
        "motion_detected": random.choice([True, False]),
        "recorded_at": datetime.now().isoformat(),
    }
    if TRANSPORT_MODE == "mqtt":
        mqtt_publish.single(
            MQTT_SENSOR_TOPIC,
            payload=json.dumps(payload),
            hostname=MQTT_BROKER_HOST,
            port=MQTT_BROKER_PORT,
        )
        print(
            f"[{payload['recorded_at']}] room={room_id} temp={temp}C "
            f"hum={humidity}% co2={co2}ppm -> MQTT {MQTT_SENSOR_TOPIC}",
            flush=True,
        )
        return

    response = requests.post(
        INGEST_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    print(
        f"[{payload['recorded_at']}] room={room_id} temp={temp}C "
        f"hum={humidity}% co2={co2}ppm -> HTTP {response.status_code}",
        flush=True,
    )


def run_room_simulator(
    token_manager: TokenManager,
    room_id: int,
    initial_environment: tuple[float, float, float],
    stop_event: threading.Event,
) -> None:
    temp, humidity, co2 = initial_environment
    jitter = random.Random(room_id * 997)

    while not stop_event.is_set():
        try:
            token = token_manager.get()
            states = get_device_states(token, room_id)
            temp, humidity, co2 = evolve_environment(
                temp=temp,
                humidity=humidity,
                co2=co2,
                states=states,
            )
            send_reading(token, room_id, temp, humidity, co2)
        except requests.HTTPError as error:
            if is_unauthorized(error):
                token_manager.refresh()
                print(
                    f"[{datetime.now().isoformat()}] room={room_id} Token expired, refreshed token",
                    flush=True,
                )
                continue
            print(
                f"[{datetime.now().isoformat()}] room={room_id} HTTP error: {error}",
                flush=True,
            )
        except requests.ConnectionError:
            print(
                f"[{datetime.now().isoformat()}] room={room_id} Cannot connect to backend",
                flush=True,
            )
        except Exception as error:
            print(
                f"[{datetime.now().isoformat()}] room={room_id} Unexpected error: {error}",
                flush=True,
            )

        sleep_time = INTERVAL_SECONDS + jitter.uniform(-0.25, 0.25)
        stop_event.wait(max(0.5, sleep_time))


def main() -> None:
    token_manager = TokenManager()
    token = token_manager.get()
    room_ids = get_room_ids(token)
    if not room_ids:
        raise RuntimeError("No rooms returned by backend")

    if RESET_HISTORY_ON_START:
        reset_sensor_history(token, room_ids)

    environments = {
        room_id: create_initial_environment(room_id)
        for room_id in room_ids
    }

    print("=" * 60)
    print(
        "Sensor simulator running "
        f"| rooms={len(room_ids)} | interval={INTERVAL_SECONDS}s"
    )
    print(f"Room IDs: {', '.join(str(room_id) for room_id in room_ids)}")
    print("It reacts to fan, air_conditioner and window state.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)
    print(flush=True)

    stop_event = threading.Event()
    threads = [
        threading.Thread(
            target=run_room_simulator,
            args=(token_manager, room_id, environments[room_id], stop_event),
            name=f"room-simulator-{room_id}",
            daemon=True,
        )
        for room_id in room_ids
    ]

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping room simulators...", flush=True)
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2)


if __name__ == "__main__":
    main()
