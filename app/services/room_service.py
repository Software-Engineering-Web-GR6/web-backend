from app.repositories.room_repository import room_repository
from app.repositories.rule_repository import rule_repository


class RoomService:
    async def list_all(self, db):
        return await room_repository.list_all(db)

    async def list_by_ids(self, db, room_ids: list[int]):
        return await room_repository.list_by_ids(db, room_ids)

    async def set_automation_mode(self, db, room_id: int, enabled: bool):
        room = await room_repository.get_by_id(db, room_id)
        if not room:
            raise ValueError("Room not found")
        updated_room = await room_repository.update(db, room, {"auto_control_enabled": enabled})
        await rule_repository.set_active_by_room(db, room_id, enabled)
        return updated_room


room_service = RoomService()
