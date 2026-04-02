from datetime import datetime
from pydantic import BaseModel


class DeviceResponse(BaseModel):
    id: int
    room_id: int
    name: str
    device_type: str
    state: str
    target_temp: int
    is_online: bool
    last_updated: datetime

    model_config = {"from_attributes": True}


class DeviceControlRequest(BaseModel):
    action: str


class DeviceTemperatureUpdateRequest(BaseModel):
    target_temp: int
