"""Create solicitudes table and catalog enum types.

Revision ID: 20260803_01
Revises:
Create Date: 2026-08-03
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260803_01"
down_revision: str | None = None
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


def upgrade() -> None:
    bind = op.get_bind()
    request_type.create(bind, checkfirst=True)
    request_priority.create(bind, checkfirst=True)
    request_state.create(bind, checkfirst=True)

    op.create_table(
        "solicitudes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("externalId", sa.String(length=100), nullable=False),
        sa.Column("type", request_type, nullable=False),
        sa.Column("applicant", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("priority", request_priority, nullable=False),
        sa.Column("state", request_state, nullable=False),
        sa.Column(
            "createdAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updatedAt",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_solicitudes_email"),
    )
    op.create_index("ix_solicitudes_createdAt", "solicitudes", ["createdAt"])
    op.create_index(
        "ix_solicitudes_externalId",
        "solicitudes",
        ["externalId"],
        unique=True,
    )
    op.create_index("ix_solicitudes_priority", "solicitudes", ["priority"])
    op.create_index("ix_solicitudes_state", "solicitudes", ["state"])
    op.create_index("ix_solicitudes_type", "solicitudes", ["type"])


def downgrade() -> None:
    op.drop_index("ix_solicitudes_type", table_name="solicitudes")
    op.drop_index("ix_solicitudes_state", table_name="solicitudes")
    op.drop_index("ix_solicitudes_priority", table_name="solicitudes")
    op.drop_index("ix_solicitudes_externalId", table_name="solicitudes")
    op.drop_index("ix_solicitudes_createdAt", table_name="solicitudes")
    op.drop_table("solicitudes")

    bind = op.get_bind()
    request_state.drop(bind, checkfirst=True)
    request_priority.drop(bind, checkfirst=True)
    request_type.drop(bind, checkfirst=True)
