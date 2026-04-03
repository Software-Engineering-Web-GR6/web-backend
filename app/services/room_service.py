from app.repositories.room_repository import room_repository
from app.repositories.rule_repository import rule_repository
from app.services.room_defaults import ensure_room_devices_and_rules


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

    async def create_room(self, db, *, name: str, building: str, location: str | None):
        normalized_name = name.strip()
        normalized_building = building.strip().upper()
        normalized_location = location.strip() if location else None

        existing_room = await room_repository.get_by_name(db, normalized_name)
        if existing_room:
            raise ValueError("Room name already exists")

        room = await room_repository.create(
            db,
            name=normalized_name,
            building=normalized_building,
            location=normalized_location,
            auto_control_enabled=True,
        )
        await ensure_room_devices_and_rules(db, room)
        return room


room_service = RoomService()
