from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    building: Mapped[str] = mapped_column(String(10), nullable=False, default="A")
    location: Mapped[str] = mapped_column(String(100), nullable=True)
    auto_control_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
