from datetime import UTC, datetime
from uuid import UUID

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


def test_create_solicitud_rejects_unknown_fields():
    with pytest.raises(ValidationError) as error:
        SolicitudCreate(
            external_id="EXT-001",
            type=RequestType.ACADEMIC,
            applicant="Ada Lovelace",
            email="ada@example.com",
            description="Question",
            priority=Priority.LOW,
            unexpected_field="not allowed",
        )

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_update_only_exports_fields_that_were_provided():
    data = SolicitudUpdate(state=State.COMPLETED)

    assert data.model_dump(exclude_unset=True) == {"state": State.COMPLETED}


def test_filters_limit_is_bounded():
    with pytest.raises(ValidationError):
        SolicitudFilters(limit=101)


def test_filters_accept_every_model_column():
    timestamp = datetime.now(UTC)
    solicitud_id = UUID("12345678-1234-5678-1234-567812345678")
    filters = SolicitudFilters(
        id=solicitud_id,
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
        "id",
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
    assert filters.id == solicitud_id
