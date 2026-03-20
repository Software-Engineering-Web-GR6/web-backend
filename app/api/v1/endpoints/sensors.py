from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db_session, get_current_user, require_room_access, ensure_room_shift_access
from app.schemas.sensor import SensorReadingCreate, SensorReadingResponse
from app.services.sensor_service import sensor_service

router = APIRouter()


@router.post("/ingest")
async def ingest_sensor_data(
    payload: SensorReadingCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
):
    try:
        await ensure_room_shift_access(db, current_user, payload.room_id)
        reading, executed = await sensor_service.ingest(db, payload)
        return {"reading": SensorReadingResponse.model_validate(reading), "executed_rules": executed}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{room_id}/latest", response_model=SensorReadingResponse)
async def get_latest(room_id: int, db: AsyncSession = Depends(get_db_session), _: dict = Depends(require_room_access)):
    reading = await sensor_service.get_latest(db, room_id)
    if not reading:
        raise HTTPException(status_code=404, detail="No sensor data found")
    return reading


@router.get("/{room_id}/history", response_model=list[SensorReadingResponse])
async def get_history(
    room_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: dict = Depends(require_room_access),
):
    return await sensor_service.get_history(db, room_id, limit)
