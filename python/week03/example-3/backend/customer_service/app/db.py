# week03/example-3/backend/customer_service/app/db.py

"""
Database connection setup and session management for the Order Service.

This module configures the SQLAlchemy engine and session factory for connecting
to a PostgreSQL database. It also provides a FastAPI dependency function
(`get_db`) to manage database sessions effectively for API endpoints.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "customers")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Construct the full database connection URL using an f-string for readability.
# Format: "postgresql://user:password@host:port/database_name"
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Create the SQLAlchemy engine for the Order Service database.
# pool_pre_ping=True helps maintain healthy connections in a pool.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Dependency that provides a database session to path operations.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
