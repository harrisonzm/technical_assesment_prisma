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
async def test_get_solicitud_by_id_endpoint_returns_existing_record():
    solicitud = build_solicitud()
    session = MagicMock()
    session.get = AsyncMock(return_value=solicitud)

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/solicitudes/{SOLICITUD_ID}")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {
        "id": str(SOLICITUD_ID),
        "external_id": "EXT-001",
        "type": "Acceso a plataforma",
        "applicant": "Ada Lovelace",
        "email": "ada@example.com",
        "description": "Platform access request",
        "priority": "Alta",
        "state": "Recibida",
        "created_at": solicitud.created_at.isoformat().replace("+00:00", "Z"),
        "updated_at": solicitud.updated_at.isoformat().replace("+00:00", "Z"),
    }
    session.get.assert_awaited_once_with(Solicitudes, SOLICITUD_ID)


@pytest.mark.asyncio
async def test_get_solicitud_by_id_endpoint_returns_404_when_missing():
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/solicitudes/{MISSING_ID}")

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
    session.get.assert_awaited_once_with(Solicitudes, MISSING_ID)
