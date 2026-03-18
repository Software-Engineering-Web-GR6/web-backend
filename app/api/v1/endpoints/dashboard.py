from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db_session, get_current_user
from app.services.sensor_service import sensor_service
from app.schemas.sensor import SensorReadingResponse
from app.schemas.device import DeviceResponse
from app.schemas.alert import AlertResponse

router = APIRouter()


@router.get("/{room_id}")
async def get_dashboard(room_id: int, db: AsyncSession = Depends(get_db_session), _: dict = Depends(get_current_user)):
    data = await sensor_service.get_dashboard(db, room_id)
    return {
        "room_id": data["room_id"],
        "latest": SensorReadingResponse.model_validate(data["latest"]) if data["latest"] else None,
        "history": [SensorReadingResponse.model_validate(i) for i in data["history"]],
        "averages": data["averages"],
        "devices": [DeviceResponse.model_validate(i) for i in data["devices"]],
        "unresolved_alerts": [AlertResponse.model_validate(i) for i in data["unresolved_alerts"]],
    }
