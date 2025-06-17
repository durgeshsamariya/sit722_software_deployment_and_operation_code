# week03/example-1/backend/order_service/tests/test_main.py

import logging
import time
from decimal import Decimal

import pytest
from app.db import SessionLocal, engine, get_db
from app.main import app
from app.models import Base, Order, OrderItem

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

# Suppress noisy logs from SQLAlchemy/FastAPI during tests for cleaner output
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)
logging.getLogger("app.main").setLevel(logging.WARNING)


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
            logging.info(
                f"Order Service Tests: Attempting to connect to PostgreSQL for test setup (attempt {i+1}/{max_retries})..."
            )
            # Explicitly drop all tables first to ensure a clean slate for the session
            Base.metadata.drop_all(bind=engine)
            logging.info(
                "Order Service Tests: Successfully dropped all tables in PostgreSQL for test setup."
            )

            # Then create all tables required by the application
            Base.metadata.create_all(bind=engine)
            logging.info(
                "Order Service Tests: Successfully created all tables in PostgreSQL for test setup."
            )
            break
        except OperationalError as e:
            logging.warning(
                f"Order Service Tests: Test setup DB connection failed: {e}. Retrying in {retry_delay_seconds} seconds..."
            )
            time.sleep(retry_delay_seconds)
            if i == max_retries - 1:
                pytest.fail(
                    f"Could not connect to PostgreSQL for Order Service test setup after {max_retries} attempts: {e}"
                )
        except Exception as e:
            pytest.fail(
                f"Order Service Tests: An unexpected error occurred during test DB setup: {e}",
                pytrace=True,
            )

    yield


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


def test_create_order_success(client: TestClient, db_session_for_test: Session):
    """
    Tests successful creation of an order with multiple items.
    Verifies status code, response data, and database entries.
    """
    order_data = {
        "user_id": 1,
        "shipping_address": "123 Test St, Test City",
        "items": [
            {"product_id": 101, "quantity": 2, "price_at_purchase": 10.50},
            {"product_id": 102, "quantity": 1, "price_at_purchase": 25.00},
        ],
    }
    response = client.post("/orders/", json=order_data)

    assert response.status_code == 201
    response_data = response.json()

    assert response_data["user_id"] == order_data["user_id"]
    assert response_data["shipping_address"] == order_data["shipping_address"]
    assert response_data["status"] == "pending"
    assert "order_id" in response_data
    assert isinstance(response_data["order_id"], int)
    assert "total_amount" in response_data
    assert Decimal(str(response_data["total_amount"])) == Decimal("2.00") * Decimal(
        "10.50"
    ) + Decimal("1.00") * Decimal(
        "25.00"
    )  # 21.00 + 25.00 = 46.00
    assert "items" in response_data
    assert len(response_data["items"]) == 2

    # Verify order items
    item1 = next(
        (item for item in response_data["items"] if item["product_id"] == 101), None
    )
    assert item1 is not None
    assert item1["quantity"] == 2
    assert float(item1["price_at_purchase"]) == 10.50
    assert Decimal(str(item1["item_total"])) == Decimal("21.00")

    item2 = next(
        (item for item in response_data["items"] if item["product_id"] == 102), None
    )
    assert item2 is not None
    assert item2["quantity"] == 1
    assert float(item2["price_at_purchase"]) == 25.00
    assert Decimal(str(item2["item_total"])) == Decimal("25.00")

    # Verify the order and items exist in the database using the test session
    db_order = (
        db_session_for_test.query(Order)
        .filter(Order.order_id == response_data["order_id"])
        .first()
    )
    assert db_order is not None
    assert len(db_order.items) == 2


def test_create_order_invalid_quantity(
    client: TestClient, db_session_for_test: Session
):
    """
    Tests order creation with invalid (zero) quantity, expecting a 422.
    """
    invalid_order_data = {
        "user_id": 2,
        "items": [
            {
                "product_id": 103,
                "quantity": 0,
                "price_at_purchase": 5.00,
            }  # Invalid quantity
        ],
    }
    response = client.post("/orders/", json=invalid_order_data)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert any(
        "greater than or equal to 1" in err["msg"] for err in response.json()["detail"]
    )


def test_create_order_missing_items(client: TestClient, db_session_for_test: Session):
    """
    Tests order creation with missing items list, expecting a 422.
    """
    invalid_order_data = {
        "user_id": 3,
        "shipping_address": "Some address",
        # Missing "items"
    }
    response = client.post("/orders/", json=invalid_order_data)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert any(
        "Field required" in err["msg"] and err["loc"][1] == "items"
        for err in response.json()["detail"]
    )


def test_list_orders_empty(client: TestClient, db_session_for_test: Session):
    """
    Tests listing orders when no orders exist, expecting an empty list.
    """
    response = client.get("/orders/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_orders_with_data(client: TestClient, db_session_for_test: Session):
    """
    Tests listing orders when orders exist.
    """
    # Create an order
    order_data = {
        "user_id": 4,
        "items": [{"product_id": 201, "quantity": 1, "price_at_purchase": 100.00}],
    }
    client.post("/orders/", json=order_data)

    response = client.get("/orders/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
    assert any(o["user_id"] == 4 for o in response.json())


def test_list_orders_filter_by_user_id(
    client: TestClient, db_session_for_test: Session
):
    """
    Tests filtering orders by user ID.
    """
    client.post(
        "/orders/",
        json={
            "user_id": 10,
            "items": [{"product_id": 301, "quantity": 1, "price_at_purchase": 10.00}],
        },
    )
    client.post(
        "/orders/",
        json={
            "user_id": 11,
            "items": [{"product_id": 302, "quantity": 1, "price_at_purchase": 20.00}],
        },
    )
    client.post(
        "/orders/",
        json={
            "user_id": 10,
            "items": [{"product_id": 303, "quantity": 1, "price_at_purchase": 30.00}],
        },
    )

    response = client.get("/orders/?user_id=10")
    assert response.status_code == 200
    filtered_orders = response.json()
    assert len(filtered_orders) == 2
    assert all(o["user_id"] == 10 for o in filtered_orders)


def test_list_orders_filter_by_status(client: TestClient, db_session_for_test: Session):
    """
    Tests filtering orders by status.
    """
    client.post(
        "/orders/",
        json={
            "user_id": 12,
            "status": "pending",
            "items": [{"product_id": 401, "quantity": 1, "price_at_purchase": 1.00}],
        },
    )
    client.post(
        "/orders/",
        json={
            "user_id": 13,
            "status": "shipped",
            "items": [{"product_id": 402, "quantity": 1, "price_at_purchase": 2.00}],
        },
    )
    client.post(
        "/orders/",
        json={
            "user_id": 12,
            "status": "pending",
            "items": [{"product_id": 403, "quantity": 1, "price_at_purchase": 3.00}],
        },
    )

    response = client.get("/orders/?status=pending")
    assert response.status_code == 200
    filtered_orders = response.json()
    assert len(filtered_orders) == 2
    assert all(o["status"] == "pending" for o in filtered_orders)


def test_get_order_success(client: TestClient, db_session_for_test: Session):
    """
    Tests successful retrieval of a single order by ID.
    """
    order_data = {
        "user_id": 5,
        "items": [{"product_id": 501, "quantity": 3, "price_at_purchase": 15.00}],
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id
    assert response.json()["user_id"] == 5
    assert len(response.json()["items"]) == 1
    assert Decimal(str(response.json()["total_amount"])) == Decimal("45.00")


def test_get_order_not_found(client: TestClient):
    """
    Tests retrieving a non-existent order, expecting a 404.
    """
    response = client.get("/orders/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_update_order_status(client: TestClient, db_session_for_test: Session):
    """
    Tests updating the status of an existing order.
    """
    order_data = {
        "user_id": 6,
        "status": "pending",
        "items": [{"product_id": 601, "quantity": 1, "price_at_purchase": 1.00}],
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    new_status = "shipped"
    response = client.patch(f"/orders/{order_id}/status?new_status={new_status}")
    assert response.status_code == 200
    updated_order = response.json()
    assert updated_order["order_id"] == order_id
    assert updated_order["status"] == new_status

    # Verify status in database
    db_order = (
        db_session_for_test.query(Order).filter(Order.order_id == order_id).first()
    )
    assert db_order.status == new_status


def test_update_order_status_not_found(client: TestClient):
    """
    Tests updating status for a non-existent order, expecting a 404.
    """
    response = client.patch("/orders/999999/status?new_status=cancelled")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_delete_order_success(client: TestClient, db_session_for_test: Session):
    """
    Tests successful deletion of an order and its items.
    """
    order_data = {
        "user_id": 7,
        "items": [{"product_id": 701, "quantity": 1, "price_at_purchase": 10.00}],
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    # Ensure items exist before deletion test
    db_items_before_delete = (
        db_session_for_test.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )
    assert len(db_items_before_delete) == 1

    response = client.delete(f"/orders/{order_id}")
    assert response.status_code == 204

    # Verify order is deleted
    get_response = client.get(f"/orders/{order_id}")
    assert get_response.status_code == 404

    # Verify items are also deleted due to cascade
    db_items_after_delete = (
        db_session_for_test.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )
    assert len(db_items_after_delete) == 0


def test_delete_order_not_found(client: TestClient):
    """
    Tests deleting a non-existent order, expecting a 404.
    """
    response = client.delete("/orders/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_get_order_items_success(client: TestClient, db_session_for_test: Session):
    """
    Tests retrieving order items for a specific order.
    """
    order_data = {
        "user_id": 8,
        "items": [
            {"product_id": 801, "quantity": 2, "price_at_purchase": 5.00},
            {"product_id": 802, "quantity": 1, "price_at_purchase": 10.00},
        ],
    }
    create_response = client.post("/orders/", json=order_data)
    order_id = create_response.json()["order_id"]

    response = client.get(f"/orders/{order_id}/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert any(item["product_id"] == 801 for item in items)
    assert any(item["product_id"] == 802 for item in items)


def test_get_order_items_order_not_found(client: TestClient):
    """
    Tests retrieving order items for a non-existent order.
    """
    response = client.get("/orders/999999/items")
    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"
