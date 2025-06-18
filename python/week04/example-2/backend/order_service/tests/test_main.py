# week04/example-2/backend/order_service/tests/test_main.py

import logging
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.db import SessionLocal, engine, get_db
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
logging.getLogger("app.main").setLevel(logging.WARNING)  # Suppress app's own info logs


@pytest.fixture(scope="session", autouse=True)
def setup_database_for_tests():
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


@pytest.fixture(scope="function")
def mock_httpx_client():
    with patch("app.main.httpx.AsyncClient") as mock_async_client_cls:
        mock_client_instance = AsyncMock()
        mock_async_client_cls.return_value.__aenter__.return_value = (
            mock_client_instance
        )
        yield mock_client_instance


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


def test_create_order_success(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests successful creation of an order with multiple items,
    mocking successful stock deduction from Product Service.
    """
    # Configure the mock Product Service response for stock deduction
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": "Stock deducted successfully"}
    mock_response.raise_for_status.return_value = (
        None  # Ensure raise_for_status doesn't raise
    )

    # Set the return value for the patch method of the mocked httpx client
    mock_httpx_client.patch.return_value = mock_response

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

    # Verify that the Product Service's deduct-stock endpoint was called for each item
    expected_calls = [
        (
            "patch",
            f"{PRODUCT_SERVICE_URL}/products/101/deduct-stock",
            {"quantity_to_deduct": 2},
        ),
        (
            "patch",
            f"{PRODUCT_SERVICE_URL}/products/102/deduct-stock",
            {"quantity_to_deduct": 1},
        ),
    ]
    # Check that mock_httpx_client.patch was called twice with correct arguments
    assert mock_httpx_client.patch.call_count == 2
    for call_args, call_kwargs in mock_httpx_client.patch.call_args_list:
        url = call_args[0]
        json_payload = call_kwargs["json"]

        found_call = False
        for expected_url, expected_payload in [
            (
                f"{PRODUCT_SERVICE_URL}/products/101/deduct-stock",
                {"quantity_to_deduct": 2},
            ),
            (
                f"{PRODUCT_SERVICE_URL}/products/102/deduct-stock",
                {"quantity_to_deduct": 1},
            ),
        ]:
            if url == expected_url and json_payload == expected_payload:
                found_call = True
                break
        assert found_call, f"Unexpected call: url={url}, json={json_payload}"


def test_create_order_insufficient_stock(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests order creation when Product Service reports insufficient stock.
    Verifies that order is NOT created and an appropriate error is returned.
    """
    # Configure the mock Product Service response for insufficient stock
    mock_response = AsyncMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {
        "detail": "Insufficient stock for product 'TestProduct'. Only 0 available."
    }
    # Mock raise_for_status to raise httpx.HTTPStatusError
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request",
        request=httpx.Request("PATCH", "http://mock/"),
        response=mock_response,
    )

    # Make the patch call return this mock response for the first item
    mock_httpx_client.patch.return_value = mock_response

    order_data = {
        "user_id": 2,
        "shipping_address": "456 Commerce Rd",
        "items": [
            {
                "product_id": 201,
                "quantity": 5,
                "price_at_purchase": 50.00,
            }  # This item will fail stock deduction
        ],
    }
    response = client.post("/orders/", json=order_data)

    assert response.status_code == 400
    assert "Failed to deduct stock for product 201" in response.json()["detail"]
    assert (
        "Insufficient stock for product 'TestProduct'. Only 0 available."
        in response.json()["detail"]
    )

    # Verify that the order was NOT created in the database
    db_order = db_session_for_test.query(Order).filter(Order.user_id == 2).first()
    assert db_order is None

    # Verify rollback was called (though in this mock it's a no-op as it's the first item)
    # The _rollback_stock_deductions helper will log a warning as it can't truly roll back a mock
    # without a specific add-stock endpoint on the mock.
    # We can check that the patch call was made as expected.
    mock_httpx_client.patch.assert_called_once_with(
        f"{PRODUCT_SERVICE_URL}/products/201/deduct-stock",
        json={"quantity_to_deduct": 5},
        timeout=5,
    )


def test_create_order_product_not_found(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests order creation when Product Service reports product not found.
    Verifies that order is NOT created.
    """
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Product not found"}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found",
        request=httpx.Request("PATCH", "http://mock/"),
        response=mock_response,
    )
    mock_httpx_client.patch.return_value = mock_response

    order_data = {
        "user_id": 3,
        "shipping_address": "789 Main St",
        "items": [
            {
                "product_id": 999,
                "quantity": 1,
                "price_at_purchase": 10.00,
            }  # Non-existent product
        ],
    }
    response = client.post("/orders/", json=order_data)

    assert response.status_code == 400  # Order Service returns 400 for its own logic
    assert "Failed to deduct stock for product 999" in response.json()["detail"]
    assert "Product 999 not found" in response.json()["detail"]

    db_order = db_session_for_test.query(Order).filter(Order.user_id == 3).first()
    assert db_order is None

    mock_httpx_client.patch.assert_called_once_with(
        f"{PRODUCT_SERVICE_URL}/products/999/deduct-stock",
        json={"quantity_to_deduct": 1},
        timeout=5,
    )


def test_create_order_product_service_unavailable(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests order creation when Product Service is unreachable due to network error.
    Verifies that order is NOT created and a 503 error is returned.
    """
    mock_httpx_client.patch.side_effect = httpx.RequestError(
        "Connection refused", request=httpx.Request("PATCH", "http://mock/")
    )

    order_data = {
        "user_id": 4,
        "shipping_address": "101 Network Ave",
        "items": [{"product_id": 401, "quantity": 1, "price_at_purchase": 10.00}],
    }
    response = client.post("/orders/", json=order_data)

    assert response.status_code == 503
    assert "Product Service is currently unavailable" in response.json()["detail"]

    db_order = db_session_for_test.query(Order).filter(Order.user_id == 4).first()
    assert db_order is None

    mock_httpx_client.patch.assert_called_once()  # Verify a call was attempted


def test_create_order_with_partial_stock_failure_rollback_simulated(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests a scenario where the first item's stock deduction succeeds, but the second fails.
    Verifies that no order is created and a rollback for the first item is attempted (simulated).
    """
    # Mock responses for two items
    mock_success_response = AsyncMock()
    mock_success_response.status_code = 200
    mock_success_response.raise_for_status.return_value = None

    mock_failure_response = AsyncMock()
    mock_failure_response.status_code = 400
    mock_failure_response.json.return_value = {
        "detail": "Insufficient stock for product 202"
    }
    mock_failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Bad Request",
        request=httpx.Request("PATCH", "http://mock/"),
        response=mock_failure_response,
    )

    # Configure mock_httpx_client.patch to return responses in order for consecutive calls
    mock_httpx_client.patch.side_effect = [
        mock_success_response,  # Response for product 101
        mock_failure_response,  # Response for product 202
    ]

    order_data = {
        "user_id": 5,
        "shipping_address": "888 Partial Fail Lane",
        "items": [
            {"product_id": 101, "quantity": 1, "price_at_purchase": 10.00},  # Succeeds
            {
                "product_id": 202,
                "quantity": 10,
                "price_at_purchase": 20.00,
            },  # Fails (insufficient stock)
        ],
    }
    response = client.post("/orders/", json=order_data)

    assert response.status_code == 400
    assert "Failed to deduct stock for product 202" in response.json()["detail"]
    assert "Insufficient stock for product 202" in response.json()["detail"]

    # Verify that the order was NOT created in the database
    db_order = db_session_for_test.query(Order).filter(Order.user_id == 5).first()
    assert db_order is None

    # Verify both patch calls were made
    assert mock_httpx_client.patch.call_count == 2
    # The _rollback_stock_deductions helper will be called, logging a warning
    # because we don't have a real 'add-stock' endpoint to test rollback.
    # In a real system, you would assert that the add-stock endpoint was called.

    # We can assert the calls made for deduction
    call_args_list = mock_httpx_client.patch.call_args_list
    assert (
        call_args_list[0].args[0] == f"{PRODUCT_SERVICE_URL}/products/101/deduct-stock"
    )
    assert call_args_list[0].kwargs["json"] == {"quantity_to_deduct": 1}
    assert (
        call_args_list[1].args[0] == f"{PRODUCT_SERVICE_URL}/products/202/deduct-stock"
    )
    assert call_args_list[1].kwargs["json"] == {"quantity_to_deduct": 10}


# Remaining tests from previous example (no changes needed, but ensure they are present)


def test_list_orders_empty(client: TestClient, db_session_for_test: Session):
    """
    Tests listing orders when no orders exist, expecting an empty list.
    """
    response = client.get("/orders/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_orders_with_data(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests listing orders when orders exist.
    """
    # Mock product service success for the creation
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

    # Create an order
    order_data = {
        "user_id": 44,
        "items": [{"product_id": 201, "quantity": 1, "price_at_purchase": 100.00}],
    }
    client.post("/orders/", json=order_data)

    response = client.get("/orders/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
    assert any(o["user_id"] == 44 for o in response.json())


def test_list_orders_filter_by_user_id(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests filtering orders by user ID.
    """
    # Mock product service success for creations
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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


def test_list_orders_filter_by_status(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests filtering orders by status.
    """
    # Mock product service success for creations
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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


def test_get_order_success(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests successful retrieval of a single order by ID.
    """
    # Mock product service success for the creation
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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


def test_update_order_status(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests updating the status of an existing order.
    """
    # Mock product service success for the creation
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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


def test_delete_order_success(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests successful deletion of an order and its items.
    """
    # Mock product service success for the creation
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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


def test_get_order_items_success(
    client: TestClient, db_session_for_test: Session, mock_httpx_client: AsyncMock
):
    """
    Tests retrieving order items for a specific order.
    """
    # Mock product service success for the creation
    mock_httpx_client.patch.return_value = AsyncMock(status_code=200)
    mock_httpx_client.patch.return_value.raise_for_status.return_value = None

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
