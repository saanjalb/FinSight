"""
Database connection setup.

Uses SQLite for local development/demo simplicity. The engine is created
through SQLAlchemy, so switching to PostgreSQL later is a one-line change
to DATABASE_URL — no changes needed anywhere else in the app.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite file lives alongside this module. In production this would be
# a PostgreSQL connection string read from an environment variable.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/db/finsight.db")

# check_same_thread=False is required for SQLite when used with FastAPI,
# since FastAPI can handle requests across multiple threads.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models will inherit from this Base.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request,
    and guarantees it's closed afterward even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
