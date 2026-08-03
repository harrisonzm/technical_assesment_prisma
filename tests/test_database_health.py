from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import create_app


@pytest.mark.asyncio
async def test_health_returns_ok_without_accessing_database():
    app = create_app()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_database_readiness_returns_ready_when_database_responds():
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {"status": "ready"}
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_readiness_returns_structured_503():
    session = MagicMock()
    session.execute = AsyncMock(side_effect=ConnectionError("database is down"))

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health/ready")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "Database is unavailable",
            "details": None,
            "request_id": response.headers["x-request-id"],
        }
    }
