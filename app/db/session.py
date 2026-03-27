from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from app.models import room, device, sensor_reading, automation_rule, action_log, alert, user, user_room_shift_access  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        room_columns = await conn.execute(text("PRAGMA table_info(rooms)"))
        room_column_names = {row[1] for row in room_columns.fetchall()}
        device_columns = await conn.execute(text("PRAGMA table_info(devices)"))
        device_column_names = {row[1] for row in device_columns.fetchall()}
        if "building" not in room_column_names:
            await conn.execute(text("ALTER TABLE rooms ADD COLUMN building VARCHAR(10) DEFAULT 'A' NOT NULL"))
        if "auto_control_enabled" not in room_column_names:
            await conn.execute(text("ALTER TABLE rooms ADD COLUMN auto_control_enabled BOOLEAN DEFAULT 1 NOT NULL"))
        if "target_temp" not in device_column_names:
            await conn.execute(text("ALTER TABLE devices ADD COLUMN target_temp INTEGER DEFAULT 24 NOT NULL"))
