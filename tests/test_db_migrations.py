from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import session as session_module
from app.db.seed import seed_data


@pytest.mark.asyncio
async def test_bootstrap_database_migrates_legacy_users_table_without_data_loss(monkeypatch):
    # Keep one SQLite-focused test so the compatibility path for old local DB files
    # does not regress while PostgreSQL remains the primary database backend.
    temp_dir = Path("tests") / ".tmp_migrations" / uuid4().hex
    temp_dir.mkdir(parents=True, exist_ok=True)
    database_path = temp_dir / "legacy.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"

    legacy_engine = create_async_engine(database_url, echo=False)
    async with legacy_engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20)
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, role)
                VALUES (99, 'legacy.user@example.com', 'hash', 'user')
                """
            )
        )
    await legacy_engine.dispose()

    original_database_url = session_module.settings.DATABASE_URL
    original_engine = session_module.engine
    original_session_local = session_module.AsyncSessionLocal
    monkeypatch.setattr(session_module.settings, "DATABASE_URL", database_url)

    test_engine = create_async_engine(database_url, echo=False)
    test_session_local = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(session_module, "engine", test_engine)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", test_session_local)

    try:
        await session_module.bootstrap_database(seed_data)
    finally:
        await test_engine.dispose()
        session_module.engine = original_engine
        session_module.AsyncSessionLocal = original_session_local
        monkeypatch.setattr(session_module.settings, "DATABASE_URL", original_database_url)

    backups = list(temp_dir.glob("legacy.incompatible.*.db"))
    assert backups == []

    with sqlite3.connect(database_path) as conn:
        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        assert "full_name" in user_columns
        assert "created_at" in user_columns

        users = conn.execute(
            "SELECT id, email, full_name FROM users WHERE email = 'legacy.user@example.com'"
        ).fetchone()
        assert users == (99, "legacy.user@example.com", "legacy.user@example.com")

        room_columns = {row[1] for row in conn.execute("PRAGMA table_info(rooms)").fetchall()}
        device_columns = {row[1] for row in conn.execute("PRAGMA table_info(devices)").fetchall()}
        assert "building" in room_columns
        assert "auto_control_enabled" in room_columns
        assert "target_temp" in device_columns
