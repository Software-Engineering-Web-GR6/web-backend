from datetime import datetime
from pydantic import BaseModel


class SensorReadingCreate(BaseModel):
    room_id: int
    temperature: float | None = None
    humidity: float | None = None
    co2: float | None = None
    motion_detected: bool | None = None
    recorded_at: datetime | None = None


class SensorReadingResponse(BaseModel):
    id: int
    room_id: int
    temperature: float | None = None
    humidity: float | None = None
    co2: float | None = None
    motion_detected: bool | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}
