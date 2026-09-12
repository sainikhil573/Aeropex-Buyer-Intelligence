"""SQLAlchemy engine and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aeropex_api.core.config import Settings, get_settings


def create_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    app_settings = settings or get_settings()
    if not app_settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured before opening database sessions")

    engine = create_engine(app_settings.database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    session_factory = create_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
