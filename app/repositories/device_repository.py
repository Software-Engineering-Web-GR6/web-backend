from datetime import datetime, timezone
from sqlalchemy import select
from app.models.device import Device
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository):
    def __init__(self):
        super().__init__(Device)

    async def get_by_room(self, db, room_id: int):
        result = await db.execute(
            select(Device)
            .where(Device.room_id == room_id)
            .order_by(Device.device_type.asc(), Device.name.asc(), Device.id.asc())
        )
        return list(result.scalars().all())

    async def update_state(self, db, device: Device, state: str):
        device.state = state
        device.last_updated = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(device)
        return device


device_repository = DeviceRepository()
