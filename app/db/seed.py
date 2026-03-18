from sqlalchemy import select

from app.models.room import Room
from app.models.device import Device
from app.models.automation_rule import AutomationRule
from app.models.sensor_reading import SensorReading
from app.models.alert import Alert
from app.services.auth_service import auth_service


async def seed_data(db):
    await auth_service.seed_admin_if_empty(db)

    # 1. Seed room cố định, không bị trùng
    room_name = "Room A101"
    room_location = "Building A - Floor 1"

    room_result = await db.execute(
        select(Room).where(Room.name == room_name)
    )
    room = room_result.scalar_one_or_none()

    if not room:
        room = Room(name=room_name, location=room_location)
        db.add(room)
        await db.commit()
        await db.refresh(room)

    # 2. Seed devices theo từng tên, không seed trùng
    device_seeds = [
        {"name": "fan_01", "device_type": "fan", "state": "OFF", "is_online": True},
        {"name": "ac_01", "device_type": "air_conditioner", "state": "OFF", "is_online": True},
        {"name": "window_01", "device_type": "window", "state": "CLOSE", "is_online": True},
    ]

    devices = []
    for device_seed in device_seeds:
        device_result = await db.execute(
            select(Device).where(
                Device.room_id == room.id,
                Device.name == device_seed["name"]
            )
        )
        existing_device = device_result.scalar_one_or_none()

        if not existing_device:
            existing_device = Device(
                room_id=room.id,
                name=device_seed["name"],
                device_type=device_seed["device_type"],
                state=device_seed["state"],
                is_online=device_seed["is_online"],
            )
            db.add(existing_device)
            await db.commit()
            await db.refresh(existing_device)

        devices.append(existing_device)

    fan = next((d for d in devices if d.device_type == "fan"), None)
    window = next((d for d in devices if d.device_type == "window"), None)

    # 3. Seed rules theo từng tên, không seed trùng
    rule_seeds = [
        {
            "name": "High temperature turns on fan",
            "metric": "temperature",
            "operator": ">",
            "threshold_value": 30,
            "target_device_id": fan.id if fan else None,
            "action": "ON",
            "alert_level": "MEDIUM",
            "alert_message": "Nhiệt độ vượt 30°C, bật quạt tự động",
            "is_active": True,
        },
        {
            "name": "High CO2 opens window",
            "metric": "co2",
            "operator": ">",
            "threshold_value": 1000,
            "target_device_id": window.id if window else None,
            "action": "OPEN",
            "alert_level": "HIGH",
            "alert_message": "CO2 vượt ngưỡng an toàn, mở cửa sổ",
            "is_active": True,
        },
    ]

    for rule_seed in rule_seeds:
        rule_result = await db.execute(
            select(AutomationRule).where(
                AutomationRule.room_id == room.id,
                AutomationRule.name == rule_seed["name"]
            )
        )
        existing_rule = rule_result.scalar_one_or_none()

        if not existing_rule:
            new_rule = AutomationRule(
                room_id=room.id,
                name=rule_seed["name"],
                metric=rule_seed["metric"],
                operator=rule_seed["operator"],
                threshold_value=rule_seed["threshold_value"],
                target_device_id=rule_seed["target_device_id"],
                action=rule_seed["action"],
                alert_level=rule_seed["alert_level"],
                alert_message=rule_seed["alert_message"],
                is_active=rule_seed["is_active"],
            )
            db.add(new_rule)

    await db.commit()

    # 4. Seed sensor reading mẫu nếu chưa có
    sensor_result = await db.execute(
        select(SensorReading).where(SensorReading.room_id == room.id).limit(1)
    )
    existing_sensor = sensor_result.scalar_one_or_none()

    if not existing_sensor:
        sensor_samples = [
            SensorReading(
                room_id=room.id,
                temperature=28,
                humidity=60,
                co2=700,
                motion_detected=False,
            ),
            SensorReading(
                room_id=room.id,
                temperature=31,
                humidity=65,
                co2=950,
                motion_detected=True,
            ),
            SensorReading(
                room_id=room.id,
                temperature=35,
                humidity=70,
                co2=1200,
                motion_detected=True,
            ),
        ]
        db.add_all(sensor_samples)
        await db.commit()

    # 5. Seed alert mẫu nếu chưa có alert nào cho room
    alert_result = await db.execute(
        select(Alert).where(Alert.room_id == room.id).limit(1)
    )
    existing_alert = alert_result.scalar_one_or_none()

    if not existing_alert:
        sample_alert = Alert(
    room_id=room.id,
    alert_type="TEMPERATURE",
    level="HIGH",
    message="Nhiệt độ phòng đang vượt ngưỡng an toàn",
    status="OPEN",
)
        db.add(sample_alert)
        await db.commit()