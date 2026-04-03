from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_accessible_room_ids,
    get_current_user,
    get_db_session,
    require_admin,
)
from app.schemas.room import RoomAutomationModeUpdate, RoomCreateRequest, RoomResponse
from app.services.room_service import room_service

router = APIRouter()


@router.get("", response_model=list[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") == "admin":
        return await room_service.list_all(db)

    room_ids = await get_accessible_room_ids(db, current_user)
    return await room_service.list_by_ids(db, room_ids)


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    payload: RoomCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_admin),
):
    try:
        return await room_service.create_room(
            db,
            name=payload.name,
            building=payload.building,
            location=payload.location,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
