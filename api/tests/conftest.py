import asyncio
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.core.security import hash_password

TEST_DB_URL = "postgresql+asyncpg://agentic:agentic_secret@localhost:5432/agentic_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db: AsyncSession):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def tenant(db: AsyncSession) -> Tenant:
    t = Tenant(name="Test Corp", slug="test-corp")
    db.add(t)
    await db.flush()
    return t


@pytest.fixture
async def user(db: AsyncSession, tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email="testuser@example.com",
        full_name="Test User",
        hashed_password=hash_password("password123"),
    )
    db.add(u)
    await db.flush()
    return u


@pytest.fixture
async def auth_headers(client, user: User) -> dict:
    resp = await client.post("/api/v1/auth/login", json={
        "email": "testuser@example.com",
        "password": "password123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
