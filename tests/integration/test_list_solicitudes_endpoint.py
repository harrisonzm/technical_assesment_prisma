from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models.solicitudes import Solicitudes
from app.db.session import get_db_session
from app.main import create_app
from app.schemas.enums import Priority, RequestType, State


@pytest.mark.asyncio
async def test_list_solicitudes_endpoint_filters_and_paginates_results():
    timestamp = datetime.now(UTC)
    solicitud = Solicitudes(
        id=UUID("12345678-1234-5678-1234-567812345678"),
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

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [solicitud]
    session = MagicMock()
    session.scalar = AsyncMock(return_value=2)
    session.execute = AsyncMock(return_value=query_result)

    async def override_db_session():
        yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/solicitudes",
            params={
                "state": "Recibida",
                "type": "Acceso a plataforma",
                "priority": "Alta",
                "offset": 0,
                "limit": 1,
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {
        "items": [
            {
                "id": "12345678-1234-5678-1234-567812345678",
                "external_id": "EXT-001",
                "type": "Acceso a plataforma",
                "applicant": "Ada Lovelace",
                "email": "ada@example.com",
                "description": "Platform access request",
                "priority": "Alta",
                "state": "Recibida",
                "created_at": timestamp.isoformat().replace("+00:00", "Z"),
                "updated_at": timestamp.isoformat().replace("+00:00", "Z"),
            }
        ],
        "total": 2,
        "offset": 0,
        "limit": 1,
        "has_next": True,
    }

    page_statement = session.execute.await_args.args[0]
    statement_values = set(page_statement.compile().params.values())
    assert State.RECEIVED in statement_values
    assert RequestType.PLATFORM_ACCESS in statement_values
    assert Priority.HIGH in statement_values
    assert 0 in statement_values
    assert 1 in statement_values
