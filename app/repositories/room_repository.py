from sqlalchemy import select
from sqlalchemy import func

from app.models.room import Room
from app.repositories.base import BaseRepository


class RoomRepository(BaseRepository):
    def __init__(self):
        super().__init__(Room)

    async def list_all(self, db):
        result = await db.execute(
            select(Room).order_by(Room.building.asc(), Room.name.asc(), Room.id.asc())
        )
        return list(result.scalars().all())

    async def list_by_ids(self, db, room_ids: list[int]):
        if not room_ids:
            return []
        result = await db.execute(
            select(Room)
            .where(Room.id.in_(room_ids))
            .order_by(Room.building.asc(), Room.name.asc(), Room.id.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, db, room_id: int):
        result = await db.execute(select(Room).where(Room.id == room_id))
        return result.scalar_one_or_none()

    async def update(self, db, room: Room, updates: dict):
        for key, value in updates.items():
            setattr(room, key, value)
        await db.commit()
        await db.refresh(room)
        return room

    async def get_by_name(self, db, room_name: str):
        result = await db.execute(select(Room).where(func.lower(Room.name) == room_name.strip().lower()))
        return result.scalar_one_or_none()


room_repository = RoomRepository()
