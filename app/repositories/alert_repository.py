from datetime import datetime
from sqlalchemy import select
from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository):
    def __init__(self):
        super().__init__(Alert)

    async def get_unresolved(self, db):
        result = await db.execute(select(Alert).where(Alert.status != "RESOLVED").order_by(Alert.created_at.desc()))
        return list(result.scalars().all())

    async def get_all_ordered(self, db):
        result = await db.execute(select(Alert).order_by(Alert.created_at.desc()))
        return list(result.scalars().all())

    async def create_alert(self, db, room_id: int, level: str, message: str):
        return await self.create(db, room_id=room_id, level=level, message=message, status="OPEN")

    async def resolve(self, db, alert: Alert):
        alert.status = "RESOLVED"
        alert.resolved_at = datetime.utcnow()
        await db.commit()
        await db.refresh(alert)
        return alert


alert_repository = AlertRepository()
