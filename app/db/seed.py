from sqlalchemy import select
from app.models.room import Room
from app.models.device import Device
from app.models.automation_rule import AutomationRule
from app.services.auth_service import auth_service
from app.core.config import settings


async def seed_data(db):
    await auth_service.seed_admin_if_empty(db)

    room_result = await db.execute(select(Room).limit(1))
    room = room_result.scalar_one_or_none()
    if not room:
        room = Room(name="Room A101", location="Building A - Floor 1")
        db.add(room)
        await db.commit()
        await db.refresh(room)

    device_result = await db.execute(select(Device).where(Device.room_id == room.id))
    devices = list(device_result.scalars().all())
    if not devices:
        fan = Device(room_id=room.id, name="fan_01", device_type="fan", state="OFF", is_online=True)
        ac = Device(room_id=room.id, name="ac_01", device_type="air_conditioner", state="OFF", is_online=True)
        window = Device(room_id=room.id, name="window_01", device_type="window", state="CLOSE", is_online=True)
        db.add_all([fan, ac, window])
        await db.commit()
        await db.refresh(fan)
        await db.refresh(ac)
        await db.refresh(window)
        devices = [fan, ac, window]

    rule_result = await db.execute(select(AutomationRule).where(AutomationRule.room_id == room.id))
    rules = list(rule_result.scalars().all())
    if not rules:
        first_fan = next((d for d in devices if d.device_type == "fan"), None)
        first_window = next((d for d in devices if d.device_type == "window"), None)
        db.add_all([
            AutomationRule(
                room_id=room.id,
                name="High temperature turns on fan",
                metric="temperature",
                operator=">",
                threshold_value=settings.DEFAULT_TEMP_WARNING,
                target_device_id=first_fan.id if first_fan else None,
                action="ON",
                alert_level="MEDIUM",
                alert_message=f"Nhiệt độ vượt {settings.DEFAULT_TEMP_WARNING}°C, bật quạt tự động",
                is_active=True,
            ),
            AutomationRule(
                room_id=room.id,
                name="High CO2 opens window",
                metric="co2",
                operator=">",
                threshold_value=settings.DEFAULT_CO2_WARNING,
                target_device_id=first_window.id if first_window else None,
                action="OPEN",
                alert_level="HIGH",
                alert_message=f"CO2 vượt ngưỡng an toàn ({settings.DEFAULT_CO2_WARNING}), mở cửa sổ",
                is_active=True,
            ),
        ])
        await db.commit()
