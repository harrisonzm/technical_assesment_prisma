from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models.solicitudes import Solicitudes
from app.repositories.solicitudes import SolicitudRepository
from app.schemas.enums import Priority, RequestType, State
from app.schemas.solicitudes import SolicitudCreate, SolicitudFilters, SolicitudUpdate


@pytest.mark.asyncio
async def test_create_flushes_and_refreshes_solicitud():
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repository = SolicitudRepository(session)
    data = SolicitudCreate(
        external_id="EXT-001",
        type=RequestType.PLATFORM_ACCESS,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Access request",
        priority=Priority.MEDIUM,
    )

    solicitud = await repository.create(data)

    assert isinstance(solicitud, Solicitudes)
    assert solicitud.state is State.RECEIVED
    session.add.assert_called_once_with(solicitud)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(solicitud)


@pytest.mark.asyncio
async def test_get_by_id_uses_session_identity_lookup():
    solicitud_id = uuid4()
    expected = MagicMock(spec=Solicitudes)
    session = MagicMock()
    session.get = AsyncMock(return_value=expected)

    result = await SolicitudRepository(session).get_by_id(solicitud_id)

    assert result is expected
    session.get.assert_awaited_once_with(Solicitudes, solicitud_id)


@pytest.mark.asyncio
async def test_update_only_changes_provided_fields():
    solicitud = Solicitudes(
        external_id="EXT-001",
        type=RequestType.ACADEMIC,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Question",
        priority=Priority.LOW,
        state=State.RECEIVED,
    )
    session = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    result = await SolicitudRepository(session).update(
        solicitud,
        SolicitudUpdate(priority=Priority.HIGH),
    )

    assert result.priority is Priority.HIGH
    assert result.state is State.RECEIVED
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(solicitud)


@pytest.mark.asyncio
async def test_list_returns_page_with_total_and_has_next():
    items = [MagicMock(spec=Solicitudes), MagicMock(spec=Solicitudes)]
    scalar_result = MagicMock()
    scalar_result.scalars.return_value.all.return_value = items
    session = MagicMock()
    session.scalar = AsyncMock(return_value=3)
    session.execute = AsyncMock(return_value=scalar_result)

    page = await SolicitudRepository(session).list(
        SolicitudFilters(offset=0, limit=2)
    )

    assert page.items == items
    assert page.total == 3
    assert page.offset == 0
    assert page.limit == 2
    assert page.has_next is True
    session.scalar.assert_awaited_once()
    session.execute.assert_awaited_once()
