from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.config import get_settings
from app.db.session import AsyncSessionFactory, engine


def test_engine_uses_configured_database_url():
    assert engine.url.render_as_string(hide_password=False) == get_settings().database_url


def test_session_factory_creates_async_sessions():
    session = AsyncSessionFactory()

    try:
        assert isinstance(session, AsyncSession)
        assert session.sync_session.expire_on_commit is False
        assert session.autoflush is False
    finally:
        # No connection is acquired until the session executes a statement.
        session.sync_session.close()
