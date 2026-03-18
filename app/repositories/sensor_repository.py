from sqlalchemy import select, func
from app.models.sensor_reading import SensorReading
from app.repositories.base import BaseRepository


class SensorRepository(BaseRepository):
    def __init__(self):
        super().__init__(SensorReading)

    async def get_latest(self, db, room_id: int):
        result = await db.execute(
            select(SensorReading)
            .where(SensorReading.room_id == room_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(self, db, room_id: int, limit: int = 50):
        result = await db.execute(
            select(SensorReading)
            .where(SensorReading.room_id == room_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_avg(self, db, room_id: int):
        result = await db.execute(
            select(
                func.avg(SensorReading.temperature),
                func.avg(SensorReading.humidity),
                func.avg(SensorReading.co2),
            ).where(SensorReading.room_id == room_id)
        )
        row = result.one()
        return {
            "avg_temperature": row[0],
            "avg_humidity": row[1],
            "avg_co2": row[2],
        }


sensor_repository = SensorRepository()
