from collections.abc import Awaitable, Callable
import logging
from typing import cast

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = None
AsyncSessionLocal = None


def _build_engine_and_sessionmaker() -> tuple:
    db_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return db_engine, session_factory


def ensure_engine_initialized():
    global engine, AsyncSessionLocal
    if engine is None or AsyncSessionLocal is None:
        engine, AsyncSessionLocal = _build_engine_and_sessionmaker()
    return engine, AsyncSessionLocal


async def get_db():
    _, session_factory = ensure_engine_initialized()
    async with cast(async_sessionmaker[AsyncSession], session_factory)() as session:
        yield session


async def _column_names(conn, table_name: str) -> set[str]:
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    return {row[1] for row in result.fetchall()}


async def _add_column_if_missing(conn, table_name: str, column_name: str, ddl: str) -> bool:
    existing_columns = await _column_names(conn, table_name)
    if column_name in existing_columns:
        return False
    await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
    return True


async def _migrate_legacy_schema(conn) -> None:
    if await _add_column_if_missing(
        conn,
        "rooms",
        "building",
        "building VARCHAR(10) DEFAULT 'A' NOT NULL",
    ):
        logger.info("Added missing column rooms.building")

    if await _add_column_if_missing(
        conn,
        "rooms",
        "auto_control_enabled",
        "auto_control_enabled BOOLEAN DEFAULT 1 NOT NULL",
    ):
        logger.info("Added missing column rooms.auto_control_enabled")

    if await _add_column_if_missing(
        conn,
        "devices",
        "target_temp",
        "target_temp INTEGER DEFAULT 24 NOT NULL",
    ):
        logger.info("Added missing column devices.target_temp")

    if await _add_column_if_missing(
        conn,
        "users",
        "full_name",
        "full_name VARCHAR(100) DEFAULT 'Unknown User' NOT NULL",
    ):
        logger.info("Added missing column users.full_name")
        await conn.execute(
            text(
                """
                UPDATE users
                SET full_name = COALESCE(NULLIF(email, ''), 'Unknown User')
                WHERE full_name IS NULL OR full_name = '' OR full_name = 'Unknown User'
                """
            )
        )

    if await _add_column_if_missing(
        conn,
        "users",
        "created_at",
        "created_at DATETIME",
    ):
        logger.info("Added missing column users.created_at")
        await conn.execute(
            text(
                """
                UPDATE users
                SET created_at = CURRENT_TIMESTAMP
                WHERE created_at IS NULL
                """
            )
        )


async def _migrate_legacy_schema_if_needed(conn) -> None:
    if conn.dialect.name != "sqlite":
        return
    await _migrate_legacy_schema(conn)


async def init_db():
    from app.models import room, device, sensor_reading, automation_rule, action_log, alert, user, user_room_shift_access, password_reset_code  # noqa
    db_engine, _ = ensure_engine_initialized()
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_legacy_schema_if_needed(conn)


async def bootstrap_database(seed_callback: Callable[[AsyncSession], Awaitable[None]]) -> None:
    try:
        logger.info("Initializing database schema")
        await init_db()
        logger.info("Database schema ready; starting seed phase")
        _, session_factory = ensure_engine_initialized()
        async with cast(async_sessionmaker[AsyncSession], session_factory)() as session:
            await seed_callback(session)
        logger.info("Database seed completed")
    except (OperationalError, ProgrammingError) as exc:
        logger.exception("Database bootstrap failed with a schema or query error")
        raise RuntimeError(
            "Database schema is incompatible and could not be initialized automatically. "
            "Review the active database and add an explicit migration for the missing fields."
        ) from exc
