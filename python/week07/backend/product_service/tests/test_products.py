import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

@pytest.fixture(scope="module")
def created_product():
    # create a product for use in other tests
    payload = {"name": "TestProduct", "description": "A product for testing"}
    res = client.post("/products/", json=payload)
    assert res.status_code == 200
    return res.json()

def test_create_product():
    payload = {"name": "AnotherProd", "description": "Another test"}
    res = client.post("/products/", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == payload["name"]
    assert "id" in data

def test_list_products(created_product):
    res = client.get("/products/")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    # ensure the product we created appears
    assert any(p["id"] == created_product["id"] for p in data)

def test_get_product_by_id(created_product):
    prod_id = created_product["id"]
    res = client.get(f"/products/{prod_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == prod_id
    assert data["name"] == created_product["name"]

def test_update_product(created_product):
    prod_id = created_product["id"]
    update = {"name": "UpdatedName", "description": "Updated desc"}
    res = client.put(f"/products/{prod_id}", json=update)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == update["name"]

def test_delete_product():
    # create a fresh product then delete
    payload = {"name": "ToDelete", "description": "Will be deleted"}
    res = client.post("/products/", json=payload)
    pid = res.json()["id"]

    res = client.delete(f"/products/{pid}")
    assert res.status_code == 200
    # subsequent fetch returns 404
    res = client.get(f"/products/{pid}")
    assert res.status_code == 404
