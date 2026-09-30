import sqlite3

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

DATABASE_URL = get_settings().database_url

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=not IS_SQLITE,  # hosted PostgreSQL drops idle connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores foreign keys unless enabled per connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
