from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db_session
from app.main import create_app


VALID_PAYLOAD = {
    "external_id": "EXT-INVALID",
    "type": "Acceso a plataforma",
    "applicant": "Ada Lovelace",
    "email": "ada@example.com",
    "description": "Platform access request",
    "priority": "Alta",
}


@pytest.mark.asyncio
async def test_create_solicitud_endpoint_returns_created_resource():
    session = MagicMock()
    lookup_result = MagicMock()
    lookup_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=lookup_result)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def refresh(solicitud):
        timestamp = datetime.now(UTC)
        solicitud.id = UUID("12345678-1234-5678-1234-567812345678")
        solicitud.created_at = timestamp
        solicitud.updated_at = timestamp

    session.refresh = AsyncMock(side_effect=refresh)

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/solicitudes",
            json={
                "external_id": "EXT-001",
                "type": "Acceso a plataforma",
                "applicant": "Ada Lovelace",
                "email": "ada@example.com",
                "description": "Platform access request",
                "priority": "Alta",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.headers["x-request-id"]
    assert response.json() == {
        "id": "12345678-1234-5678-1234-567812345678",
        "external_id": "EXT-001",
        "type": "Acceso a plataforma",
        "applicant": "Ada Lovelace",
        "email": "ada@example.com",
        "description": "Platform access request",
        "priority": "Alta",
        "state": "Recibida",
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
    }
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_solicitud_endpoint_returns_409_for_duplicate_external_id():
    session = MagicMock()
    session.flush = AsyncMock(
        side_effect=IntegrityError(
            "INSERT INTO solicitudes",
            {"externalId": "EXT-DUPLICATE"},
            Exception("duplicate key"),
        )
    )
    session.rollback = AsyncMock()

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/solicitudes",
            json={
                "external_id": "EXT-DUPLICATE",
                "type": "Acceso a plataforma",
                "applicant": "Grace Hopper",
                "email": "grace@example.com",
                "description": "Duplicate request",
                "priority": "Media",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.headers["x-request-id"]
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "A solicitud with this external ID already exists",
            "details": {"external_id": "EXT-DUPLICATE"},
            "request_id": response.headers["x-request-id"],
        }
    }
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {**VALID_PAYLOAD, "email": "not-an-email"},
        {**VALID_PAYLOAD, "type": "Tipo inexistente"},
        {**VALID_PAYLOAD, "unexpected_field": "not allowed"},
        {
            key: value
            for key, value in VALID_PAYLOAD.items()
            if key != "description"
        },
    ],
    ids=[
        "invalid-email",
        "invalid-catalog-value",
        "unknown-field",
        "missing-required-field",
    ],
)
async def test_create_solicitud_endpoint_rejects_invalid_payload(
    invalid_payload: dict[str, str],
):
    session = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/solicitudes",
            json=invalid_payload,
        )

    app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.headers["x-request-id"]
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "Request validation failed"
    assert response.json()["error"]["details"]["errors"]
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
