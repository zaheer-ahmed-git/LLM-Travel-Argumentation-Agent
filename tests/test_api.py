"""API tests using in-memory SQLite."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from workflow_automation.api.deps import get_db
from workflow_automation.api.main import create_app
from workflow_automation.models.orm import Base


@pytest_asyncio.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app = create_app()

    async def override_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["agents_ready"] is True


@pytest.mark.asyncio
async def test_roles_endpoint(client):
    response = await client.get("/agents/roles")
    assert response.status_code == 200
    roles = {item["role"] for item in response.json()}
    assert "planner" in roles
    assert "reviewer" in roles


@pytest.mark.asyncio
async def test_workflow_run_offline(client):
    create = await client.post(
        "/workflows",
        json={
            "name": "Vendor review",
            "goal": "Research vendor options and write a recommendation report",
            "description": "Portfolio demo workflow",
        },
    )
    assert create.status_code == 200
    workflow_id = create.json()["id"]

    run = await client.post(f"/workflows/{workflow_id}/run", json={})
    assert run.status_code == 200
    body = run.json()
    assert body["workflow_id"] == workflow_id
    assert body["messages_exchanged"] >= 3
    assert body["assigned_roles"]
    assert 0 < body["compression_ratio"] <= 1.0
    assert body["result_summary"]

    messages = await client.get(f"/workflows/{workflow_id}/messages")
    assert messages.status_code == 200
    assert len(messages.json()) >= 3

    memory = await client.post(
        "/memory/query",
        json={"key": "summary", "limit": 3},
    )
    assert memory.status_code == 200
    assert memory.json()["retrieval_ms"] >= 0
