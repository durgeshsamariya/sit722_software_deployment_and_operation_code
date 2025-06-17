# week02/example-2/backend/product_service/tests/test_main.py

"""
Integration tests for the Product Service API.
These tests verify the functionality of the API endpoints by
making actual HTTP requests to the running FastAPI application.
Each test runs within its own database transaction for isolation,
which is rolled back after the test completes.
"""

import logging
import time  # For the startup retry logic

import pytest
from app.db import SessionLocal, engine, get_db
from app.main import app
from app.models import Base, Product
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Suppress noisy logs from SQLAlchemy/FastAPI during tests for cleaner output
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
                f"Attempting to connect to main PostgreSQL for test setup (attempt {i+1}/{max_retries})..."
            )
            # Explicitly drop all tables first to ensure a clean slate for the session
            # This handles cases where data might persist from previous failed runs or manual interaction
            Base.metadata.drop_all(bind=engine)
            logging.info(
                "Successfully dropped all tables in main PostgreSQL for test setup."
            )

            # Then create all tables required by the application
            Base.metadata.create_all(bind=engine)
            logging.info(
                "Successfully created all tables in main PostgreSQL for test setup."
            )
            break
        except OperationalError as e:
            logging.warning(
                f"Test setup DB connection failed: {e}. Retrying in {retry_delay_seconds} seconds..."
            )
            time.sleep(retry_delay_seconds)
            if i == max_retries - 1:
                pytest.fail(
                    f"Could not connect to PostgreSQL for test setup after {max_retries} attempts: {e}"
                )
        except Exception as e:
            pytest.fail(
                f"An unexpected error occurred during test DB setup: {e}", pytrace=True
            )

    yield


@pytest.fixture(
    scope="function"
)  # 'function' scope ensures a fresh DB state for each test
def db_session_for_test():
    """
    Provides a transactional database session for each test function.
    This fixture:
    1. Connects to the database using the main app's engine.
    2. Begins a transaction.
    3. Creates a new session bound to this transaction.
    4. Overrides the app's `get_db` dependency to yield this test session.
    5. Yields the test session to the test function.
    6. Rolls back the transaction and closes the session/connection after the test.
    This ensures each test runs in isolation and its changes are not persisted to the actual DB.
    """
    connection = engine.connect()
    transaction = connection.begin()
    db = SessionLocal(bind=connection)

    # Define a new callable to provide the test session for dependency override
    def override_get_db():
        yield db

    # Override the application's get_db dependency
    app.dependency_overrides[get_db] = override_get_db

    try:
        yield db  # Yield the db session to the test function that requests it
    finally:
        # This will rollback all changes made during the test function
        transaction.rollback()
        db.close()
        connection.close()
        # Clean up the dependency override
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")  # Client is created once per test module
def client():
    """
    Provides a TestClient for making HTTP requests to the FastAPI application.
    The TestClient automatically manages the app's lifespan events (startup/shutdown).
    """

    with TestClient(app) as test_client:
        yield test_client


def test_read_root(client: TestClient):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Product Service!"}


def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "product-service"}


def test_create_product_success(client: TestClient, db_session_for_test: Session):
    """
    Tests successful creation of a product via POST /products/.
    Verifies status code, response data, and database entry.
    """
    test_data = {
        "name": "New Test Product",
        "description": "A brand new product for testing",
        "price": 12.34,
        "stock_quantity": 100,
    }
    response = client.post("/products/", json=test_data)

    assert response.status_code == 201
    response_data = response.json()

    # Assert response fields match input and generated fields exist
    assert response_data["name"] == test_data["name"]
    assert response_data["description"] == test_data["description"]
    assert (
        float(response_data["price"]) == test_data["price"]
    )  # Convert to float for comparison
    assert response_data["stock_quantity"] == test_data["stock_quantity"]
    assert "product_id" in response_data
    assert isinstance(response_data["product_id"], int)
    assert "created_at" in response_data
    assert "updated_at" in response_data

    # Verify the product exists in the database using the test session
    db_product = (
        db_session_for_test.query(Product)
        .filter(Product.product_id == response_data["product_id"])
        .first()
    )
    assert db_product is not None
    assert db_product.name == test_data["name"]


def test_create_product_missing_required_field(
    client: TestClient,
):  # Removed db_session_for_test: Session
    """
    Tests product creation with a missing required field (name), expecting a 422.
    """
    invalid_data = {"description": "Missing name", "price": 10.00, "stock_quantity": 10}
    response = client.post("/products/", json=invalid_data)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert any(
        "Field required" in err["msg"] and err["loc"][1] == "name"
        for err in response.json()["detail"]
    )


def test_list_products_empty(
    client: TestClient,
):
    """
    Tests listing products when no products exist, expecting an empty list.
    This test assumes a clean database state (due to transactional fixture).
    """
    response = client.get("/products/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_products_with_data(client: TestClient, db_session_for_test: Session):
    """
    Tests listing products when products exist, verifying the list structure.
    A product is created via API to ensure it's present.
    """
    # Create a product via API within the test's transaction
    product_data = {
        "name": "List Product Example",
        "description": "For list test",
        "price": 5.00,
        "stock_quantity": 10,
    }
    client.post("/products/", json=product_data)

    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1  # Should contain the product we just added
    assert any(p["name"] == "List Product Example" for p in response.json())


def test_list_products_pagination(client: TestClient, db_session_for_test: Session):
    """
    Tests pagination with skip and limit parameters.
    """
    # Create multiple products via API to properly test pagination
    for i in range(5):
        client.post(
            "/products/",
            json={
                "name": f"Paginated Product {i}",
                "description": f"Description for {i}",
                "price": float(10 + i),
                "stock_quantity": i,
            },
        )

    response = client.get("/products/?skip=1&limit=2")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 2


def test_list_products_search(client: TestClient, db_session_for_test: Session):
    """
    Tests searching products by name or description.
    """
    # Create specific products via API for search
    client.post(
        "/products/",
        json={
            "name": "Apple Laptop",
            "description": "Powerful machine",
            "price": 1000,
            "stock_quantity": 10,
        },
    )
    client.post(
        "/products/",
        json={
            "name": "Banana Phone",
            "description": "Fruit-themed device",
            "price": 500,
            "stock_quantity": 20,
        },
    )
    client.post(
        "/products/",
        json={
            "name": "Orange Juice",
            "description": "Freshly squeezed",
            "price": 5,
            "stock_quantity": 50,
        },
    )

    # Test search by name
    response = client.get("/products/?search=Apple")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Apple Laptop"

    # Test search by description
    response = client.get("/products/?search=machine")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Apple Laptop"

    # Test case-insensitivity
    response = client.get("/products/?search=banana")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Banana Phone"

    # Test no results
    response = client.get("/products/?search=xyz")
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_product_success(client: TestClient, db_session_for_test: Session):
    """
    Tests successful retrieval of a product by ID.
    """
    # Create a product via API for this test
    product_data = {
        "name": "Get Product Test",
        "description": "Temp desc",
        "price": 15.00,
        "stock_quantity": 20,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["product_id"] == product_id
    assert response.json()["name"] == "Get Product Test"


def test_get_product_not_found(
    client: TestClient,
):
    """
    Tests retrieving a non-existent product, expecting a 404.
    """
    response = client.get("/products/999999")  # Assuming 999999 is a non-existent ID
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_product_full(
    client: TestClient, db_session_for_test: Session
):  # db_session_for_test added
    """
    Tests full update of a product's details.
    """
    # Create a product for update test
    product_data = {
        "name": "Product To Update",
        "description": "Original description",
        "price": 20.00,
        "stock_quantity": 30,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    update_data = {
        "name": "Updated Name",
        "description": "Updated description text.",
        "price": 25.50,
        "stock_quantity": 75,
    }
    response = client.put(f"/products/{product_id}", json=update_data)
    assert response.status_code == 200
    updated_product = response.json()
    assert updated_product["product_id"] == product_id
    assert updated_product["name"] == "Updated Name"
    assert updated_product["description"] == "Updated description text."
    assert float(updated_product["price"]) == 25.50
    assert updated_product["stock_quantity"] == 75


def test_update_product_partial(client: TestClient, db_session_for_test: Session):
    """
    Tests partial update of a product (e.g., only name).
    """
    # Create a product for partial update test
    product_data = {
        "name": "Original Name",
        "description": "Original Desc",
        "price": 10.00,
        "stock_quantity": 10,
    }
    create_response = client.post("/products/", json=product_data)
    product_id = create_response.json()["product_id"]

    partial_update_data = {"name": "Partially Updated Name"}
    response = client.put(f"/products/{product_id}", json=partial_update_data)
    assert response.status_code == 200
    updated_product = response.json()
    assert updated_product["product_id"] == product_id
    assert updated_product["name"] == "Partially Updated Name"
    # Other fields should retain their original values
    assert updated_product["description"] == "Original Desc"
    assert float(updated_product["price"]) == 10.00
    assert updated_product["stock_quantity"] == 10


def test_update_product_not_found(client: TestClient):
    """
    Tests updating a non-existent product, expecting a 404.
    """
    update_data = {"name": "Non Existent Product"}
    response = client.put("/products/999999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_delete_product_success(client: TestClient):
    """
    Tests successful deletion of a product and verifies it's no longer retrievable.
    """
    # Create a product specifically for deletion
    create_resp = client.post(
        "/products/",
        json={
            "name": "Product to Delete",
            "description": "Will be deleted",
            "price": 10.0,
            "stock_quantity": 5,
        },
    )
    product_id = create_resp.json()["product_id"]

    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 204  # No content on successful delete

    # Verify product is no longer in DB via GET attempt
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Product not found"


def test_delete_product_not_found(
    client: TestClient,
):  # Removed db_session_for_test: Session
    """
    Tests deleting a non-existent product, expecting a 404.
    """
    response = client.delete("/products/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
