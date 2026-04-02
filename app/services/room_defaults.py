from sqlalchemy import select

from app.core.config import settings
from app.models.automation_rule import AutomationRule
from app.models.device import Device
from app.models.room import Room

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


async def ensure_room_devices_and_rules(db, room: Room) -> None:
    device_result = await db.execute(select(Device).where(Device.room_id == room.id))
    devices = list(device_result.scalars().all())
    existing_by_name = {device.name: device for device in devices}

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
    devices_by_id = {device.id: device for device in devices}

    first_fan = next((device for device in devices if device.device_type == "fan"), None)
    rule_result = await db.execute(select(AutomationRule).where(AutomationRule.room_id == room.id))
    rules = list(rule_result.scalars().all())

    if rules:
        co2_rule = next(
            (
                rule
                for rule in rules
                if rule.metric == "co2"
                and rule.operator == ">"
                and rule.threshold_value == settings.DEFAULT_CO2_WARNING
                and rule.action == "ON"
            ),
            None,
        )
        if co2_rule and first_fan:
            current_target = devices_by_id.get(co2_rule.target_device_id)
            if current_target is None or current_target.device_type == "light":
                co2_rule.target_device_id = first_fan.id
                co2_rule.name = "CO2 cao bat quat"
                co2_rule.alert_message = (
                    f"CO2 vuot nguong an toan ({settings.DEFAULT_CO2_WARNING}), "
                    "he thong tu dong bat quat"
                )
                await db.commit()
        return

    db.add_all(
        [
            AutomationRule(
                room_id=room.id,
                name="Nhiet do cao bat quat",
                metric="temperature",
                operator=">",
                threshold_value=settings.DEFAULT_TEMP_WARNING,
                target_device_id=first_fan.id if first_fan else None,
                action="ON",
                alert_level="MEDIUM",
                alert_message=(
                    f"Nhiet do vuot {settings.DEFAULT_TEMP_WARNING}C, "
                    "he thong tu dong bat quat"
                ),
                is_active=True,
            ),
            AutomationRule(
                room_id=room.id,
                name="CO2 cao bat quat",
                metric="co2",
                operator=">",
                threshold_value=settings.DEFAULT_CO2_WARNING,
                target_device_id=first_fan.id if first_fan else None,
                action="ON",
                alert_level="HIGH",
                alert_message=(
                    f"CO2 vuot nguong an toan ({settings.DEFAULT_CO2_WARNING}), "
                    "he thong tu dong bat quat"
                ),
                is_active=True,
            ),
        ]
    )
    await db.commit()
