"""Database configuration and session management."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from ..models import Base

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "performance_management.db"

# Create engine
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging during development
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    This should be called once when the application starts.
    """
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency function to get a database session.

    Yields:
        Session: SQLAlchemy database session

    Example:
        with next(get_session()) as session:
            # use session here
            pass
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db() -> Session:
    """
    Get a database session for direct use.
    Remember to close the session when done.

    Returns:
        Session: SQLAlchemy database session

    Example:
        db = get_db()
        try:
            # use db here
            pass
        finally:
            db.close()
    """
    return SessionLocal()
