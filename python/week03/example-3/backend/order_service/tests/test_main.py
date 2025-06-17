# week03/example-2/backend/order_service/tests/test_main.py

"""
Integration tests for the Order Service API.
These tests verify the functionality of the API endpoints by
making actual HTTP requests to the running FastAPI application.
Each test runs within its own database transaction for isolation,
which is rolled back after the test completes.
Crucially, these tests also mock the external HTTP calls to the Product Service
to control its responses and test stock deduction scenarios.
"""

import logging
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch  # For mocking httpx.AsyncClient

import pytest
from app.db import SessionLocal, engine, get_db
# Import app, engine, get_db, SessionLocal, and Base from your main application's modules.
from app.main import PRODUCT_SERVICE_URL, app
from app.models import Base, Order, OrderItem
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Suppress noisy logs from SQLAlchemy/FastAPI/Uvicorn during tests for cleaner output
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING) # Suppress app's own info logs


# --- Pytest Fixtures ---

@pytest.fixture(scope="session", autouse=True)
def setup_database_for_tests():
    """
    Ensures the Order Service's database is reachable and its tables are created
    before any tests run. This runs once per test session.
    Also ensures a clean state by dropping and recreating tables.
    """
    max_retries = 10
    retry_delay_seconds = 3
    for i in range(max_retries):
        try:
            logging.info(f"Order Service Tests: Attempting to connect to PostgreSQL for test setup (attempt {i+1}/{max_retries})...")
            # Explicitly drop all tables first to ensure a clean slate for the session
            Base.metadata.drop_all(bind=engine)
            logging.info("Order Service Tests: Successfully dropped all tables in PostgreSQL for test setup.")

            # Then create all tables required by the application
            Base.metadata.create_all(bind=engine)
            logging.info("Order Service Tests: Successfully created all tables in PostgreSQL for test setup.")
            break
        except OperationalError as e:
            logging.warning(f"Order Service Tests: Test setup DB connection failed: {e}. Retrying in {retry_delay_seconds} seconds...")
            time.sleep(retry_delay_seconds)
            if i == max_retries - 1:
                pytest.fail(f"Could not connect to PostgreSQL for Order Service test setup after {max_retries} attempts: {e}")
        except Exception as e:
            pytest.fail(f"Order Service Tests: An unexpected error occurred during test DB setup: {e}", pytrace=True)
    
    yield # Yield control to the tests

    # Optional: Uncomment to drop tables after all tests in the session
    # logging.info("Order Service Tests: Dropping tables from PostgreSQL after test session.")
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session_for_test():
    """
    Provides a transactional database session for each test function.
    This fixture ensures each test runs in isolation and its changes are not persisted.
    """
    connection = engine.connect()
    transaction = connection.begin()
    db = SessionLocal(bind=connection)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db
    finally:
        transaction.rollback()
        db.close()
        connection.close()
        app.dependency_overrides.pop(get_db, None)

@pytest.fixture(scope="module")
def client():
    """
    Provides a TestClient for making HTTP requests to the FastAPI application.
    """
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="function")
def mock_httpx_client():
    """
    Mocks httpx.AsyncClient to prevent actual HTTP calls to the Product Service.
    We mock the entire AsyncClient and its patch method.
    """
    with patch('app.main.httpx.AsyncClient') as mock_async_client_cls:
        mock_client_instance = AsyncMock()
        mock_async_client_cls.return_value.__aenter__.return_value = mock_client_instance
        yield mock_client_instance

# --- Order Service Tests ---

def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Order Service!"}

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "order-service"}
