"""Remove the unique constraint from solicitudes email.

Revision ID: 20260803_03
Revises: 20260803_02
Create Date: 2026-08-03
"""
from typing import Sequence

from alembic import op


revision: str = "20260803_03"
down_revision: str | None = "20260803_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_solicitudes_email",
        "solicitudes",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_solicitudes_email",
        "solicitudes",
        ["email"],
    )
