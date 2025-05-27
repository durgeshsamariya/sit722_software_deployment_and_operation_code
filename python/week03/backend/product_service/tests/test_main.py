# tests/test_main.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

client = TestClient(app)

# Track created products
created_product_ids = []

def test_create_product():
    data = {
        "name": "Test Product",
        "description": "A demo product",
        "price": 9.99,
        "stock_quantity": 10
    }
    response = client.post("/products/", data=data)
    assert response.status_code == 201
    resp_json = response.json()
    assert resp_json["name"] == "Test Product"
    created_product_ids.append(resp_json["product_id"])

def test_list_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_stock():
    # Use the product created in previous test
    product_id = created_product_ids[-1]
    stock_url = f"/products/{product_id}/stock?stock_quantity=2"
    update_resp = client.put(stock_url)
    assert update_resp.status_code == 200
    assert update_resp.json()["stock_quantity"] == 2

def test_delete_product():
    # Clean up: delete only the product(s) created in this test run
    for product_id in created_product_ids:
        resp = client.delete(f"/products/{product_id}")
        assert resp.status_code in (204, 200)  # 204 for delete success
