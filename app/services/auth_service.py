from sqlalchemy import select
from app.models.user import User
from app.models.room import Room
from app.models.user_room_shift_access import UserRoomShiftAccess
from app.core.security import verify_password, create_access_token, hash_password


class AuthService:
    async def get_user_by_id(self, db, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def login(self, db, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})

    async def seed_admin_if_empty(self, db):
        result = await db.execute(select(User).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        user = User(
            full_name="System Admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def create_user(self, db, full_name: str, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("Email already exists")
        
        user = User(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def change_password(self, db, user_id: int, current_password: str, new_password: str):
        user = await self.get_user_by_id(db, user_id)
        if not user:
            raise ValueError("User not found")
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        if current_password == new_password:
            raise ValueError("New password must be different from current password")

        user.password_hash = hash_password(new_password)
        await db.commit()
        await db.refresh(user)
        return user

    async def list_users(self, db):
        result = await db.execute(select(User).order_by(User.id.asc()))
        return result.scalars().all()

    async def delete_user(self, db, user_id: int):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        await db.delete(user)
        await db.commit()

    async def grant_room_shift_access(self, db, user_id: int, room_id: int, shifts: list[int], days_of_week: list[int]):
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        room_result = await db.execute(select(Room).where(Room.id == room_id))
        room = room_result.scalar_one_or_none()
        if not room:
            raise ValueError("Room not found")

        normalized_shifts = sorted(set(shifts))
        if any(shift < 1 or shift > 6 for shift in normalized_shifts):
            raise ValueError("Shift must be between 1 and 6")

        normalized_days = sorted(set(days_of_week))
        if any(day < 0 or day > 6 for day in normalized_days):
            raise ValueError("Day of week must be between 0 (Monday) and 6 (Sunday)")

        granted = []
        for shift in normalized_shifts:
            for day in normalized_days:
                occupied_result = await db.execute(
                    select(UserRoomShiftAccess).where(
                        UserRoomShiftAccess.user_id != user_id,
                        UserRoomShiftAccess.room_id == room_id,
                        UserRoomShiftAccess.shift_number == shift,
                        UserRoomShiftAccess.day_of_week == day,
                    )
                )
                occupied = occupied_result.scalar_one_or_none()
                if occupied:
                    raise ValueError(
                        f"Room {room_id} already has a schedule entry for shift {shift} on day {day}"
                    )

                existing_result = await db.execute(
                    select(UserRoomShiftAccess).where(
                        UserRoomShiftAccess.user_id == user_id,
                        UserRoomShiftAccess.room_id == room_id,
                        UserRoomShiftAccess.shift_number == shift,
                        UserRoomShiftAccess.day_of_week == day,
                    )
                )
                existing = existing_result.scalar_one_or_none()
                if existing:
                    granted.append(existing)
                    continue

                access = UserRoomShiftAccess(user_id=user_id, room_id=room_id, shift_number=shift, day_of_week=day)
                db.add(access)
                await db.flush()
                granted.append(access)

        await db.commit()
        for access in granted:
            await db.refresh(access)
        return granted

    async def assign_user_schedule(self, db, user_id: int, room_id: int, shifts: list[int], days_of_week: list[int]):
        return await self.grant_room_shift_access(db, user_id, room_id, shifts, days_of_week)

    async def list_room_shift_access(self, db, user_id: int):
        result = await db.execute(
            select(UserRoomShiftAccess)
            .where(UserRoomShiftAccess.user_id == user_id)
            .order_by(UserRoomShiftAccess.room_id.asc(), UserRoomShiftAccess.shift_number.asc())
        )
        return list(result.scalars().all())

    async def list_user_schedule(self, db, user_id: int):
        return await self.list_room_shift_access(db, user_id)

    async def list_room_occupancy(self, db, room_id: int):
        result = await db.execute(
            select(UserRoomShiftAccess)
            .where(UserRoomShiftAccess.room_id == room_id)
            .order_by(UserRoomShiftAccess.day_of_week.asc(), UserRoomShiftAccess.shift_number.asc())
        )
        return list(result.scalars().all())

    async def list_room_schedule(self, db, room_id: int):
        return await self.list_room_occupancy(db, room_id)

    async def revoke_room_shift_access(self, db, user_id: int, room_id: int, shift_number: int, day_of_week: int):
        result = await db.execute(
            select(UserRoomShiftAccess).where(
                UserRoomShiftAccess.user_id == user_id,
                UserRoomShiftAccess.room_id == room_id,
                UserRoomShiftAccess.shift_number == shift_number,
                UserRoomShiftAccess.day_of_week == day_of_week,
            )
        )
        access = result.scalar_one_or_none()
        if not access:
            raise ValueError("Schedule entry not found")

        await db.delete(access)
        await db.commit()

    async def remove_user_schedule_entry(self, db, user_id: int, room_id: int, shift_number: int, day_of_week: int):
        await self.revoke_room_shift_access(db, user_id, room_id, shift_number, day_of_week)
     
auth_service = AuthService()
