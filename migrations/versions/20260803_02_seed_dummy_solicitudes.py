"""Seed solicitudes with deterministic dummy data.

Revision ID: 20260803_02
Revises: 20260803_01
Create Date: 2026-08-03
"""
from datetime import datetime, timedelta, timezone
from typing import Sequence
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260803_02"
down_revision: str | None = "20260803_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


request_type = postgresql.ENUM(
    "Acceso a plataforma",
    "Soporte técnico",
    "Académica",
    "Administrativa",
    name="request_type",
    create_type=False,
)
request_priority = postgresql.ENUM(
    "Baja",
    "Media",
    "Alta",
    name="request_priority",
    create_type=False,
)
request_state = postgresql.ENUM(
    "Recibida",
    "En proceso",
    "Completada",
    "Rechazada",
    name="requestState",
    create_type=False,
)

solicitudes = sa.table(
    "solicitudes",
    sa.column("id", sa.Uuid()),
    sa.column("externalId", sa.String(length=100)),
    sa.column("type", request_type),
    sa.column("applicant", sa.String(length=40)),
    sa.column("email", sa.String(length=254)),
    sa.column("description", sa.String(length=1000)),
    sa.column("priority", request_priority),
    sa.column("state", request_state),
    sa.column("createdAt", sa.DateTime(timezone=True)),
    sa.column("updatedAt", sa.DateTime(timezone=True)),
)

REQUEST_TYPES = (
    "Acceso a plataforma",
    "Soporte técnico",
    "Académica",
    "Administrativa",
)
PRIORITIES = ("Baja", "Media", "Alta")
STATES = ("Recibida", "En proceso", "Completada", "Rechazada")
DESCRIPTIONS = (
    "Solicitud de acceso para un nuevo usuario institucional.",
    "Incidente técnico reportado durante el uso de la plataforma.",
    "Consulta relacionada con procesos académicos.",
    "Solicitud de actualización de información administrativa.",
    "Requerimiento general para validar el flujo institucional.",
)


def _dummy_rows() -> list[dict[str, object]]:
    reference_time = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)

    return [
        {
            "id": uuid5(NAMESPACE_URL, f"solicitud-dummy-{number}"),
            "externalId": f"DUMMY-{number:03d}",
            "type": REQUEST_TYPES[(number - 1) % len(REQUEST_TYPES)],
            "applicant": f"Solicitante Demo {number}",
            "email": f"solicitante.demo.{number}@example.com",
            "description": DESCRIPTIONS[(number - 1) % len(DESCRIPTIONS)],
            "priority": PRIORITIES[(number - 1) % len(PRIORITIES)],
            "state": STATES[(number - 1) % len(STATES)],
            "createdAt": reference_time - timedelta(hours=number),
            "updatedAt": reference_time - timedelta(minutes=number),
        }
        for number in range(1, 31)
    ]


def upgrade() -> None:
    op.bulk_insert(solicitudes, _dummy_rows())


def downgrade() -> None:
    op.execute(
        solicitudes.delete().where(solicitudes.c.externalId.like("DUMMY-%"))
    )
