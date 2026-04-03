from datetime import datetime as real_datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core import dependencies as deps


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
async def test_admin_has_full_access_without_schedule_check():
    db = AsyncMock()
    current_user = {"sub": "1", "role": "admin"}

    await deps.ensure_room_shift_access(db, current_user, room_id=1)

    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_user_blocked_outside_all_shifts(monkeypatch):
    db = AsyncMock()
    current_user = {"sub": "2", "role": "user"}
    monkeypatch.setattr(deps, "get_current_shift", lambda: None)

    with pytest.raises(HTTPException) as exc_info:
        await deps.ensure_room_shift_access(db, current_user, room_id=1)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Outside all allowed shifts"


@pytest.mark.asyncio
async def test_user_blocked_when_not_granted_for_current_day(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_ScalarResult(None))
    current_user = {"sub": "3", "role": "user"}

    class _FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 3, 17, 10, 0, 0)

    monkeypatch.setattr(deps, "datetime", _FixedDateTime)
    monkeypatch.setattr(deps, "get_current_shift", lambda: 2)

    with pytest.raises(HTTPException) as exc_info:
        await deps.ensure_room_shift_access(db, current_user, room_id=101)

    assert exc_info.value.status_code == 403
    assert "No schedule entry for room 101 in shift 2 on this day" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_user_allowed_when_granted_for_current_day(monkeypatch):
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_ScalarResult(99))
    current_user = {"sub": "4", "role": "user"}

    class _FixedDateTime:
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 3, 17, 10, 0, 0)

    monkeypatch.setattr(deps, "datetime", _FixedDateTime)
    monkeypatch.setattr(deps, "get_current_shift", lambda: 2)

    await deps.ensure_room_shift_access(db, current_user, room_id=202)


def test_get_current_shift_matches_schedule_boundaries():
    assert deps.get_current_shift(real_datetime(2026, 3, 17, 7, 0, 0)) == 1
    assert deps.get_current_shift(real_datetime(2026, 3, 17, 9, 35, 0)) == 2
    assert deps.get_current_shift(real_datetime(2026, 3, 17, 12, 0, 0)) is None
    assert deps.get_current_shift(real_datetime(2026, 3, 17, 19, 55, 0)) == 6
