from app.repositories.alert_repository import alert_repository
from app.websocket.manager import ws_manager


class AlertService:
    async def list_all(self, db):
        return await alert_repository.get_all_ordered(db)

    async def create(self, db, room_id: int, level: str, message: str):
        alert = await alert_repository.create_alert(db, room_id, level, message)
        await ws_manager.broadcast_json(
            {
                "event": "new_alert",
                "alert": {
                    "id": alert.id,
                    "room_id": alert.room_id,
                    "level": alert.level,
                    "message": alert.message,
                    "status": alert.status,
                },
            }
        )
        return alert

    async def resolve(self, db, alert_id: int):
        alert = await alert_repository.get_by_id(db, alert_id)
        if not alert:
            raise ValueError("Alert not found")
        alert = await alert_repository.resolve(db, alert)
        await ws_manager.broadcast_json(
            {"event": "resolved_alert", "alert": {"id": alert.id, "status": alert.status}}
        )
        return alert


alert_service = AlertService()
