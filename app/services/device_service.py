from app.repositories.device_repository import device_repository
from app.repositories.action_log_repository import action_log_repository


class DeviceService:
    async def get_by_room(self, db, room_id: int):
        return await device_repository.get_by_room(db, room_id)

    async def control(self, db, device_id: int, action: str, source: str = "MANUAL", description: str = "Manual control"):
        device = await device_repository.get_by_id(db, device_id)
        if not device:
            raise ValueError("Device not found")
        if action not in {"ON", "OFF", "OPEN", "CLOSE"}:
            raise ValueError("Invalid action")
        updated = await device_repository.update_state(db, device, action)
        await action_log_repository.create(
            db,
            room_id=updated.room_id,
            device_id=updated.id,
            action=action,
            source=source,
            description=description,
        )
        return updated

    async def update_temperature(self, db, device_id: int, target_temp: int):
        device = await device_repository.get_by_id(db, device_id)
        if not device:
            raise ValueError("Device not found")
        if device.device_type != "air_conditioner":
            raise ValueError("Only air conditioners support target temperature")
        if target_temp < 16 or target_temp > 30:
            raise ValueError("Target temperature must be between 16 and 30")

        updated = await device_repository.update_target_temp(db, device, target_temp)
        await action_log_repository.create(
            db,
            room_id=updated.room_id,
            device_id=updated.id,
            action=f"SET_TEMP_{target_temp}",
            source="MANUAL",
            description=f"Set AC target temperature to {target_temp}C",
        )
        return updated


device_service = DeviceService()
