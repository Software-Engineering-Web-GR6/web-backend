from sqlalchemy import select

from app.core.config import settings
from app.models.automation_rule import AutomationRule
from app.models.device import Device
from app.models.room import Room
from app.services.auth_service import auth_service

ROOM_SEED_DATA = [
    {"name": "Room A101", "building": "A", "location": "Building A - Floor 1"},
    {"name": "Room A102", "building": "A", "location": "Building A - Floor 1"},
    {"name": "Room A201", "building": "A", "location": "Building A - Floor 2"},
    {"name": "Room B101", "building": "B", "location": "Building B - Floor 1"},
    {"name": "Room B102", "building": "B", "location": "Building B - Floor 1"},
    {"name": "Room B201", "building": "B", "location": "Building B - Floor 2"},
    {"name": "Room E101", "building": "E", "location": "Building E - Floor 1"},
    {"name": "Room E201", "building": "E", "location": "Building E - Floor 2"},
]

DEVICE_TEMPLATES = [
    *[
        {"name": f"fan_{index:02d}", "device_type": "fan", "state": "OFF"}
        for index in range(1, 5)
    ],
    *[
        {"name": f"light_{index:02d}", "device_type": "light", "state": "OFF"}
        for index in range(1, 5)
    ],
    *[
        {"name": f"ac_{index:02d}", "device_type": "air_conditioner", "state": "OFF"}
        for index in range(1, 4)
    ],
]


async def seed_data(db):
    await auth_service.seed_admin_if_empty(db)

    room_result = await db.execute(select(Room))
    existing_rooms = {room.name: room for room in room_result.scalars().all()}

    for room_data in ROOM_SEED_DATA:
        room = existing_rooms.get(room_data["name"])
        if room is None:
            db.add(Room(**room_data))
        else:
            room.building = room_data["building"]
            room.location = room_data["location"]

    await db.commit()

    room_result = await db.execute(select(Room).order_by(Room.id.asc()))
    rooms = list(room_result.scalars().all())

    for room in rooms:
        device_result = await db.execute(select(Device).where(Device.room_id == room.id))
        devices = list(device_result.scalars().all())
        existing_by_name = {device.name: device for device in devices}

        # Migrate the old single window device to the first light device so the
        # existing database matches the current classroom equipment model.
        legacy_window = next((device for device in devices if device.device_type == "window"), None)
        if legacy_window:
            legacy_window.name = "light_01"
            legacy_window.device_type = "light"
            legacy_window.state = "OFF"
            existing_by_name["light_01"] = legacy_window

        for template in DEVICE_TEMPLATES:
            device = existing_by_name.get(template["name"])
            if device is None:
                db.add(
                    Device(
                        room_id=room.id,
                        name=template["name"],
                        device_type=template["device_type"],
                        state=template["state"],
                        is_online=True,
                    )
                )
                continue

            device.device_type = template["device_type"]
            device.is_online = True
            if device.state not in {"ON", "OFF"}:
                device.state = template["state"]

        await db.commit()
        device_result = await db.execute(select(Device).where(Device.room_id == room.id))
        devices = list(device_result.scalars().all())

        rule_result = await db.execute(select(AutomationRule).where(AutomationRule.room_id == room.id))
        rules = list(rule_result.scalars().all())
        if rules:
            continue

        first_fan = next((d for d in devices if d.device_type == "fan"), None)
        first_light = next((d for d in devices if d.device_type == "light"), None)
        db.add_all(
            [
                AutomationRule(
                    room_id=room.id,
                    name="Nhiệt độ cao bật quạt",
                    metric="temperature",
                    operator=">",
                    threshold_value=settings.DEFAULT_TEMP_WARNING,
                    target_device_id=first_fan.id if first_fan else None,
                    action="ON",
                    alert_level="MEDIUM",
                    alert_message=f"Nhiệt độ vượt {settings.DEFAULT_TEMP_WARNING}°C, hệ thống tự động bật quạt",
                    is_active=True,
                ),
                AutomationRule(
                    room_id=room.id,
                    name="CO2 cao bật đèn cảnh báo",
                    metric="co2",
                    operator=">",
                    threshold_value=settings.DEFAULT_CO2_WARNING,
                    target_device_id=first_light.id if first_light else None,
                    action="ON",
                    alert_level="HIGH",
                    alert_message=f"CO2 vượt ngưỡng an toàn ({settings.DEFAULT_CO2_WARNING}), hệ thống tự động bật đèn",
                    is_active=True,
                ),
            ]
        )
        await db.commit()
