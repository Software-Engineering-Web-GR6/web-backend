from sqlalchemy import select

from app.core.security import hash_password
from app.models.room import Room
from app.models.user import User
from app.models.user_room_shift_access import UserRoomShiftAccess
from app.services.auth_service import auth_service
from app.services.room_defaults import ensure_room_devices_and_rules

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

DEMO_USERS = [
    {
        "full_name": "Nguyen Van User",
        "email": "demo.user1@example.com",
        "password": "user12345",
        "role": "user",
        "schedule": [
            {"room_name": "Room A101", "day_of_week": 0, "shift_number": 1},
            {"room_name": "Room A102", "day_of_week": 0, "shift_number": 2},
            {"room_name": "Room B101", "day_of_week": 2, "shift_number": 3},
            {"room_name": "Room A101", "day_of_week": 4, "shift_number": 2},
            {"room_name": "Room E101", "day_of_week": 4, "shift_number": 3},
        ],
    },
    {
        "full_name": "Tran Thi Test",
        "email": "demo.user2@example.com",
        "password": "user12345",
        "role": "user",
        "schedule": [
            {"room_name": "Room B102", "day_of_week": 1, "shift_number": 1},
            {"room_name": "Room E201", "day_of_week": 1, "shift_number": 2},
            {"room_name": "Room A201", "day_of_week": 3, "shift_number": 4},
            {"room_name": "Room B201", "day_of_week": 4, "shift_number": 4},
            {"room_name": "Room E201", "day_of_week": 5, "shift_number": 1},
        ],
    },
]


async def seed_demo_users_and_schedules(db, rooms: list[Room]) -> None:
    room_by_name = {room.name: room for room in rooms}

    existing_users_result = await db.execute(select(User))
    existing_users = {user.email: user for user in existing_users_result.scalars().all()}

    for user_seed in DEMO_USERS:
        user = existing_users.get(user_seed["email"])
        if user is None:
            user = User(
                full_name=user_seed["full_name"],
                email=user_seed["email"],
                password_hash=hash_password(user_seed["password"]),
                role=user_seed["role"],
            )
            db.add(user)
            await db.flush()
            existing_users[user.email] = user
        else:
            user.full_name = user_seed["full_name"]
            user.password_hash = hash_password(user_seed["password"])
            user.role = user_seed["role"]

        existing_schedule_result = await db.execute(
            select(UserRoomShiftAccess).where(UserRoomShiftAccess.user_id == user.id)
        )
        existing_schedule = list(existing_schedule_result.scalars().all())
        existing_by_slot = {
            (item.room_id, item.day_of_week, item.shift_number): item for item in existing_schedule
        }

        desired_slots = set()
        for entry in user_seed["schedule"]:
            room = room_by_name.get(entry["room_name"])
            if room is None:
                continue

            slot_key = (room.id, entry["day_of_week"], entry["shift_number"])
            desired_slots.add(slot_key)
            if slot_key in existing_by_slot:
                continue

            db.add(
                UserRoomShiftAccess(
                    user_id=user.id,
                    room_id=room.id,
                    day_of_week=entry["day_of_week"],
                    shift_number=entry["shift_number"],
                )
            )

        for slot_key, schedule_entry in existing_by_slot.items():
            if slot_key not in desired_slots:
                await db.delete(schedule_entry)

    await db.commit()


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

    await seed_demo_users_and_schedules(db, rooms)

    for room in rooms:
        await ensure_room_devices_and_rules(db, room)
