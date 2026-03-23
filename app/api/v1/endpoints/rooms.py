from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session, require_admin
from app.schemas.room import RoomAutomationModeUpdate, RoomResponse
from app.services.room_service import room_service

router = APIRouter()


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(get_current_user),
):
    return await room_service.list_all(db)


@router.put("/{room_id}/automation-mode", response_model=RoomResponse)
async def update_room_automation_mode(
    room_id: int,
    payload: RoomAutomationModeUpdate,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await room_service.set_automation_mode(db, room_id, payload.auto_control_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
