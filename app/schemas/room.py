from pydantic import BaseModel


class RoomResponse(BaseModel):
    id: int
    name: str
    building: str
    location: str | None = None
    auto_control_enabled: bool

    model_config = {"from_attributes": True}


class RoomAutomationModeUpdate(BaseModel):
    auto_control_enabled: bool
