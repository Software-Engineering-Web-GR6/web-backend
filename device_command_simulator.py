"""
Device command simulator for Smart Classroom.

This script acts like a simple ESP32-side consumer:
- subscribes to device command topics from MQTT
- prints received commands
- publishes a lightweight acknowledgement topic

Run:
    python device_command_simulator.py
"""

from __future__ import annotations

import json
import os
import signal
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_DEVICE_COMMAND_TOPIC_PREFIX = os.getenv(
    "MQTT_DEVICE_COMMAND_TOPIC_PREFIX",
    "smartclassrooms/devices",
)

COMMAND_TOPIC = f"{MQTT_DEVICE_COMMAND_TOPIC_PREFIX}/+/+/commands"
STATUS_TOPIC_TEMPLATE = f"{MQTT_DEVICE_COMMAND_TOPIC_PREFIX}/{{room_id}}/{{device_id}}/status"

stop_event = threading.Event()


def build_status_payload(command_payload: dict) -> dict:
    payload = {
        "room_id": command_payload.get("room_id"),
        "device_id": command_payload.get("device_id"),
        "device_type": command_payload.get("device_type"),
        "status": "ACK",
        "received_command": command_payload.get("command"),
        "source": command_payload.get("source"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if "target_temp" in command_payload:
        payload["target_temp"] = command_payload["target_temp"]
    return payload


def on_connect(client: mqtt.Client, _userdata, _flags, rc: int) -> None:
    if rc != 0:
        print(f"MQTT connect failed with code {rc}", flush=True)
        return

    client.subscribe(COMMAND_TOPIC)
    print(
        f"Device command simulator connected | broker={MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} | topic={COMMAND_TOPIC}",
        flush=True,
    )


def on_message(client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except json.JSONDecodeError:
        print(f"Ignoring invalid command payload on {message.topic}", flush=True)
        return

    room_id = payload.get("room_id")
    device_id = payload.get("device_id")
    device_type = payload.get("device_type")
    command = payload.get("command")

    print(
        f"[{datetime.now().isoformat()}] room={room_id} device={device_id} type={device_type} command={command}",
        flush=True,
    )

    if room_id is None or device_id is None:
        return

    status_topic = STATUS_TOPIC_TEMPLATE.format(room_id=room_id, device_id=device_id)
    client.publish(status_topic, json.dumps(build_status_payload(payload)), qos=0)


def handle_shutdown(_signum=None, _frame=None) -> None:
    stop_event.set()


def main() -> None:
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    client = mqtt.Client(client_id="smart-classroom-device-simulator", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
    client.loop_start()

    print("Press Ctrl+C to stop device command simulator.", flush=True)
    stop_event.wait()

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
