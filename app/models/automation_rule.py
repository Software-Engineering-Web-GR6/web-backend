from sqlalchemy import Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric: Mapped[str] = mapped_column(String(30), nullable=False)
    operator: Mapped[str] = mapped_column(String(5), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    alert_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    alert_message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
