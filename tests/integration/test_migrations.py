from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import MetaData, Table, create_engine, delete, insert, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.core.config.config import get_settings


def test_migrations_create_schema_and_seed_dummy_data(monkeypatch):
    """Run the full Alembic lifecycle against an isolated PostgreSQL database."""
    original_url = make_url(get_settings().database_url)
    if original_url.get_backend_name() != "postgresql":
        pytest.skip("PostgreSQL is required for the migration integration test")

    database_name = f"migration_test_{uuid4().hex}"
    admin_engine = create_engine(
        original_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True,
    )

    try:
        try:
            with admin_engine.connect() as connection:
                connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        except OperationalError as exc:
            pytest.skip(f"PostgreSQL is unavailable: {exc}")

        migration_url = original_url.set(database=database_name)
        monkeypatch.setenv(
            "DATABASE_URL",
            migration_url.render_as_string(hide_password=False),
        )
        get_settings.cache_clear()

        alembic_config = Config("alembic.ini")
        command.upgrade(alembic_config, "head")

        migration_engine = create_engine(migration_url)
        try:
            with migration_engine.connect() as connection:
                inspector = inspect(connection)
                assert inspector.has_table("solicitudes")
                assert all(
                    "email" not in constraint["column_names"]
                    for constraint in inspector.get_unique_constraints("solicitudes")
                )
                assert connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM solicitudes "
                        "WHERE applicant LIKE 'Solicitante Demo %'"
                    )
                ) == 30
                assert connection.scalar(
                    text("SELECT version_num FROM alembic_version")
                ) == "20260803_03"

                solicitudes = Table(
                    "solicitudes",
                    MetaData(),
                    autoload_with=connection,
                )
                shared_email = "shared.migration@example.com"
                connection.execute(
                    insert(solicitudes),
                    [
                        {
                            "id": uuid4(),
                            "externalId": "MIGRATION-EMAIL-001",
                            "type": "Acceso a plataforma",
                            "applicant": "Migration User One",
                            "email": shared_email,
                            "description": "First request with shared email",
                            "priority": "Baja",
                            "state": "Recibida",
                        },
                        {
                            "id": uuid4(),
                            "externalId": "MIGRATION-EMAIL-002",
                            "type": "Soporte técnico",
                            "applicant": "Migration User Two",
                            "email": shared_email,
                            "description": "Second request with shared email",
                            "priority": "Media",
                            "state": "En proceso",
                        },
                    ],
                )
                connection.commit()

                assert connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM solicitudes "
                        "WHERE email = :email"
                    ),
                    {"email": shared_email},
                ) == 2

                connection.execute(
                    delete(solicitudes).where(
                        solicitudes.c.externalId.like("MIGRATION-EMAIL-%")
                    )
                )
                connection.commit()
        finally:
            migration_engine.dispose()

        command.downgrade(alembic_config, "base")

        downgraded_engine = create_engine(migration_url)
        try:
            with downgraded_engine.connect() as connection:
                assert not inspect(connection).has_table("solicitudes")
        finally:
            downgraded_engine.dispose()
    finally:
        get_settings.cache_clear()
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin_engine.dispose()
