from datetime import datetime, time

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.device import Device
from app.models.user_room_shift_access import UserRoomShiftAccess
from app.db.session import get_db
from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SHIFT_WINDOWS: dict[int, tuple[time, time]] = {
    1: (time(7, 0), time(9, 35)),
    2: (time(9, 35), time(12, 0)),
    3: (time(13, 0), time(15, 35)),
    4: (time(15, 35), time(18, 0)),
    5: (time(18, 15), time(19, 50)),
    6: (time(19, 55), time(21, 30)),
}


async def get_db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user


def get_current_shift(now: datetime | None = None) -> int | None:
    now_time = (now or datetime.now()).time()
    for shift_number, (start, end) in SHIFT_WINDOWS.items():
        if start <= now_time < end:
            return shift_number
    return None


async def ensure_room_shift_access(db: AsyncSession, current_user: dict, room_id: int) -> None:
    if current_user.get("role") == "admin":
        return

    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    current_shift = get_current_shift()
    if current_shift is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Outside all allowed shifts",
        )

    current_day = datetime.now().weekday()

    permission_result = await db.execute(
        select(UserRoomShiftAccess.id).where(
            UserRoomShiftAccess.user_id == user_id,
            UserRoomShiftAccess.room_id == room_id,
            UserRoomShiftAccess.shift_number == current_shift,
            UserRoomShiftAccess.day_of_week == current_day,
        )
    )
    permission = permission_result.scalar_one_or_none()
    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No schedule entry for room {room_id} in shift {current_shift} on this day",
        )


async def get_accessible_room_ids(db: AsyncSession, current_user: dict) -> list[int]:
    if current_user.get("role") == "admin":
        result = await db.execute(select(UserRoomShiftAccess.room_id).distinct())
        return list(result.scalars().all())

    user_id_raw = current_user.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    current_shift = get_current_shift()
    if current_shift is None:
        return []

    current_day = datetime.now().weekday()
    result = await db.execute(
        select(UserRoomShiftAccess.room_id)
        .where(
            UserRoomShiftAccess.user_id == user_id,
            UserRoomShiftAccess.shift_number == current_shift,
            UserRoomShiftAccess.day_of_week == current_day,
        )
        .distinct()
    )
    return list(result.scalars().all())


async def require_room_access(
    room_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    await ensure_room_shift_access(db, current_user, room_id)
    return current_user


async def require_device_access(
    device_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    await ensure_room_shift_access(db, current_user, device.room_id)
    return current_user


async def require_alert_access(
    alert_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    await ensure_room_shift_access(db, current_user, alert.room_id)
    return current_user
