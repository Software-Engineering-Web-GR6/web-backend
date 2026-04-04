from datetime import datetime, timezone
from app.repositories.room_repository import room_repository
from app.repositories.sensor_repository import sensor_repository
from app.repositories.rule_repository import rule_repository
from app.domain.automation_engine import automation_engine
from app.services.alert_service import alert_service
from app.services.device_service import device_service
from app.websocket.manager import ws_manager


class SensorService:
    async def ingest(self, db, payload):
        data = payload.model_dump()
        recorded_at = data.get("recorded_at")
        if recorded_at is None:
            data["recorded_at"] = datetime.now(timezone.utc)
        elif recorded_at.tzinfo is None:
            data["recorded_at"] = recorded_at.replace(tzinfo=timezone.utc)
        reading = await sensor_repository.create(db, **data)
        room = await room_repository.get_by_id(db, payload.room_id)
        executed = []
        if room is not None and room.auto_control_enabled:
            rules = await rule_repository.get_active_rules_by_room(db, payload.room_id)
            executed = await automation_engine.evaluate_rules(
                reading=reading,
                rules=rules,
                alert_service=alert_service,
                device_service=device_service,
                db=db,
            )
        await ws_manager.broadcast_json(
            {
                "event": "sensor_reading",
                "reading": {
                    "id": reading.id,
                    "room_id": reading.room_id,
                    "temperature": reading.temperature,
                    "humidity": reading.humidity,
                    "co2": reading.co2,
                    "motion_detected": reading.motion_detected,
                    "recorded_at": reading.recorded_at.isoformat(),
                },
                "executed_rules": executed,
            }
        )
        return reading, executed

    async def get_latest(self, db, room_id: int):
        return await sensor_repository.get_latest(db, room_id)

    async def get_history(self, db, room_id: int, limit: int = 50):
        return await sensor_repository.get_history(db, room_id, limit)

    async def clear_history(self, db, room_ids: list[int] | None = None):
        return await sensor_repository.clear_history(db, room_ids)

    async def get_dashboard(self, db, room_id: int):
        latest = await sensor_repository.get_latest(db, room_id)
        history = await sensor_repository.get_history(db, room_id, 10)
        averages = await sensor_repository.get_avg(db, room_id)
        devices = await device_service.get_by_room(db, room_id)
        unresolved_alerts = [a for a in await alert_service.list_all(db) if a.room_id == room_id and a.status != "RESOLVED"]
        return {
            "room_id": room_id,
            "latest": latest,
            "history": history,
            "averages": averages,
            "devices": devices,
            "unresolved_alerts": unresolved_alerts,
        }


sensor_service = SensorService()
