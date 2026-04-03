from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import delete, func, select
from app.models.user import User
from app.models.room import Room
from app.models.user_room_shift_access import UserRoomShiftAccess
from app.models.password_reset_code import PasswordResetCode
from app.core.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.services.mail_service import mail_service


class AuthService:
    _email_adapter = TypeAdapter(EmailStr)

    def _normalized_email(self, email: str) -> str:
        return email.strip().lower()

    def _get_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _parse_import_email(self, value: Any) -> str:
        email = self._get_text(value)
        try:
            normalized = self._email_adapter.validate_python(email)
        except ValidationError as exc:
            raise ValueError("Invalid email") from exc
        return self._normalized_email(str(normalized))

    def _parse_import_integer(self, value: Any, *, field_name: str, minimum: int, maximum: int) -> int:
        try:
            parsed = int(str(value).strip())
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError(f"{field_name} must be an integer between {minimum} and {maximum}") from exc

        if parsed < minimum or parsed > maximum:
            raise ValueError(f"{field_name} must be an integer between {minimum} and {maximum}")
        return parsed

    def _validate_import_user_row(self, item: dict[str, Any]) -> dict[str, str]:
        full_name = self._get_text(item.get("full_name") or item.get("name"))
        email = self._parse_import_email(item.get("email"))
        password = self._get_text(item.get("password"))

        if len(full_name) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(full_name) > 100:
            raise ValueError("Full name must not exceed 100 characters")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(password) > 128:
            raise ValueError("Password must not exceed 128 characters")

        return {
            "full_name": full_name,
            "email": email,
            "password": password,
        }

    def _validate_import_schedule_row(self, item: dict[str, Any]) -> dict[str, str | int]:
        email = self._parse_import_email(item.get("email"))
        room_name = self._get_text(item.get("room_name") or item.get("room"))

        if len(room_name) < 3:
            raise ValueError("Room name must be at least 3 characters")
        if len(room_name) > 100:
            raise ValueError("Room name must not exceed 100 characters")

        day_of_week = self._parse_import_integer(
            item.get("day_of_week"),
            field_name="day_of_week",
            minimum=0,
            maximum=6,
        )
        shift_number = self._parse_import_integer(
            item.get("shift_number"),
            field_name="shift_number",
            minimum=1,
            maximum=6,
        )

        return {
            "email": email,
            "room_name": room_name,
            "day_of_week": day_of_week,
            "shift_number": shift_number,
        }

    def _hash_reset_code(self, email: str, code: str) -> str:
        payload = f"{self._normalized_email(email)}:{code}:{settings.SECRET_KEY}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _generate_reset_code(self) -> str:
        digits = max(4, settings.PASSWORD_RESET_CODE_LENGTH)
        lower_bound = 10 ** (digits - 1)
        upper_bound = (10 ** digits) - 1
        return str(secrets.randbelow(upper_bound - lower_bound + 1) + lower_bound)

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
        normalized_email = self._normalized_email(email)
        result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("Email already exists")
        
        user = User(
            full_name=full_name,
            email=normalized_email,
            password_hash=hash_password(password),
            role="user",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def import_users(self, db, items: list[dict]):
        results = []
        created_count = 0

        for index, item in enumerate(items, start=1):
            try:
                validated = self._validate_import_user_row(item)
                user = await self.create_user(
                    db,
                    full_name=validated["full_name"],
                    email=validated["email"],
                    password=validated["password"],
                )
                created_count += 1
                results.append(
                    {
                        "row_number": index,
                        "success": True,
                        "message": "User created successfully",
                        "email": user.email,
                        "user_id": user.id,
                    }
                )
            except ValueError as exc:
                results.append(
                    {
                        "row_number": index,
                        "success": False,
                        "message": str(exc),
                        "email": self._get_text(item.get("email")) or None,
                    }
                )

        return {
            "created_count": created_count,
            "failed_count": len(results) - created_count,
            "results": results,
        }

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

    async def request_password_reset(self, db, email: str):
        normalized_email = self._normalized_email(email)
        result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
        user = result.scalar_one_or_none()
        if not user:
            return

        await db.execute(
            delete(PasswordResetCode).where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.used_at.is_(None),
            )
        )

        code = self._generate_reset_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES)

        db.add(
            PasswordResetCode(
                user_id=user.id,
                email=normalized_email,
                code_hash=self._hash_reset_code(normalized_email, code),
                attempts=0,
                expires_at=expires_at,
            )
        )

        try:
            await mail_service.send_password_reset_code(
                to_email=normalized_email,
                code=code,
                expires_minutes=settings.PASSWORD_RESET_CODE_EXPIRE_MINUTES,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    async def _get_active_reset_code(self, db, email: str) -> PasswordResetCode | None:
        normalized_email = self._normalized_email(email)
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PasswordResetCode)
            .where(
                PasswordResetCode.email == normalized_email,
                PasswordResetCode.used_at.is_(None),
                PasswordResetCode.expires_at > now,
                PasswordResetCode.attempts < settings.PASSWORD_RESET_MAX_ATTEMPTS,
            )
            .order_by(PasswordResetCode.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def verify_password_reset_code(self, db, email: str, code: str):
        reset_entry = await self._get_active_reset_code(db, email)
        if not reset_entry:
            raise ValueError("Invalid or expired verification code")

        expected_hash = self._hash_reset_code(email, code)
        if reset_entry.code_hash != expected_hash:
            reset_entry.attempts += 1
            await db.commit()
            raise ValueError("Invalid or expired verification code")

    async def reset_password_with_code(self, db, email: str, code: str, new_password: str):
        normalized_email = self._normalized_email(email)
        user_result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("Invalid or expired verification code")

        reset_entry = await self._get_active_reset_code(db, normalized_email)
        if not reset_entry:
            raise ValueError("Invalid or expired verification code")

        expected_hash = self._hash_reset_code(normalized_email, code)
        if reset_entry.code_hash != expected_hash:
            reset_entry.attempts += 1
            await db.commit()
            raise ValueError("Invalid or expired verification code")

        if verify_password(new_password, user.password_hash):
            raise ValueError("New password must be different from current password")

        user.password_hash = hash_password(new_password)
        reset_entry.used_at = datetime.now(timezone.utc)

        await db.execute(
            delete(PasswordResetCode).where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.id != reset_entry.id,
            )
        )
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

    async def import_user_schedule(self, db, items: list[dict]):
        results = []
        created_count = 0

        for index, item in enumerate(items, start=1):
            try:
                validated = self._validate_import_schedule_row(item)
            except ValueError as exc:
                results.append(
                    {
                        "row_number": index,
                        "success": False,
                        "message": str(exc),
                        "email": self._get_text(item.get("email")) or None,
                        "room_name": self._get_text(item.get("room_name") or item.get("room")) or None,
                    }
                )
                continue

            normalized_email = str(validated["email"])
            room_name = str(validated["room_name"])

            user_result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
            user = user_result.scalar_one_or_none()
            if not user:
                results.append(
                    {
                        "row_number": index,
                        "success": False,
                        "message": "User not found",
                        "email": normalized_email,
                        "room_name": room_name,
                    }
                )
                continue

            room_result = await db.execute(select(Room).where(func.lower(Room.name) == room_name.lower()))
            room = room_result.scalar_one_or_none()
            if not room:
                results.append(
                    {
                        "row_number": index,
                        "success": False,
                        "message": "Room not found",
                        "email": normalized_email,
                        "room_name": room_name,
                        "user_id": user.id,
                    }
                )
                continue

            try:
                await self.assign_user_schedule(
                    db,
                    user.id,
                    room.id,
                    [int(validated["shift_number"])],
                    [int(validated["day_of_week"])],
                )
                created_count += 1
                results.append(
                    {
                        "row_number": index,
                        "success": True,
                        "message": "Schedule imported successfully",
                        "email": normalized_email,
                        "room_name": room.name,
                        "user_id": user.id,
                    }
                )
            except ValueError as exc:
                results.append(
                    {
                        "row_number": index,
                        "success": False,
                        "message": str(exc),
                        "email": normalized_email,
                        "room_name": room_name,
                        "user_id": user.id,
                    }
                )

        return {
            "created_count": created_count,
            "failed_count": len(results) - created_count,
            "results": results,
        }

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
