from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import load_settings
from app.db.base import Base, import_models

settings = load_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

TWIN_OWNED_TABLES = ("conversations", "messages", "documents", "document_chunks", "learning_records")


def init_db() -> None:
    import_models()
    Base.metadata.create_all(bind=engine)
    _ensure_twin_columns()


def _ensure_twin_columns() -> None:
    """Add nullable twin_id columns to existing local SQLite databases.

    Base.metadata.create_all does not alter existing tables. The app currently uses
    SQLite by default, so this keeps older developer/server databases bootable after
    adding twin-scoped ownership. Production databases should still use Alembic.
    """
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name in TWIN_OWNED_TABLES:
            if table_name not in existing_tables:
                continue
            column_names = {column["name"] for column in inspector.get_columns(table_name)}
            if "twin_id" not in column_names:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN twin_id VARCHAR(36)"))


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
