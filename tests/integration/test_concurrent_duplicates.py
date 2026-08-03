import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url

from app.core.config.config import get_settings
from app.db.models.solicitudes import Solicitudes
from app.db.session import engine
from app.main import create_app


@pytest.mark.asyncio
async def test_concurrent_posts_with_same_external_id_persist_only_one_record():
    if make_url(get_settings().database_url).get_backend_name() != "postgresql":
        pytest.skip("PostgreSQL is required for the concurrency integration test")

    marker = uuid4().hex
    external_id = f"CONCURRENT-{marker}"

    async with engine.begin() as connection:
        await connection.execute(
            delete(Solicitudes).where(Solicitudes.external_id == external_id)
        )

    app = create_app()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            payload = {
                "external_id": external_id,
                "type": "Acceso a plataforma",
                "applicant": "Concurrent User",
                "description": "Concurrent duplicate request",
                "priority": "Alta",
            }

            first_request, second_request = await asyncio.gather(
                client.post(
                    "/api/v1/solicitudes",
                    json={**payload, "email": f"first.{marker}@example.com"},
                ),
                client.post(
                    "/api/v1/solicitudes",
                    json={**payload, "email": f"second.{marker}@example.com"},
                ),
            )

        responses = [first_request, second_request]
        assert sorted(response.status_code for response in responses) == [201, 409]

        created_response = next(
            response for response in responses if response.status_code == 201
        )
        conflict_response = next(
            response for response in responses if response.status_code == 409
        )
        assert created_response.json()["external_id"] == external_id
        assert conflict_response.json()["error"]["code"] == "conflict"
        assert conflict_response.json()["error"]["details"] == {
            "external_id": external_id
        }

        async with engine.connect() as connection:
            persisted_count = await connection.scalar(
                select(func.count())
                .select_from(Solicitudes)
                .where(Solicitudes.external_id == external_id)
            )
        assert persisted_count == 1
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(Solicitudes).where(Solicitudes.external_id == external_id)
            )
