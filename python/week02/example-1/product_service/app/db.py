# week02/backend/product_service/app/db.py

"""
Database configuration and session management for FastAPI app.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Read DB settings from environment variables, with defaults for local/dev
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "products")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Compose the SQLAlchemy database URL, split for linting
DATABASE_URL = (
    "postgresql://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Create SQLAlchemy engine and session
# pool_pre_ping=True helps maintain healthy connections in a pool
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Configure a sessionmaker to create new database sessions.
# autocommit=False ensures transactions must be committed explicitly.
# autoflush=False means changes aren't flushed to DB until commit or explicit flush.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your ORM models
Base = declarative_base()


def get_db():
    """
    Dependency to provide a new database session for FastAPI endpoints.
    A session is created for each request and automatically closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
