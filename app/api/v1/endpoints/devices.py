from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db_session, require_device_access, require_room_access
from app.schemas.device import DeviceResponse, DeviceControlRequest, DeviceTemperatureUpdateRequest
from app.services.device_service import device_service

router = APIRouter()


@router.get("/{room_id}", response_model=list[DeviceResponse])
async def get_devices(
    room_id: int,
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_room_access),
):
    return await device_service.get_by_room(db, room_id)


@router.post("/{device_id}/control", response_model=DeviceResponse)
async def control_device(
    device_id: int,
    payload: DeviceControlRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_device_access),
):
    try:
        return await device_service.control(
            db,
            device_id=device_id,
            action=payload.action,
            source=current_user.get("role", "MANUAL").upper(),
            description=f"Manual override by {current_user.get('email')}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{device_id}/temperature", response_model=DeviceResponse)
async def update_device_temperature(
    device_id: int,
    payload: DeviceTemperatureUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(require_device_access),
):
    try:
        return await device_service.update_temperature(
            db,
            device_id=device_id,
            target_temp=payload.target_temp,
            source=current_user.get("role", "MANUAL").upper(),
            description=f"Manual override by {current_user.get('email')}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
