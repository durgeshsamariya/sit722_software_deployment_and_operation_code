from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String
from pydantic import BaseModel
from .db import engine, Base, get_db


# -----------------------------
# Models
# -----------------------------
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, index=True)
    item = Column(String, index=True)


Base.metadata.create_all(bind=engine)


# -----------------------------
# Schemas
# -----------------------------
class OrderCreate(BaseModel):
    customer_name: str
    item: str


class OrderUpdate(BaseModel):
    customer_name: str
    item: str


class OrderResponse(OrderCreate):
    id: int

    class Config:
        orm_mode = True


# -----------------------------
# FastAPI app
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only — restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create
@app.post("/orders/", response_model=OrderResponse)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    db_order = Order(customer_name=order.customer_name, item=order.item)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


# Read All
@app.get("/orders/", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).all()


# Read One
@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# Update
@app.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, updated: OrderUpdate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.customer_name = updated.customer_name
    order.item = updated.item
    db.commit()
    db.refresh(order)
    return order


# Delete
@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"detail": "Order deleted successfully"}
