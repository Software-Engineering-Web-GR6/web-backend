import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.session import Base
from app.core.dependencies import get_db_session

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    from app.models import room, device, sensor_reading, automation_rule, action_log, alert, user  # noqa
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    from main import app
    from app.db.seed import seed_data

    await seed_data(db_session)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_token(client):
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
