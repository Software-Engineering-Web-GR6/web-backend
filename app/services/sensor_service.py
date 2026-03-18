from datetime import datetime
from app.repositories.sensor_repository import sensor_repository
from app.repositories.rule_repository import rule_repository
from app.domain.automation_engine import automation_engine
from app.services.alert_service import alert_service
from app.services.device_service import device_service


class SensorService:
    async def ingest(self, db, payload):
        data = payload.model_dump()
        if data.get("recorded_at") is None:
            data["recorded_at"] = datetime.utcnow()
        reading = await sensor_repository.create(db, **data)
        rules = await rule_repository.get_active_rules_by_room(db, payload.room_id)
        executed = await automation_engine.evaluate_rules(
            reading=reading,
            rules=rules,
            alert_service=alert_service,
            device_service=device_service,
            db=db,
        )
        return reading, executed

    async def get_latest(self, db, room_id: int):
        return await sensor_repository.get_latest(db, room_id)

    async def get_history(self, db, room_id: int, limit: int = 50):
        return await sensor_repository.get_history(db, room_id, limit)

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
