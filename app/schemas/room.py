from pydantic import BaseModel
from pydantic import Field


class RoomResponse(BaseModel):
    id: int
    name: str
    building: str
    location: str | None = None
    auto_control_enabled: bool

    model_config = {"from_attributes": True}


class RoomAutomationModeUpdate(BaseModel):
    auto_control_enabled: bool


class RoomCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    building: str = Field(min_length=1, max_length=10)
    location: str | None = Field(default=None, max_length=100)
