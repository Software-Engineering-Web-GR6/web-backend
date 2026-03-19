from datetime import datetime
from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    room_id: int
    level: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}
