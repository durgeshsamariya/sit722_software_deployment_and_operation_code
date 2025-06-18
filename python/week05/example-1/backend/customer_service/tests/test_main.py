# week05/example-1/backend/customer_service/tests/test_main.py

import logging
import time

import pytest
from app.db import Base, SessionLocal, engine, get_db
from app.main import app
from app.models import Customer

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Suppress noisy logs from SQLAlchemy/FastAPI/Uvicorn during tests for cleaner output
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)


# --- Pytest Fixtures ---
@pytest.fixture(scope="session", autouse=True)
def setup_database_for_tests():
    max_retries = 10
    retry_delay_seconds = 3
    for i in range(max_retries):
        try:
            logging.info(
                f"Customer Service Tests: Attempting to connect to PostgreSQL for test setup (attempt {i+1}/{max_retries})..."
            )
            # Explicitly drop all tables first to ensure a clean slate for the session
            Base.metadata.drop_all(bind=engine)
            logging.info(
                "Customer Service Tests: Successfully dropped all tables in PostgreSQL for test setup."
            )

            # Then create all tables required by the application
            Base.metadata.create_all(bind=engine)
            logging.info(
                "Customer Service Tests: Successfully created all tables in PostgreSQL for test setup."
            )
            break
        except OperationalError as e:
            logging.warning(
                f"Customer Service Tests: Test setup DB connection failed: {e}. Retrying in {retry_delay_seconds} seconds..."
            )
            time.sleep(retry_delay_seconds)
            if i == max_retries - 1:
                pytest.fail(
                    f"Could not connect to PostgreSQL for Customer Service test setup after {max_retries} attempts: {e}"
                )
        except Exception as e:
            pytest.fail(
                f"Customer Service Tests: An unexpected error occurred during test DB setup: {e}",
                pytrace=True,
            )

    yield


@pytest.fixture(scope="function")
def db_session_for_test():
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
    with TestClient(app) as test_client:
        yield test_client


# --- Customer Service Tests ---
def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Customer Service!"}


def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "customer-service"}


def test_create_customer_success(client: TestClient, db_session_for_test: Session):
    """Tests successful creation of a customer."""
    customer_data = {
        "email": "test1@example.com",
        "password": "securepassword123",
        "first_name": "Alice",
        "last_name": "Smith",
        "phone_number": "111-222-3333",
        "shipping_address": "123 Main St",
    }
    response = client.post("/customers/", json=customer_data)

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["email"] == customer_data["email"]
    assert response_data["first_name"] == customer_data["first_name"]
    assert "customer_id" in response_data
    assert isinstance(response_data["customer_id"], int)

    # Verify customer exists in DB
    db_customer = (
        db_session_for_test.query(Customer)
        .filter(Customer.customer_id == response_data["customer_id"])
        .first()
    )
    assert db_customer is not None
    assert db_customer.email == customer_data["email"]


def test_get_customer_success(client: TestClient, db_session_for_test: Session):
    """Tests retrieving a customer by ID."""
    customer_data = {
        "email": "getme@example.com",
        "password": "getpassword",
        "first_name": "Diana",
        "last_name": "Prince",
    }
    create_response = client.post("/customers/", json=customer_data)
    customer_id = create_response.json()["customer_id"]

    response = client.get(f"/customers/{customer_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["customer_id"] == customer_id
    assert response_data["email"] == customer_data["email"]


def test_get_customer_not_found(client: TestClient):
    """Tests retrieving a non-existent customer, expecting 404."""
    response = client.get("/customers/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_list_customers_empty(client: TestClient, db_session_for_test: Session):
    """Tests listing customers when none exist."""
    response = client.get("/customers/")
    assert response.status_code == 200
    assert response.json() == []


def test_update_customer_success(client: TestClient, db_session_for_test: Session):
    """Tests updating an existing customer."""
    customer_data = {
        "email": "updateme@example.com",
        "password": "oldpassword",
        "first_name": "Grace",
        "last_name": "Hopper",
        "shipping_address": "Old Address",
    }
    create_response = client.post("/customers/", json=customer_data)
    customer_id = create_response.json()["customer_id"]

    update_payload = {"first_name": "Graceful", "shipping_address": "New Address Lane"}
    response = client.put(f"/customers/{customer_id}", json=update_payload)

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["customer_id"] == customer_id
    assert response_data["first_name"] == "Graceful"
    assert response_data["shipping_address"] == "New Address Lane"
    assert response_data["email"] == "updateme@example.com"  # Email not changed

    # Verify in DB
    db_customer = (
        db_session_for_test.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )
    assert db_customer.first_name == "Graceful"
    assert db_customer.shipping_address == "New Address Lane"


def test_update_customer_not_found(client: TestClient):
    """Tests updating a non-existent customer, expecting 404."""
    response = client.put("/customers/999999", json={"first_name": "NonExistent"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_delete_customer_success(client: TestClient, db_session_for_test: Session):
    """Tests successful deletion of a customer."""
    customer_data = {
        "email": "deleteme@example.com",
        "password": "delpassword",
        "first_name": "Ivan",
        "last_name": "Terrible",
    }
    create_response = client.post("/customers/", json=customer_data)
    customer_id = create_response.json()["customer_id"]

    response = client.delete(f"/customers/{customer_id}")
    assert response.status_code == 204  # No Content

    # Verify customer is deleted
    get_response = client.get(f"/customers/{customer_id}")
    assert get_response.status_code == 404

    db_customer = (
        db_session_for_test.query(Customer)
        .filter(Customer.customer_id == customer_id)
        .first()
    )
    assert db_customer is None


def test_delete_customer_not_found(client: TestClient):
    """Tests deleting a non-existent customer, expecting 404."""
    response = client.delete("/customers/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"
