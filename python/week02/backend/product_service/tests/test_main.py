# backend/product_service/tests/test_main.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_products():
    # Track product IDs created in each test
    created_ids = []

    yield created_ids

    # Cleanup: delete created products after the test
    for product_id in created_ids:
        client.delete(f"/products/{product_id}")

def test_create_product(cleanup_products):
    data = {
        "name": "Test Product",
        "description": "A demo product",
        "price": 9.99,
        "stock_quantity": 10
    }
    response = client.post("/products/", json=data)
    assert response.status_code == 201
    resp_json = response.json()
    assert resp_json["name"] == "Test Product"
    assert resp_json["price"] == 9.99
    assert resp_json["stock_quantity"] == 10
    # Register product for cleanup
    cleanup_products.append(resp_json["product_id"])

def test_list_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_stock(cleanup_products):
    # First create product
    data = {
        "name": "Stock Test",
        "description": "",
        "price": 5.0,
        "stock_quantity": 10
    }
    create_resp = client.post("/products/", json=data)
    product_id = create_resp.json()["product_id"]
    cleanup_products.append(product_id)

    # Update stock
    stock_url = f"/products/{product_id}/stock?stock_quantity=2"
    update_resp = client.put(stock_url)
    assert update_resp.status_code == 200
    assert update_resp.json()["stock_quantity"] == 2

def test_get_product_not_found():
    response = client.get("/products/99999")
    assert response.status_code == 404

def test_invalid_price():
    data = {
        "name": "Invalid Price",
        "description": "",
        "price": -1,
        "stock_quantity": 5
    }
    response = client.post("/products/", json=data)
    assert response.status_code == 422
