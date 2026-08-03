from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.solicitudes import Solicitudes
from app.db.session import get_db_session
from app.main import create_app
from app.schemas.enums import Priority, RequestType, State


SOLICITUD_ID = UUID("12345678-1234-5678-1234-567812345678")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000000")


def build_solicitud() -> Solicitudes:
    timestamp = datetime.now(UTC)
    return Solicitudes(
        id=SOLICITUD_ID,
        external_id="EXT-001",
        type=RequestType.PLATFORM_ACCESS,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Platform access request",
        priority=Priority.HIGH,
        state=State.RECEIVED,
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_update_solicitud_state_endpoint_returns_updated_record():
    solicitud = build_solicitud()
    session = MagicMock()
    session.get = AsyncMock(return_value=solicitud)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/api/v1/solicitudes/{SOLICITUD_ID}/estado",
            json={"state": "En proceso"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json()["id"] == str(SOLICITUD_ID)
    assert response.json()["state"] == "En proceso"
    session.get.assert_awaited_once_with(Solicitudes, SOLICITUD_ID)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(solicitud)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_solicitud_state_endpoint_returns_404_when_missing():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.commit = AsyncMock()

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/api/v1/solicitudes/{MISSING_ID}/estado",
            json={"state": "Rechazada"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": {
            "code": "resource_not_found",
            "message": "Solicitud was not found",
            "details": {"solicitud_id": str(MISSING_ID)},
            "request_id": response.headers["x-request-id"],
        }
    }
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_solicitud_state_endpoint_rejects_invalid_state():
    session = MagicMock()
    session.get = AsyncMock()

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/api/v1/solicitudes/{SOLICITUD_ID}/estado",
            json={"state": "Estado inexistente"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    assert response.json()["error"]["code"] == "validation_error"
    session.get.assert_not_awaited()
