from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.Exceptions.RequestError import ConflictError, ResourceNotFoundError
from app.db.models.solicitudes import Solicitudes
from app.repositories.pagination import Page
from app.schemas.enums import Priority, RequestType, State
from app.schemas.solicitudes import SolicitudCreate, SolicitudFilters
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


@pytest.mark.asyncio
async def test_list_solicitudes_delegates_filters_to_repository():
    filters = SolicitudFilters(
        state=State.RECEIVED,
        type=RequestType.PLATFORM_ACCESS,
        priority=Priority.HIGH,
        offset=10,
        limit=5,
    )
    expected_page = Page(
        items=[MagicMock(spec=Solicitudes)],
        total=16,
        offset=10,
        limit=5,
    )
    repository = MagicMock()
    repository.list = AsyncMock(return_value=expected_page)
    session = MagicMock()

    result = await SolicitudService(repository, session).list(filters)

    assert result is expected_page
    assert result.has_next is True
    repository.list.assert_awaited_once_with(filters)


@pytest.mark.asyncio
async def test_get_solicitud_by_id_returns_existing_record():
    solicitud_id = UUID("12345678-1234-5678-1234-567812345678")
    expected_solicitud = MagicMock(spec=Solicitudes)
    repository = MagicMock()
    repository.get_by_id = AsyncMock(return_value=expected_solicitud)
    session = MagicMock()

    result = await SolicitudService(repository, session).get_by_id(solicitud_id)

    assert result is expected_solicitud
    repository.get_by_id.assert_awaited_once_with(solicitud_id)


@pytest.mark.asyncio
async def test_get_solicitud_by_id_raises_404_when_record_does_not_exist():
    solicitud_id = UUID("00000000-0000-0000-0000-000000000000")
    repository = MagicMock()
    repository.get_by_id = AsyncMock(return_value=None)
    session = MagicMock()

    with pytest.raises(ResourceNotFoundError) as error:
        await SolicitudService(repository, session).get_by_id(solicitud_id)

    assert error.value.status_code == 404
    assert error.value.code == "resource_not_found"
    assert error.value.details == {"solicitud_id": str(solicitud_id)}
    repository.get_by_id.assert_awaited_once_with(solicitud_id)
