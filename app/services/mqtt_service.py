import asyncio
import json
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import ensure_engine_initialized
from app.schemas.sensor import SensorReadingCreate
from app.services.sensor_service import sensor_service

logger = logging.getLogger(__name__)


class MQTTService:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False
        self._connected = False
        self._pending_acks: dict[str, asyncio.Future] = {}

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._started or not settings.MQTT_ENABLED:
            return

        self._loop = loop
        client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID, clean_session=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=10)

        try:
            client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                settings.MQTT_KEEPALIVE_SECONDS,
            )
            client.loop_start()
        except Exception:
            logger.warning(
                "MQTT subscriber could not connect at startup | host=%s port=%s",
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                exc_info=True,
            )
            return

        self._client = client
        self._started = True
        logger.info(
            "MQTT subscriber started | host=%s port=%s topic=%s",
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
            settings.MQTT_SENSOR_TOPIC,
        )

    def stop(self) -> None:
        if not self._client:
            return

        self._connected = False
        for future in self._pending_acks.values():
            if not future.done():
                future.cancel()
        self._pending_acks.clear()
        self._client.loop_stop()
        self._client.disconnect()
        self._client = None
        self._started = False
        logger.info("MQTT subscriber stopped")

    async def publish_device_command(
        self,
        *,
        room_id: int,
        device_id: int,
        device_type: str,
        command: str,
        source: str,
        target_temp: int | None = None,
    ) -> bool:
        if not settings.MQTT_ENABLED:
            return False

        if not self._client or not self._started or not self._connected or not self._loop:
            logger.info(
                "Skipping MQTT device command publish because MQTT client is not connected | device_id=%s command=%s",
                device_id,
                command,
            )
            return False

        topic = f"{settings.MQTT_DEVICE_COMMAND_TOPIC_PREFIX}/{room_id}/{device_id}/commands"
        payload = {
            "room_id": room_id,
            "device_id": device_id,
            "device_type": device_type,
            "command": command,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if target_temp is not None:
            payload["target_temp"] = target_temp

        ack_key = self._build_ack_key(room_id, device_id, command)
        ack_future = self._loop.create_future()
        self._pending_acks[ack_key] = ack_future

        message_info = self._client.publish(topic, json.dumps(payload), qos=0)
        logger.info(
            "Published MQTT device command | topic=%s device_id=%s command=%s result=%s",
            topic,
            device_id,
            command,
            message_info.rc,
        )
        if message_info.rc != mqtt.MQTT_ERR_SUCCESS:
            self._pending_acks.pop(ack_key, None)
            return False

        try:
            await asyncio.wait_for(ack_future, timeout=settings.MQTT_DEVICE_ACK_TIMEOUT_SECONDS)
            return True
        except TimeoutError:
            logger.warning(
                "Timed out waiting for MQTT device ACK | room_id=%s device_id=%s command=%s",
                room_id,
                device_id,
                command,
            )
            return False
        finally:
            self._pending_acks.pop(ack_key, None)

    def _on_connect(self, client: mqtt.Client, _userdata, _flags, rc: int) -> None:
        if rc != 0:
            logger.error("MQTT connect failed with code %s", rc)
            return

        self._connected = True
        client.subscribe(settings.MQTT_SENSOR_TOPIC)
        client.subscribe(f"{settings.MQTT_DEVICE_COMMAND_TOPIC_PREFIX}/+/+/status")
        logger.info(
            "Subscribed to MQTT topics %s and %s/+/+/status",
            settings.MQTT_SENSOR_TOPIC,
            settings.MQTT_DEVICE_COMMAND_TOPIC_PREFIX,
        )

    def _on_disconnect(self, _client: mqtt.Client, _userdata, rc: int) -> None:
        self._connected = False
        if rc != 0:
            logger.warning("MQTT disconnected unexpectedly with code %s", rc)

    def _on_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        if not self._loop:
            logger.warning("Ignoring MQTT message because event loop is not ready")
            return

        payload_text = message.payload.decode("utf-8", errors="ignore")
        future = asyncio.run_coroutine_threadsafe(
            self._dispatch_message(message.topic, payload_text),
            self._loop,
        )
        future.add_done_callback(self._log_task_error)

    def _log_task_error(self, future) -> None:
        exc = future.exception()
        if exc:
            logger.exception("MQTT message processing failed", exc_info=exc)

    async def _dispatch_message(self, topic: str, payload_text: str) -> None:
        if topic == settings.MQTT_SENSOR_TOPIC:
            await self._process_sensor_message(payload_text)
            return

        status_prefix = f"{settings.MQTT_DEVICE_COMMAND_TOPIC_PREFIX}/"
        if topic.startswith(status_prefix) and topic.endswith("/status"):
            await self._process_status_message(payload_text)
            return

        logger.debug("Ignoring MQTT message for unhandled topic %s", topic)

    async def _process_sensor_message(self, payload_text: str) -> None:
        try:
            payload = SensorReadingCreate.model_validate(json.loads(payload_text))
        except (json.JSONDecodeError, ValidationError):
            logger.warning("Ignoring invalid MQTT payload: %s", payload_text)
            return

        _, session_factory = ensure_engine_initialized()
        async with session_factory() as session:
            reading, executed = await sensor_service.ingest(session, payload)
            logger.info(
                "Ingested MQTT sensor reading | room_id=%s reading_id=%s executed_rules=%s",
                reading.room_id,
                reading.id,
                len(executed),
            )

    async def _process_status_message(self, payload_text: str) -> None:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid MQTT status payload: %s", payload_text)
            return

        ack_key = self._build_ack_key(
            payload.get("room_id"),
            payload.get("device_id"),
            payload.get("received_command"),
        )
        future = self._pending_acks.get(ack_key)
        if future and not future.done():
            future.set_result(payload)

    @staticmethod
    def _build_ack_key(room_id, device_id, command) -> str:
        return f"{room_id}:{device_id}:{command}"


mqtt_service = MQTTService()
