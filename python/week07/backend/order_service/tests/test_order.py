import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def created_order():
    # create an order for use in other tests
    payload = {"customer_name": "Alice", "item": "Widget"}
    res = client.post("/orders/", json=payload)
    assert res.status_code == 200
    return res.json()

def test_create_order():
    payload = {"customer_name": "Bob", "item": "Gadget"}
    res = client.post("/orders/", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["customer_name"] == payload["customer_name"]
    assert "id" in data

def test_list_orders(created_order):
    res = client.get("/orders/")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(o["id"] == created_order["id"] for o in data)

def test_get_order_by_id(created_order):
    oid = created_order["id"]
    res = client.get(f"/orders/{oid}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == oid
    assert data["item"] == created_order["item"]

def test_update_order(created_order):
    oid = created_order["id"]
    update = {"customer_name": "Alice_updated", "item": "WidgetPlus"}
    res = client.put(f"/orders/{oid}", json=update)
    assert res.status_code == 200
    data = res.json()
    assert data["customer_name"] == update["customer_name"]

def test_delete_order():
    payload = {"customer_name": "Carol", "item": "Thingamajig"}
    res = client.post("/orders/", json=payload)
    oid = res.json()["id"]

    res = client.delete(f"/orders/{oid}")
    assert res.status_code == 200
    res = client.get(f"/orders/{oid}")
    assert res.status_code == 404
