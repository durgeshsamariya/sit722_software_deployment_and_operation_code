# backend/order_service/app/main.py

"""
Order Service — Week 3
CRUD for orders, with synchronous stock check/update using Product Service REST API.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db import engine, Base, get_db
from models import Order
from schemas import OrderCreate, OrderUpdate, OrderResponse

import requests
import os

from dotenv import load_dotenv
load_dotenv()

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8000")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Order Service API",
    description="Handles orders and syncs stock with Product Service.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def adjust_product_stock(product_id: int, delta: int):
    """Adjust product stock via Product Service API."""
    product_resp = requests.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
    if product_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Product not found in Product Service")
    product = product_resp.json()
    new_stock = product["stock_quantity"] + delta
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Not enough stock for update")
    update_resp = requests.put(
        f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock",
        params={"stock_quantity": new_stock}
    )
    if update_resp.status_code not in (200, 201):
        raise HTTPException(status_code=update_resp.status_code, detail="Failed to update stock in Product Service")

@app.post("/orders/", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    adjust_product_stock(order.product_id, -order.quantity)
    db_order = Order(
        product_id=order.product_id,
        customer_name=order.customer_name,
        quantity=order.quantity
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.get("/orders/", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, update: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    prev_qty = order.quantity
    delta = update.quantity - prev_qty
    adjust_product_stock(order.product_id, -delta)
    order.quantity = update.quantity
    if update.customer_name:
        order.customer_name = update.customer_name
    db.commit()
    db.refresh(order)
    return order

@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    adjust_product_stock(order.product_id, order.quantity)
    db.delete(order)
    db.commit()
    return {"detail": "Order deleted"}
