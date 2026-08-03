from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.Exceptions.RequestError import ConflictError
from app.db.models.solicitudes import Solicitudes
from app.schemas.enums import Priority, RequestType
from app.schemas.solicitudes import SolicitudCreate
from app.services.solicitudes import SolicitudService


def build_create_dto() -> SolicitudCreate:
    return SolicitudCreate(
        external_id="EXT-001",
        type=RequestType.PLATFORM_ACCESS,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Platform access request",
        priority=Priority.HIGH,
    )


@pytest.mark.asyncio
async def test_create_solicitud_commits_new_record():
    data = build_create_dto()
    solicitud = MagicMock(spec=Solicitudes)
    repository = MagicMock()
    repository.create = AsyncMock(return_value=solicitud)
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    result = await SolicitudService(repository, session).create(data)

    assert result is solicitud
    repository.create.assert_awaited_once_with(data)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_solicitud_rolls_back_concurrent_duplicate():
    data = build_create_dto()
    repository = MagicMock()
    repository.create = AsyncMock(
        side_effect=IntegrityError(
            "INSERT INTO solicitudes ...",
            {"external_id": data.external_id},
            Exception("unique constraint violation"),
        )
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    with pytest.raises(ConflictError) as error:
        await SolicitudService(repository, session).create(data)

    assert error.value.status_code == 409
    assert error.value.details == {"external_id": "EXT-001"}
    repository.create.assert_awaited_once_with(data)
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
