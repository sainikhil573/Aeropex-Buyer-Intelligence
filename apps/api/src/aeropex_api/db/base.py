"""SQLAlchemy declarative base for persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_models() -> None:
    """Import models so Alembic can discover mapped metadata."""

    import aeropex_api.db.models  # noqa: F401
