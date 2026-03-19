from pydantic import BaseModel


class RuleCreate(BaseModel):
    room_id: int
    name: str
    metric: str
    operator: str
    threshold_value: float
    target_device_id: int | None = None
    action: str
    alert_level: str = "MEDIUM"
    alert_message: str
    is_active: bool = True


class RuleUpdate(BaseModel):
    name: str | None = None
    metric: str | None = None
    operator: str | None = None
    threshold_value: float | None = None
    target_device_id: int | None = None
    action: str | None = None
    alert_level: str | None = None
    alert_message: str | None = None
    is_active: bool | None = None


class RuleResponse(BaseModel):
    id: int
    room_id: int
    name: str
    metric: str
    operator: str
    threshold_value: float
    target_device_id: int | None = None
    action: str
    alert_level: str
    alert_message: str
    is_active: bool

    model_config = {"from_attributes": True}
