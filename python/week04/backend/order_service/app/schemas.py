# backend/order_service/app/schemas.py

"""
Pydantic schemas for Order Service validation and serialization.
Updated for customer_id and order_status.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from models import OrderStatus

class OrderItem(BaseModel):
    product_id: int = Field(..., gt=0, description="ID of the product ordered")
    quantity: int = Field(..., gt=0, description="Quantity of the product ordered")


class OrderCreate(BaseModel):
    customer_id: int = Field(..., gt=0, description="ID of the customer placing the order")
    items: list[OrderItem] = Field(..., min_items=1, description="List of products and quantities in the order")

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = Field(None, description="New status for the order")


class OrderResponse(OrderCreate):
    order_id: int
    customer_id: int
    items: list[OrderItem] # To reflect what was ordered initially
    status: OrderStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    class Config:
        orm_mode = True
        use_enum_values = True
