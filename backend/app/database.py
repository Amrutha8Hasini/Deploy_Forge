"""
Database connection.

We use SQLite (a single file database) through SQLAlchemy. `get_db` gives each
API request its own session and closes it afterwards.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config

# check_same_thread=False lets the background deployment thread use SQLite too.
engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Parent class for all database tables."""


def init_db() -> None:
    """Create all tables (only creates the ones that are missing)."""
    from app import models  # noqa: F401  (import registers the tables)

    config.ensure_data_dirs()
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: open a session for one request, then close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
