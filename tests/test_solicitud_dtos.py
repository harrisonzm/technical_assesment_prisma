from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.enums import Priority, RequestType, State
from app.schemas.solicitudes import SolicitudCreate, SolicitudFilters, SolicitudUpdate


def test_create_solicitud_defaults_to_received():
    data = SolicitudCreate(
        external_id="EXT-001",
        type=RequestType.TECHNICAL_SUPPORT,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Cannot access the platform",
        priority=Priority.HIGH,
    )

    assert data.state is State.RECEIVED


def test_create_solicitud_rejects_invalid_email():
    with pytest.raises(ValidationError):
        SolicitudCreate(
            external_id="EXT-001",
            type=RequestType.ACADEMIC,
            applicant="Ada Lovelace",
            email="not-an-email",
            description="Question",
            priority=Priority.LOW,
        )


def test_update_only_exports_fields_that_were_provided():
    data = SolicitudUpdate(state=State.COMPLETED)

    assert data.model_dump(exclude_unset=True) == {"state": State.COMPLETED}


def test_filters_limit_is_bounded():
    with pytest.raises(ValidationError):
        SolicitudFilters(limit=101)


def test_filters_accept_every_model_column_except_id():
    timestamp = datetime.now(UTC)
    filters = SolicitudFilters(
        external_id="EXT-001",
        type=RequestType.ADMINISTRATIVE,
        applicant="Ada Lovelace",
        email="ada@example.com",
        description="Administrative request",
        priority=Priority.MEDIUM,
        state=State.IN_PROGRESS,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert set(filters.model_fields_set) == {
        "external_id",
        "type",
        "applicant",
        "email",
        "description",
        "priority",
        "state",
        "created_at",
        "updated_at",
    }
    assert "id" not in SolicitudFilters.model_fields
