# app/database.py


"""
Database configuration and session management for the Product Service.

This module sets up the SQLAlchemy engine, session, and declarative base.
It also provides a dependency function (`get_db`) for FastAPI to manage
database sessions per request.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# Load environment variables from .env
load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "products")
# POSTGRES_HOST:
# - 'localhost' when running the backend directly on the host machine.
# - 'host.docker.internal' when running the backend in Docker and connecting
#   to a PostgreSQL server running directly on the Docker host machine.
# - A specific hostname/IP for a remote database.
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")  # default for local; set to Azure for prod
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Compose the SQLAlchemy database URL, split for linting
# Construct the full database connection URL using f-strings for readability.
# Example format: "postgresql://user:password@host:port/database_name"
DATABASE_URL = (
    "postgresql://"
    f"{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# --- SQLAlchemy Engine and Session Setup ---
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    Provides a SQLAlchemy database session for FastAPI dependencies.

    This function is a generator that manages the lifecycle of a database session.
    It yields a session for use in request handlers and ensures the session is
    closed properly in the `finally` block, even if an error occurs during the request.

    Yields:
        sqlalchemy.orm.Session: A SQLAlchemy database session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
